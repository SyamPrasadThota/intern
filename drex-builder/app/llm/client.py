import asyncio

import httpx

from app.utils import strip_think


class LLMError(Exception):
    pass


class LLMClient:
    """Minimal OpenAI-compatible chat client.
    Works for Groq, Gemini (OpenAI endpoint), OpenRouter, Ollama, DeepInfra and Drex."""

    def __init__(self, label, base_url, api_key, model, extra_body=None, timeout=180):
        self.label = label
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or "none"
        self.model = model
        self.extra_body = extra_body or {}
        self.timeout = timeout

    async def chat(self, messages, temperature=0.4, json_mode=False) -> str:
        body = {"model": self.model, "messages": messages, "temperature": temperature}
        body.update(self.extra_body)
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        url = f"{self.base_url}/chat/completions"

        last = ""
        for attempt in range(4):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as http:
                    r = await http.post(url, json=body, headers=headers)
            except httpx.HTTPError as e:
                last = f"network error: {e}"
                await asyncio.sleep(2 * (attempt + 1))
                continue

            if r.status_code in (429, 500, 502, 503, 504):
                last = f"{r.status_code}: {r.text[:200]}"
                wait = float(r.headers.get("retry-after", 2 * (attempt + 1)))
                await asyncio.sleep(min(wait, 20))
                continue
            if r.status_code == 400:
                # Some models don't support tools / json mode: strip and retry.
                if "tools" in body:
                    body.pop("tools")
                    continue
                if "response_format" in body:
                    body.pop("response_format")
                    continue
            if r.status_code >= 400:
                raise LLMError(f"{self.label} -> HTTP {r.status_code}: {r.text[:300]}")
            try:
                content = r.json()["choices"][0]["message"].get("content") or ""
            except Exception as e:
                raise LLMError(f"{self.label} bad response: {e}")
            return strip_think(content)
        raise LLMError(f"{self.label} failed after retries ({last})")
