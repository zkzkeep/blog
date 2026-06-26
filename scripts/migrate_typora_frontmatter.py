#!/usr/bin/env python3
"""一次性将历史文章改为 Typora 可识别的 YAML 图片根目录。"""
from pathlib import Path
from .config import CONTENT_DIR
from .markdown import fix_markdown
from .utils import backup_markdown, log


def main() -> None:
    posts = sorted(CONTENT_DIR.rglob("*.md"))
    log(f"准备迁移 {len(posts)} 篇文章。")
    backup = backup_markdown(posts)
    log(f"已完整备份原文到：{backup}")
    result = fix_markdown(posts)
    log(f"已更新 {len(result.changed_files)} 篇文章的 Typora 图片配置。")


if __name__ == "__main__":
    main()
