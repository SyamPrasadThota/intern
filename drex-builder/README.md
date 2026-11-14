# Drex Builder: multi-agent project builder

Chat UI where **Drex** (the brain) decides whether you are chatting or asking for a project.
For projects: every agent proposes a plan, Drex picks the best, then for each step every
capable agent proposes an approach, Drex picks the best, and the winner does the work.
Results land in `workspace/<project>/` (step notes in `steps/`, extracted code in `code/`).

## Run
1. `python -m venv .venv && source .venv/bin/activate`  (Windows: `.venv\Scripts\activate`)
2. `pip install -r requirements.txt`
3. `cp .env.example .env` and fill in keys
4. (Optional coder) `ollama pull qwen3-coder`
5. `python run.py` then open http://127.0.0.1:8000

Try it without keys first: set `MOCK=1` in `.env`.

## Layout
- `app/main.py` API + streaming endpoint
- `app/orchestrator/drex.py` Drex: classify + judge
- `app/orchestrator/pipeline.py` plan, propose, judge, execute loop
- `app/orchestrator/workspace.py` saves outputs and extracts code files
- `app/agents/` agent class, prompts, and the roster (`registry.py`)
- `app/llm/` OpenAI-compatible client + mock
- `static/` chat UI
