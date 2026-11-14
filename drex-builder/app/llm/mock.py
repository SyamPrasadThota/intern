import json
import re


class MockClient:
    """Fake LLM so you can test the whole flow with no API keys (MOCK=1)."""

    def __init__(self, label):
        self.label = label
        self.model = "mock"

    async def chat(self, messages, temperature=0.4, json_mode=False) -> str:
        prompt = messages[-1]["content"]
        if "TASK=CLASSIFY" in prompt:
            msg = prompt.split("USER_MESSAGE:")[-1].strip().lower()
            if any(w in msg for w in ("build", "create", "make", "project", "classifier", "app")) and len(msg) > 25:
                return json.dumps({"intent": "project", "reply": "On it. Briefing the team."})
            return json.dumps({"intent": "chat", "reply": "Hi! Tell me what you want to build and I'll run the team."})
        if "TASK=PLAN" in prompt:
            return json.dumps({"steps": [
                {"title": "Choose a dataset", "needs": "search", "goal": "Pick the best public dataset"},
                {"title": "Clean the dataset", "needs": "code", "goal": "Write cleaning script"},
                {"title": "Write documentation", "needs": "write", "goal": "Write the README"}]})
        if "TASK=PROPOSE" in prompt:
            return json.dumps({"approach": f"{self.label} proposes a concrete approach.", "rationale": "Because it is practical.", "confidence": 7})
        if "TASK=JUDGE" in prompt:
            names = re.findall(r"### Candidate: (.+)", prompt)
            return json.dumps({"scores": {n: 6 + i for i, n in enumerate(names)}, "winner": names[-1], "reason": "Most concrete and realistic."})
        if "TASK=EXECUTE" in prompt:
            return f"Result by {self.label}.\n\n```python\n# file: example.py\nprint('hello from {self.label}')\n```\n"
        return "ok"
