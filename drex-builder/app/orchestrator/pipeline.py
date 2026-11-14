import asyncio

from app.agents import prompts
from app.config import MAX_STEPS
from app.llm.client import LLMError
from app.orchestrator import workspace
from app.utils import clip

VALID_NEEDS = {"search", "code", "write", "data", "analysis"}


def ev(type_, **kw):
    return {"type": type_, **kw}


def clean_steps(plan):
    steps = []
    raw = plan.get("steps") if isinstance(plan, dict) else None
    for s in (raw or [])[:MAX_STEPS]:
        if isinstance(s, dict) and s.get("title"):
            need = str(s.get("needs", "analysis")).lower()
            steps.append({"title": str(s["title"]), "needs": need if need in VALID_NEEDS else "analysis",
                          "goal": str(s.get("goal", s["title"]))})
    return steps


class ProjectPipeline:
    def __init__(self, drex, workers):
        self.drex = drex
        self.workers = workers

    async def run(self, request: str):
        by_name = {w.name: w for w in self.workers}
        project = workspace.new_project_dir(request)

        # 1. every agent proposes a plan
        yield ev("status", text=f"Asking {len(self.workers)} agents for a plan…")
        results = await asyncio.gather(*[w.ask_json(prompts.plan_prompt(request, MAX_STEPS)) for w in self.workers])
        plans = {w.name: clean_steps(r) for w, r in zip(self.workers, results)}
        plans = {n: s for n, s in plans.items() if s}
        if not plans:
            yield ev("error", text="No agent returned a usable plan. Check your API keys / models in the terminal.")
            return

        # 2. Drex picks the best plan
        render = {n: "\n".join(f"{i}. [{s['needs']}] {s['title']}: {s['goal']}" for i, s in enumerate(st, 1))
                  for n, st in plans.items()}
        verdict = await self.drex.judge("Which step-by-step plan is the best way to build this project?", request, render)
        yield ev("decision", index=0, stage="Plan", winner=verdict["winner"], scores=verdict["scores"],
                 judge=self.drex.label)
        steps = plans[verdict["winner"]]
        yield ev("steps", steps=[s["title"] for s in steps], planner=verdict["winner"])

        # 3. for each step: proposals -> Drex picks -> winner executes
        done = []
        for i, step in enumerate(steps, 1):
            yield ev("status", text=f"Step {i}/{len(steps)}: collecting proposals…")
            eligible = [w for w in self.workers if step["needs"] in w.capabilities] or self.workers
            ctx = [{**d} for d in done]
            props = await asyncio.gather(*[w.ask_json(prompts.propose_prompt(request, step, ctx)) for w in eligible])
            proposals = {}
            for w, p in zip(eligible, props):
                if isinstance(p, dict) and p.get("approach"):
                    proposals[w.name] = f"{p['approach']}\nWhy: {p.get('rationale', '')}\nConfidence: {p.get('confidence', '?')}"
            if not proposals:
                proposals = {eligible[0].name: "(no proposals returned, using default agent)"}

            verdict = await self.drex.judge(f"Which agent's approach is best for the step '{step['title']}'?", request, proposals)
            yield ev("decision", index=i, stage=step["title"], winner=verdict["winner"], scores=verdict["scores"],
                     judge=self.drex.label)

            # winner first, then runners-up, then any other agent
            ranked = [verdict["winner"]] + sorted((n for n in proposals if n != verdict["winner"]),
                                                  key=lambda n: -verdict["scores"].get(n, 0))
            order = ranked + [w.name for w in self.workers if w.name not in ranked]
            output, who = None, None
            for name in order:
                yield ev("status", text=f"Step {i}/{len(steps)}: {name} is working…")
                try:
                    approach = proposals.get(name) or proposals[verdict["winner"]]
                    output = await by_name[name].ask(prompts.execute_prompt(request, step, approach, ctx), temperature=0.3)
                    if output.strip():
                        who = name
                        break
                except LLMError as e:
                    print(f"[{name} failed on step {i}] {clip(str(e), 200)}")
            if not output:
                yield ev("error", text=f"Step {i} ({step['title']}) failed for every agent. Stopping here.")
                break

            files = workspace.save_step(project, i, step["title"], who, output)
            done.append({"index": i, "title": step["title"], "agent": who, "text": output, "files": files})
            yield ev("step_result", index=i, agent=who, winner=verdict["winner"], files_count=len(files))

        if not done:
            return
        workspace.write_index(project, request, done)
        zip_path = workspace.make_zip(project)
        yield ev("done", text=f"Finished {len(done)}/{len(steps)} steps.",
                 zip=f"/workspace/{zip_path.name}", name=zip_path.name)