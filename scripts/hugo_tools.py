from __future__ import annotations
import shutil
import tempfile
from pathlib import Path
from .config import BLOG_ROOT
from .utils import BlogError, log, run

PUBLIC_DIR = BLOG_ROOT / "public"


def build_hugo(*, dry_run: bool = False) -> None:
    if dry_run: log("[dry-run] 将运行 Hugo 构建。"); return
    if shutil.which("hugo") is None: raise BlogError("找不到 hugo；请先安装 Hugo 并确认它在 PATH 中。")
    result = run(["hugo", "--minify"], check=False)
    if result.returncode: raise BlogError(result.stderr.strip() or result.stdout.strip())
    log("Hugo 构建成功。")


def deploy_pages(*, dry_run: bool = False) -> None:
    """把 public/ 构建产物发布到 gh-pages 分支——网站真正伺服的分支。

    以前这一步靠手动执行，漏掉就会出现“main 推上去了、网站却不更新”。
    做法：在临时目录挂一个 gh-pages 的 worktree，用 rsync 同步产物后提交推送。
    """
    if dry_run:
        log("[dry-run] 将把构建产物发布到 gh-pages。")
        return
    if not (PUBLIC_DIR / "index.html").is_file():
        raise BlogError("public/ 里没有构建产物；Hugo 构建可能没有成功。")
    run(["git", "fetch", "origin", "gh-pages"])
    worktree = Path(tempfile.mkdtemp(prefix="blog-gh-pages-"))
    try:
        # --force -B：以远端 gh-pages 为准重建本地分支，避免历史遗留的本地分支干扰。
        run(["git", "worktree", "add", "--force", "-B", "gh-pages", str(worktree), "origin/gh-pages"])
        run(["rsync", "-a", "--delete", "--exclude", ".git", f"{PUBLIC_DIR}/", f"{worktree}/"])
        run(["git", "-C", str(worktree), "add", "-A"])
        staged = run(["git", "-C", str(worktree), "diff", "--cached", "--quiet"], check=False)
        if staged.returncode == 0:
            log("网页内容和线上一致，无需发布。")
            return
        if staged.returncode != 1:
            raise BlogError("无法检查 gh-pages 暂存区状态。")
        head = run(["git", "rev-parse", "HEAD"]).stdout.strip()
        run(["git", "-C", str(worktree), "commit", "-m", f"deploy: {head}"])
        run(["git", "-C", str(worktree), "push", "origin", "gh-pages"])
        log("网页已发布，线上正在更新（约 1 分钟生效）。")
    finally:
        run(["git", "worktree", "remove", "--force", str(worktree)], check=False)
        run(["git", "worktree", "prune"], check=False)
