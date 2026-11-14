import re
import shutil
from pathlib import Path

from app.config import WORKSPACE
from app.utils import slugify

EXT = {"python": "py", "py": "py", "javascript": "js", "js": "js", "typescript": "ts", "bash": "sh",
       "sh": "sh", "json": "json", "yaml": "yml", "sql": "sql", "html": "html", "css": "css",
       "markdown": "md", "text": "txt", "": "txt"}
FENCE = re.compile(r"```([\w+-]*)\n(.*?)```", re.S)
HINT = re.compile(r"^\s*(?:#|//|--|<!--)\s*file:\s*(\S+)", re.I)


def new_project_dir(request: str) -> Path:
    base = slugify(request)
    path, n = WORKSPACE / base, 2
    while path.exists():
        path = WORKSPACE / f"{base}-{n}"
        n += 1
    (path / "steps").mkdir(parents=True)
    (path / "code").mkdir()
    return path


def save_step(project: Path, index: int, title: str, agent: str, text: str) -> list[str]:
    """Save the step as markdown and pull any code blocks out into code/. Returns relative paths."""
    files = []
    md = project / "steps" / f"{index:02d}-{slugify(title, 30)}.md"
    md.write_text(f"# Step {index}: {title}\n\n_Done by {agent}_\n\n{text}\n", encoding="utf-8")
    files.append(str(md.relative_to(project)))
    for n, m in enumerate(FENCE.finditer(text), 1):
        lang, body = m.group(1).lower(), m.group(2)
        first = body.splitlines()[0] if body.strip() else ""
        hint = HINT.match(first)
        if hint:
            name = Path(hint.group(1)).as_posix().lstrip("/")
            name = "/".join(p for p in name.split("/") if p not in ("..", "."))
        else:
            name = f"step{index:02d}_block{n}.{EXT.get(lang, 'txt')}"
        target = project / "code" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
        files.append(str(target.relative_to(project)))
    return files


def write_index(project: Path, request: str, done: list):
    lines = [f"# {request}\n", "Built by the Drex multi-agent team.\n", "## Steps\n"]
    for d in done:
        lines.append(f"{d['index']}. **{d['title']}** by {d['agent']}: " + ", ".join(f"`{f}`" for f in d["files"]))
    (project / "INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_zip(project: Path) -> Path:
    """Zip the whole project folder (steps/, code/, INDEX.md) next to it in workspace/."""
    out = shutil.make_archive(str(project.parent / project.name), "zip",
                              root_dir=project.parent, base_dir=project.name)
    return Path(out)