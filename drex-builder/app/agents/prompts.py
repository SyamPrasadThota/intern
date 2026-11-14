from app.utils import clip

NEEDS = "search | code | write | data | analysis"


def plan_prompt(request: str, max_steps: int) -> str:
    return f"""TASK=PLAN
Break this project into {max_steps} or fewer ordered, concrete steps (e.g. choose dataset,
research papers, clean data, train model, write code, evaluate, write documentation).

PROJECT:
{request}

Each step needs a "needs" value, the main skill required: {NEEDS}.
Reply with JSON only:
{{"steps":[{{"title":"...","needs":"search","goal":"one sentence"}}]}}"""


def propose_prompt(request: str, step: dict, done: list) -> str:
    return f"""TASK=PROPOSE
Project: {request}

Current step: {step['title']}
Goal: {step['goal']}

Completed so far:
{_done(done)}

Propose how YOU would do this step. Be concrete: if the step is choosing a dataset, name the
dataset, link/source, size, licence and why it beats alternatives. If it is code, outline the
design and libraries. Do NOT do the whole step yet.
Reply with JSON only:
{{"approach":"...","rationale":"why this is best","confidence":1-10}}"""


def execute_prompt(request: str, step: dict, approach: str, done: list) -> str:
    return f"""TASK=EXECUTE
Project: {request}

Your step: {step['title']}
Goal: {step['goal']}

Winning approach selected by the judge:
{approach}

Completed so far:
{_done(done)}

Now DO the step fully and produce the real deliverable.
- Code: complete, runnable files. Put each in a fenced block whose first line is a comment
  `# file: path/name.ext` (or `// file:` for JS).
- Dataset / research: concrete names, links, licences, how to load, caveats. Never invent sources.
- Writing: the finished text in Markdown.
Finish with a 2-line "Handoff notes" section for the next step."""


def judge_prompt(question: str, request: str, candidates: dict) -> str:
    blocks = "\n\n".join(f"### Candidate: {n}\n{clip(t, 2500)}" for n, t in candidates.items())
    return f"""TASK=JUDGE
You are the decision maker. {question}

Project: {request}

Judge on: feasibility, specificity, correctness, fit for the project, cost/time.
Penalise vague or invented claims.

{blocks}

Reply with JSON only:
{{"scores":{{"<candidate name>": 0-10}},"winner":"<candidate name>","reason":"max 2 sentences"}}"""


def classify_prompt(message: str, history: list) -> str:
    hist = "\n".join(f"{m['role']}: {clip(m['content'], 300)}" for m in history[-6:])
    return f"""TASK=CLASSIFY
You are Drex, the brain of a multi-agent project builder. Decide if the user is making small talk
or questions (intent "chat") or asking you to build / research / plan a project (intent "project").
For "chat": write a short, friendly reply and gently mention you build projects with a team of agents.
For "project": write a one-line acknowledgement.

RECENT CONVERSATION:
{hist or '(none)'}

Reply with JSON only: {{"intent":"chat"|"project","reply":"..."}}
USER_MESSAGE:
{message}"""


def _done(done: list) -> str:
    if not done:
        return "(nothing yet)"
    return "\n".join(f"- Step {d['index']} {d['title']} (by {d['agent']}): {clip(d['text'], 1200)}" for d in done)
