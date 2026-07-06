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


def _unpushed_commit_count() -> int | None:
    """本地领先上游多少个提交；没有配置上游时返回 None。"""
    upstream = run(["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], check=False)
    if upstream.returncode:
        return None
    ahead = run(["git", "rev-list", "--count", "@{u}..HEAD"], check=False).stdout.strip()
    return int(ahead) if ahead.isdigit() else None


def commit_and_push(paths: set[Path], message: str, *, push: bool) -> None:
    committed = False
    if not paths:
        log("没有本轮文章或图片变更需要提交。")
    else:
        relative = sorted(str(p.relative_to(BLOG_ROOT)) for p in paths)
        # 被清理的孤儿图片可能从未被 Git 追踪过；对这类“不存在也不在库里”的路径，
        # git add 会直接报错退出，所以先过滤掉，只保留真正需要暂存的路径。
        tracked = set(run(["git", "-c", "core.quotepath=false", "ls-files", "--", *relative]).stdout.splitlines())
        stageable = [name for name in relative if name in tracked or (BLOG_ROOT / name).exists()]
        if not stageable:
            log("没有可提交的本轮变更。")
        else:
            run(["git", "add", "--", *stageable])
            staged = run(["git", "diff", "--cached", "--quiet"], check=False)
            if staged.returncode == 1:
                run(["git", "commit", "-m", message])
                log("Git 提交成功。")
                committed = True
            elif staged.returncode == 0:
                log("没有可提交的本轮变更。")
            else:
                raise BlogError("无法检查 Git 暂存区状态。")

    if not push:
        return
    # 即便本轮没有新提交，也要把上一次“提交成功但推送失败”的旧提交补推上去，
    # 否则那些改动会一直停在本地，线上永远不更新（用户会以为“改了没生效”）。
    ahead = _unpushed_commit_count()
    if committed or (ahead is None) or ahead > 0:
        run(["git", "push"])
        log("已推送到 GitHub，Pages 将自动发布。")
    else:
        log("本地与 GitHub 已是最新，无需推送。")
