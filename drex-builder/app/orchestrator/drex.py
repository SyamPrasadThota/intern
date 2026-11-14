from app.agents import prompts
from app.llm.client import LLMError
from app.utils import extract_json

CHAT_SYSTEM = ("You are Drex, the friendly front desk of a multi-agent project builder. "
               "Reply briefly (1-3 sentences). You build projects (datasets, research, code, docs) "
               "with a team of agents, so invite the user to describe a project.")

INTENT_OPTIONS = {
    "chat": "Greeting, small talk, thanks, or a general question. NOT a request to build something.",
    "project": "A request to build, create, research, plan or implement a software, data or AI project.",
}


class Drex:
    """Decision layer. The hosted Drex model makes the decisions (classify, pick best plan/proposal).
    A normal LLM (`helper`) writes chat replies and acts as backup judge if Drex is unreachable."""

    def __init__(self, drex_client, helper=None):
        self.client = drex_client
        self.helper = helper
        self.label = "Drex" if drex_client else "Drex (backup judge)"
        self.last_error = ""

    # ---------- chat vs project ----------
    async def classify(self, message: str, history: list) -> dict:
        hist = "\n".join(f"{m['role']}: {m['content'][:300]}" for m in history[-6:])
        state = f"Recent conversation:\n{hist or '(none)'}\n\nLatest user message:\n{message}"

        if self.client:
            try:
                ans = await self.client.choose(state, "Is the latest user message small talk or a project request?", INTENT_OPTIONS)
                intent, conf = ans["choice"], ans["confidence"]
                reply = await self._chat_reply(message, history) if intent == "chat" else ""
                return {"intent": intent, "confidence": conf, "reply": reply}
            except LLMError as e:
                self.last_error = str(e)
                print("[Drex error]", e)

        if self.helper:  # backup: ask a normal LLM
            try:
                raw = await self.helper.chat([{"role": "user", "content": prompts.classify_prompt(message, history)}],
                                             temperature=0.2, json_mode=True)
                data = extract_json(raw)
                if isinstance(data, dict) and data.get("intent") in ("chat", "project"):
                    return {"intent": data["intent"], "confidence": None, "reply": data.get("reply", "")}
            except LLMError as e:
                self.last_error = str(e)
                print("[Backup classify error]", e)
        return {"intent": "error", "reply": f"Could not classify the message: {self.last_error or 'no model available'}"}

    async def _chat_reply(self, message, history) -> str:
        if not self.helper:
            return "Hi! Tell me what you'd like to build and I'll put my team on it."
        msgs = [{"role": "system", "content": CHAT_SYSTEM}] + history[-6:] + [{"role": "user", "content": message}]
        try:
            return await self.helper.chat(msgs, temperature=0.6)
        except LLMError as e:
            print("[Chat reply error]", e)
            return "Hi! Tell me what you'd like to build and I'll put my team on it."

    # ---------- pick the best candidate ----------
    async def judge(self, question: str, request: str, candidates: dict) -> dict:
        names = list(candidates)
        if len(names) == 1:
            return {"winner": names[0], "scores": {names[0]: 10}, "reason": "Only one candidate."}

        if self.client:
            try:
                state = (f"Project: {request}\n\nDecision: {question}\n"
                         "Criteria: feasibility, specificity, correctness, fit for the project, cost and time. "
                         "Penalise vague or invented claims.")
                ans = await self.client.choose(state, question, candidates)
                probs = ans["probabilities"]
                scores = {n: round(float(probs.get(n, 0)) * 10, 1) for n in names}
                winner = ans["choice"] if ans["choice"] in candidates else max(scores, key=scores.get)
                self.label = "Drex"
                return {"winner": winner, "scores": scores,
                        "reason": f"Drex confidence {ans['confidence']:.0%}. Scores are Drex's probability x10."}
            except LLMError as e:
                self.last_error = str(e)
                print("[Drex error]", e)

        if self.helper:
            try:
                raw = await self.helper.chat(
                    [{"role": "system", "content": "Reply with valid JSON only."},
                     {"role": "user", "content": prompts.judge_prompt(question, request, candidates)}],
                    temperature=0.1, json_mode=True)
                data = extract_json(raw)
                if isinstance(data, dict) and data.get("winner") in candidates:
                    scores = {}
                    for n in names:
                        try:
                            scores[n] = float((data.get("scores") or {}).get(n, 0))
                        except (TypeError, ValueError):
                            scores[n] = 0.0
                    self.label = "Drex (backup judge)"
                    return {"winner": data["winner"], "scores": scores, "reason": data.get("reason", "")}
            except LLMError as e:
                print("[Backup judge error]", e)

        self.label = "Default pick"
        return {"winner": names[0], "scores": {n: 0 for n in names}, "reason": "No judge was reachable; used the first candidate."}