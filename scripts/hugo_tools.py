from __future__ import annotations
import shutil
from .utils import BlogError, log, run
def build_hugo(*, dry_run: bool = False) -> None:
    if dry_run: log("[dry-run] 将运行 Hugo 构建。"); return
    if shutil.which("hugo") is None: raise BlogError("找不到 hugo；请先安装 Hugo 并确认它在 PATH 中。")
    result = run(["hugo", "--minify"], check=False)
    if result.returncode: raise BlogError(result.stderr.strip() or result.stdout.strip())
    log("Hugo 构建成功。")
