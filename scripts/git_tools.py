from __future__ import annotations
from pathlib import Path
from .config import BLOG_ROOT, CONTENT_DIR
from .utils import BlogError, log, run
def changed_markdown_files() -> list[Path]:
    # 关闭 Git 对中文路径的 C 风格转义；否则 Path 会把带引号的转义串当成文件名。
    git_utf8 = ["git", "-c", "core.quotepath=false"]
    changed = run([*git_utf8, "diff", "--name-only", "HEAD", "--", "content"]).stdout.splitlines()
    untracked = run([*git_utf8, "ls-files", "--others", "--exclude-standard", "--", "content"]).stdout.splitlines()
    files = {BLOG_ROOT / name for name in changed + untracked if name.endswith(".md")}
    return sorted((p for p in files if p.is_file() and CONTENT_DIR in p.parents), key=str)


def deleted_markdown_files() -> list[Path]:
    """返回相对 HEAD 已删除的文章；路径已不存在也需要被 Git 提交。"""
    lines = run(["git", "-c", "core.quotepath=false", "diff", "--name-status", "HEAD", "--", "content"]).stdout.splitlines()
    deleted = []
    for line in lines:
        status, _, name = line.partition("\t")
        if status == "D" and name.endswith(".md"):
            deleted.append(BLOG_ROOT / name)
    return sorted(deleted, key=str)


def has_pending_markdown_changes() -> bool:
    return bool(changed_markdown_files() or deleted_markdown_files())
def commit_and_push(paths: set[Path], message: str, *, push: bool) -> None:
    if not paths: log("没有本轮文章或图片变更需要提交。"); return
    run(["git", "add", "--", *(str(p.relative_to(BLOG_ROOT)) for p in sorted(paths))])
    staged = run(["git", "diff", "--cached", "--quiet"], check=False)
    if staged.returncode == 0: log("没有可提交的本轮变更。"); return
    if staged.returncode != 1: raise BlogError("无法检查 Git 暂存区状态。")
    run(["git", "commit", "-m", message]); log("Git 提交成功。")
    if push: run(["git", "push"]); log("已推送到 GitHub，Pages 将自动发布。")
