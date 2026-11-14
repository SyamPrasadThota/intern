import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

WORKSPACE = ROOT / "workspace"
WORKSPACE.mkdir(exist_ok=True)


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def flag(name: str, default: bool = False) -> bool:
    return env(name, "1" if default else "0").lower() in ("1", "true", "yes", "on")


MOCK = flag("MOCK")
MAX_STEPS = int(env("MAX_STEPS", "7"))
