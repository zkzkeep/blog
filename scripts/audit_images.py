#!/usr/bin/env python3
"""只读巡检：找出没有归档为文章编号图片的 Markdown。"""
from __future__ import annotations

from .config import CONTENT_DIR
from .organize_images import image_references, is_managed_image_reference
from .utils import log


def main() -> int:
    problems: list[str] = []
    for post in sorted(CONTENT_DIR.rglob("*.md")):
        for reference in image_references(post.read_text(encoding="utf-8")):
            if reference.startswith("data:"):
                continue
            if not is_managed_image_reference(reference, post):
                problems.append(f"{post.relative_to(CONTENT_DIR)} → {reference}")
    if not problems:
        log("图片巡检通过：所有文章图片均已编号并保存在本地。")
        return 0
    log(f"图片巡检发现 {len(problems)} 处待整理链接：")
    for problem in problems:
        log(f"  - {problem}")
    log("修复命令：python3 deploy.py --all-images")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
