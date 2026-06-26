#!/usr/bin/env python3

import re
import shutil
from pathlib import Path

# ===========================
# Hugo 博客根目录
# ===========================
BLOG_ROOT = Path.home() / "Documents" / "blog"

POSTS_DIR = BLOG_ROOT / "content" / "posts"

IMAGES_ROOT = BLOG_ROOT / "static" / "images"

TEMP_DIR = IMAGES_ROOT / "未整理"

# 匹配 Markdown 图片
pattern = re.compile(r'!\[(.*?)\]\((.*?)\)')

total = 0

for md in POSTS_DIR.rglob("*.md"):

    article_name = md.stem

    article_image_dir = IMAGES_ROOT / article_name

    article_image_dir.mkdir(exist_ok=True)

    text = md.read_text(encoding="utf-8")

    def replace(match):

        global total

        alt = match.group(1)

        image_path = match.group(2)

        if "/Users/" not in image_path:
            return match.group(0)

        source = Path(image_path)

        if not source.exists():
            print(f"找不到图片：{source}")
            return match.group(0)

        destination = article_image_dir / source.name

        if not destination.exists():
            shutil.move(str(source), str(destination))

        new_path = f"/images/{article_name}/{source.name}"

        total += 1

        print(f"✓ {source.name} -> {article_name}")

        return f"![{alt}]({new_path})"

    new_text = pattern.sub(replace, text)

    md.write_text(new_text, encoding="utf-8")

print()
print("======================")
print(f"整理完成，共处理 {total} 张图片")
print("======================")