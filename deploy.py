#!/usr/bin/env python3
"""安全发布入口：只处理相对 Git HEAD 有改动的文章。"""
from __future__ import annotations
import argparse
import sys
from scripts.git_tools import changed_markdown_files, deleted_markdown_files, commit_and_push
from scripts.hugo_tools import build_hugo
from scripts.markdown import fix_markdown
from scripts.organize_images import garbage_collect_images, organize_images
from scripts.utils import BlogError, backup_markdown, log


def main() -> int:
    p = argparse.ArgumentParser(description="安全发布 Hugo 博客")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--no-push", action="store_true")
    p.add_argument("--all-images", action="store_true", help="巡检并整理全部文章图片（含历史外链图）")
    p.add_argument("--message", default="auto deploy")
    args = p.parse_args()
    try:
        posts = changed_markdown_files()
        if args.all_images:
            from scripts.config import CONTENT_DIR
            posts = sorted(CONTENT_DIR.rglob("*.md"))
        deleted = deleted_markdown_files()
        if posts or deleted:
            scope = "全部文章图片巡检" if args.all_images else "新增或修改"
            log(f"检测到 {len(posts)} 篇{scope}、{len(deleted)} 篇已删除的文章。")
            if not args.dry_run:
                log(f"已备份原文到：{backup_markdown(posts)}")
            images = organize_images(posts, dry_run=args.dry_run)
            if images.unresolved_refs:
                details = "\n".join(images.unresolved_refs)
                raise BlogError(f"以下本地图片未找到；为避免发布坏链接，已取消提交：\n{details}")
            markdown = fix_markdown(posts, dry_run=args.dry_run)
            affected = set(posts) | set(deleted) | images.created_files | markdown.changed_files
        else:
            log("没有新增或修改的 Markdown；跳过图片整理和文章改写。")
            affected = set()
        # 无论本轮是否有文章变更，都巡检一遍孤儿图片：文章被删除、或图片被重新整理后
        # 留下的旧图，都会在这一步被清理，不依赖单独识别"删除"事件。
        affected |= garbage_collect_images(dry_run=args.dry_run)
        build_hugo(dry_run=args.dry_run)
        if not args.dry_run:
            commit_and_push(affected, args.message, push=not args.no_push)
        return 0
    except BlogError as exc:
        log(f"失败：{exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
