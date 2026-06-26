#!/usr/bin/env python3
"""不依赖第三方包的自动发布监听器。"""
from __future__ import annotations
import subprocess
import sys
import time
from pathlib import Path
from .config import BLOG_ROOT, CONTENT_DIR
from .git_tools import changed_markdown_files
from .utils import log

POLL_SECONDS, QUIET_SECONDS = 3, 15
def signature() -> tuple[tuple[str, int, int], ...]:
    return tuple(sorted((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in CONTENT_DIR.rglob("*.md")))
def main() -> None:
    last = signature(); pending_at: float | None = None
    log("自动发布监听已启动；保存文章后 15 秒自动同步。Ctrl-C 停止。")
    if changed_markdown_files():
        log("检测到启动前已写完但未发布的文章，立即自动同步…")
        result = subprocess.run([sys.executable, "deploy.py"], cwd=BLOG_ROOT)
        last = signature()
        log("自动同步完成。" if result.returncode == 0 else "自动同步失败；请查看上方错误。")
    while True:
        time.sleep(POLL_SECONDS); current = signature()
        if current != last: last, pending_at = current, time.monotonic(); log("检测到文章保存，等待编辑结束…")
        if pending_at and time.monotonic() - pending_at >= QUIET_SECONDS:
            pending_at = None; log("开始自动同步…")
            result = subprocess.run([sys.executable, "deploy.py"], cwd=BLOG_ROOT)
            last = signature()
            log("自动同步完成。" if result.returncode == 0 else "自动同步失败；下次保存会重试。")
if __name__ == "__main__": main()
