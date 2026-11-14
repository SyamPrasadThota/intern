from app.agents.base import Agent
from app.config import MOCK, env, flag
from app.llm.client import LLMClient
from app.llm.mock import MockClient

GROQ = "https://api.groq.com/openai/v1"
GEMINI = "https://generativelanguage.googleapis.com/v1beta/openai"


def build_workers() -> list[Agent]:
    workers: list[Agent] = []

    if MOCK:
        mk = MockClient
        return [
            Agent("Scout", "Researcher", {"search", "analysis", "data"}, mk("Scout"), "You research."),
            Agent("Sage", "Planner & writer", {"write", "analysis"}, mk("Sage"), "You write."),
            Agent("Forge", "Coder", {"code", "data"}, mk("Forge"), "You code."),
            Agent("Flash", "Fast helper", {"data", "write", "analysis"}, mk("Flash"), "You help."),
        ]

    groq_key = env("GROQ_API_KEY")
    if groq_key:
        extra = {"tools": [{"type": "browser_search"}]} if flag("GROQ_BROWSER_SEARCH", True) else {}
        workers.append(Agent(
            "Scout", "Researcher (web search)", {"search", "analysis", "data", "code"},
            LLMClient("Scout", GROQ, groq_key, env("GROQ_BIG", "openai/gpt-oss-120b"), extra),
            "You are Scout, a rigorous research agent. Find real datasets, papers and tools. "
            "Cite sources with URLs. Never invent a source."))
        workers.append(Agent(
            "Flash", "Fast data & cleaning helper", {"data", "write", "analysis"},
            LLMClient("Flash", GROQ, groq_key, env("GROQ_SMALL", "openai/gpt-oss-20b")),
            "You are Flash, a fast, practical data engineer. Keep answers tight and concrete."))

    gem_key = env("GEMINI_API_KEY")
    if gem_key:
        workers.append(Agent(
            "Sage", "Planner & technical writer", {"write", "analysis", "data"},
            LLMClient("Sage", GEMINI, gem_key, env("GEMINI_MODEL", "gemini-2.5-flash")),
            "You are Sage, a senior engineer and technical writer. You plan carefully and write clear docs."))

    if flag("USE_OLLAMA", True):
        workers.append(Agent(
            "Forge", "Coder (local Qwen3-Coder)", {"code", "data"},
            LLMClient("Forge", env("OLLAMA_BASE_URL", "http://localhost:11434/v1"), "ollama",
                      env("OLLAMA_MODEL", "qwen3-coder"), timeout=600),
            "You are Forge, an expert software engineer. Write complete, runnable, well-structured code."))
    elif env("OPENROUTER_API_KEY"):
        workers.append(Agent(
            "Forge", "Coder (OpenRouter)", {"code", "data"},
            LLMClient("Forge", "https://openrouter.ai/api/v1", env("OPENROUTER_API_KEY"),
                      env("OPENROUTER_MODEL", "qwen/qwen3-coder:free")),
            "You are Forge, an expert software engineer. Write complete, runnable, well-structured code."))

    return workers


def build_drex_client():
    """Hosted Drex decision model (System One API). Needs DREX_API_KEY (nace_sk_...)."""
    from app.llm.drex_client import DrexClient
    if env("DREX_API_KEY"):
        return DrexClient(env("DREX_BASE_URL", "https://drex.nace.ai"), env("DREX_API_KEY"),
                          env("DREX_MODEL", "drex-latest"))
    return None


def build_helper_llm():
    """Normal LLM used for chat replies and as backup judge when Drex is unavailable."""
    if MOCK:
        return MockClient("Helper")
    if env("GROQ_API_KEY"):
        return LLMClient("Groq helper", GROQ, env("GROQ_API_KEY"), env("GROQ_SMALL", "openai/gpt-oss-20b"))
    if env("GEMINI_API_KEY"):
        return LLMClient("Gemini helper", GEMINI, env("GEMINI_API_KEY"), env("GEMINI_MODEL", "gemini-2.5-flash"))
    return None