import json

from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.agents.registry import build_drex_client, build_helper_llm, build_workers
from app.config import MOCK, ROOT, WORKSPACE
from app.orchestrator.drex import Drex
from app.orchestrator.pipeline import ProjectPipeline

app = FastAPI(title="Drex Project Builder")

workers = build_workers()
drex_client = build_drex_client()
helper = build_helper_llm()
drex = Drex(drex_client, helper) if (drex_client or helper) else None
pipeline = ProjectPipeline(drex, workers) if drex else None


class ChatIn(BaseModel):
    message: str
    history: list[dict] = []


@app.get("/api/agents")
def agents():
    return {"mock": MOCK,
            "drex": "Drex (hosted)" if drex_client else "no Drex key: backup judge",
            "workers": [w.info() for w in workers]}


@app.post("/api/chat")
async def chat(body: ChatIn):
    async def stream():
        def line(obj):
            return json.dumps(obj) + "\n"

        if not drex or not workers:
            yield line({"type": "error", "text": "No agents configured. Copy .env.example to .env and add keys (or set MOCK=1)."})
            return

        decision = await drex.classify(body.message, body.history)
        if decision["intent"] == "chat":
            yield line({"type": "reply", "text": decision.get("reply") or "Hi! What would you like to build?"})
            return
        if decision["intent"] != "project":
            yield line({"type": "error", "text": decision["reply"]})
            return

        conf = decision.get("confidence")
        note = f" (Drex is {conf:.0%} sure)" if conf else ""
        yield line({"type": "reply", "text": f"This looks like a project{note}. Briefing the team."})
        async for event in pipeline.run(body.message):
            yield line(event)

    return StreamingResponse(stream(), media_type="application/x-ndjson")


app.mount("/workspace", StaticFiles(directory=WORKSPACE), name="workspace")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")