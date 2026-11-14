import httpx

from app.llm.client import LLMError
from app.utils import clip


class DrexClient:
    """Hosted Drex (System One API): POST {base}/v1/systemone.
    Drex does not generate text. It reads a `state` and answers typed questions
    with a probability for every option."""

    label = "Drex"

    def __init__(self, base_url, api_key, model="drex-latest", timeout=60):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    async def choose(self, state: str, instructions: str, options: dict) -> dict:
        """Pick one option. Returns {"choice", "confidence", "probabilities"}."""
        body = {
            "model": self.model,
            "state": clip(state, 12000),
            "questions": {
                "pick": {
                    "type": "choice",
                    "instructions": instructions,
                    "criteria": {k: clip(v, 1500) for k, v in options.items()},
                }
            },
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as http:
                r = await http.post(f"{self.base_url}/v1/systemone", json=body, headers=headers)
        except httpx.HTTPError as e:
            raise LLMError(f"Drex network error: {e}")
        if r.status_code >= 400:
            raise LLMError(f"Drex HTTP {r.status_code}: {r.text[:300]}")
        try:
            ans = r.json()["answers"]["pick"]
            return {"choice": ans["choice"], "confidence": float(ans.get("confidence", 0)),
                    "probabilities": ans.get("probabilities", {})}
        except Exception as e:
            raise LLMError(f"Drex unexpected response ({e}): {r.text[:300]}")