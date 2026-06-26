#!/usr/bin/env python3
"""安全发布入口：只处理相对 Git HEAD 有改动的文章。"""
from __future__ import annotations
import argparse
import sys
from scripts.git_tools import changed_markdown_files, commit_and_push
from scripts.hugo_tools import build_hugo
from scripts.markdown import fix_markdown
from scripts.organize_images import organize_images
from scripts.utils import BlogError, backup_markdown, log


def main() -> int:
    p = argparse.ArgumentParser(description="安全发布 Hugo 博客")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--no-push", action="store_true")
    p.add_argument("--message", default="auto deploy")
    args = p.parse_args()
    try:
        posts = changed_markdown_files()
        if posts:
            log(f"检测到 {len(posts)} 篇新增或修改的文章。")
            if not args.dry_run:
                log(f"已备份原文到：{backup_markdown(posts)}")
            images = organize_images(posts, dry_run=args.dry_run)
            if images.unresolved_refs:
                details = "\n".join(images.unresolved_refs)
                raise BlogError(f"以下本地图片未找到；为避免发布坏链接，已取消提交：\n{details}")
            markdown = fix_markdown(posts, dry_run=args.dry_run)
            affected = set(posts) | images.created_files | markdown.changed_files
        else:
            log("没有新增或修改的 Markdown；跳过图片整理和文章改写。")
            affected = set()
        build_hugo(dry_run=args.dry_run)
        if not args.dry_run:
            commit_and_push(affected, args.message, push=not args.no_push)
        return 0
    except BlogError as exc:
        log(f"失败：{exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
