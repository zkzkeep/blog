from __future__ import annotations
import hashlib
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from .config import BACKUPS_DIR, BLOG_ROOT

class BlogError(RuntimeError): pass
def log(message: str) -> None: print(message)
def run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=BLOG_ROOT, text=True, capture_output=True)
    if check and result.returncode:
        raise BlogError(f"命令失败：{' '.join(command)}\n{result.stderr.strip() or result.stdout.strip()}")
    return result
def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""): digest.update(chunk)
    return digest.hexdigest()
def safe_directory_name(name: str) -> str:
    name = re.sub(r'[\\/:*?"<>|]', "-", name.strip().replace("《", "").replace("》", ""))
    return re.sub(r"\s+", " ", name).strip(". -") or "untitled"
def backup_markdown(paths: list[Path]) -> Path | None:
    if not paths: return None
    target = BACKUPS_DIR / datetime.now().strftime("%Y%m%d-%H%M%S") / "markdown"
    for source in paths:
        destination = target / source.relative_to(BLOG_ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    return target
