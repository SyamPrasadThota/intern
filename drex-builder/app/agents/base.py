from app.llm.client import LLMError
from app.utils import extract_json


class Agent:
    def __init__(self, name, role, capabilities, client, persona):
        self.name = name
        self.role = role
        self.capabilities = set(capabilities)
        self.client = client
        self.persona = persona

    async def ask(self, prompt, json_mode=False, temperature=0.4) -> str:
        msgs = [{"role": "system", "content": self.persona}, {"role": "user", "content": prompt}]
        return await self.client.chat(msgs, temperature=temperature, json_mode=json_mode)

    async def ask_json(self, prompt):
        """Returns parsed JSON or None. Never raises."""
        try:
            raw = await self.ask(prompt, json_mode=True)
        except LLMError as e:
            print(f"[{self.name} error] {e}")
            return None
        return extract_json(raw)

    def info(self):
        return {"name": self.name, "role": self.role, "model": getattr(self.client, "model", "?"),
                "capabilities": sorted(self.capabilities)}