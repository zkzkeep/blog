#!/usr/bin/env python3
"""安装每天一次的图片只读巡检（macOS launchd）。"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .config import BLOG_ROOT
from .utils import log

LABEL = "cc.leesy.blog-image-audit"
PLIST_NAME = "com.leesy.blog-image-audit.plist"


def main() -> int:
    source = BLOG_ROOT / "scripts" / PLIST_NAME
    target = Path.home() / "Library" / "LaunchAgents" / source.name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    uid = str(__import__("os").getuid())
    subprocess.run(["launchctl", "bootout", f"gui/{uid}/{LABEL}"], capture_output=True)
    result = subprocess.run(["launchctl", "bootstrap", f"gui/{uid}", str(target)], text=True, capture_output=True)
    if result.returncode:
        log(f"安装失败：{result.stderr.strip() or result.stdout.strip()}")
        return 1
    log("图片巡检已安装：登录后立即检查，此后每天 09:00 检查一次。")
    log("日志位置：~/Library/Logs/blog-image-audit.log")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
