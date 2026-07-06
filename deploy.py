#!/usr/bin/env python3
"""安全发布入口：只处理相对 Git HEAD 有改动的文章。"""
from __future__ import annotations
import argparse
import sys
from scripts.config import BLOG_ROOT
from scripts.git_tools import changed_markdown_files, deleted_markdown_files, commit_and_push
from scripts.hugo_tools import build_hugo, deploy_pages
from scripts.markdown import fix_markdown
from scripts.organize_images import garbage_collect_images, organize_images
from scripts.utils import BlogError, backup_markdown, log

TOTAL_STEPS = 6


def step(number: int, title: str) -> None:
    log("")
    log("──────────────────────────────────────────")
    log(f"第 {number}/{TOTAL_STEPS} 步：{title}")
    log("──────────────────────────────────────────")


def main() -> int:
    p = argparse.ArgumentParser(description="安全发布 Hugo 博客")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--no-push", action="store_true")
    p.add_argument("--all-images", action="store_true", help="巡检并整理全部文章图片（含历史外链图）")
    p.add_argument("--message", default="auto deploy")
    args = p.parse_args()
    try:
        # 第 1 步：看看有哪些文章需要发布。
        step(1, "检查有哪些文章需要发布")
        posts = changed_markdown_files()
        if args.all_images:
            from scripts.config import CONTENT_DIR
            posts = sorted(CONTENT_DIR.rglob("*.md"))
        deleted = deleted_markdown_files()
        if posts:
            scope = "全部文章（图片巡检）" if args.all_images else "新增或修改"
            log(f"检测到 {len(posts)} 篇{scope}的文章：")
            for path in posts:
                log(f"  · {path.relative_to(BLOG_ROOT)}")
        if deleted:
            log(f"检测到 {len(deleted)} 篇已删除的文章：")
            for path in deleted:
                log(f"  · {path.relative_to(BLOG_ROOT)}")
        if not posts and not deleted:
            log("没有检测到新增、修改或删除的文章。")
            log("如果你刚在 Typora 里改过，请确认已按 Cmd+S 保存后再发布。")
            log("（下面仍会检查未发布的旧改动、并确保 GitHub 是最新的。）")

        # 第 2 步：整理这些文章的图片和 Markdown。
        step(2, "整理图片、改写 Markdown")
        if posts or deleted:
            if not args.dry_run:
                log(f"已备份原文到：{backup_markdown(posts)}")
            images = organize_images(posts, dry_run=args.dry_run)
            if images.unresolved_refs:
                details = "\n".join(images.unresolved_refs)
                raise BlogError(f"以下本地图片未找到；为避免发布坏链接，已取消提交：\n{details}")
            markdown = fix_markdown(posts, dry_run=args.dry_run)
            affected = set(posts) | set(deleted) | images.created_files | markdown.changed_files
            log(f"整理完成，本轮涉及 {len(affected)} 个文件。")
        else:
            log("没有需要整理的文章，跳过。")
            affected = set()

        # 第 3 步：清理不再被任何文章引用的孤儿图片。
        step(3, "清理无用图片")
        # 无论本轮是否有文章变更，都巡检一遍孤儿图片：文章被删除、或图片被重新整理后
        # 留下的旧图，都会在这一步被清理，不依赖单独识别"删除"事件。
        orphans = garbage_collect_images(dry_run=args.dry_run)
        log(f"清理了 {len(orphans)} 张无用图片。" if orphans else "没有需要清理的图片。")
        affected |= orphans

        # 第 4 步：本地构建一遍，确保网站能正常生成。
        step(4, "构建 Hugo 网站")
        build_hugo(dry_run=args.dry_run)

        # 第 5 步：提交并推送文章源码。
        step(5, "提交文章并推送到 GitHub")
        if args.dry_run:
            log("[dry-run] 跳过提交和推送。")
        else:
            commit_and_push(affected, args.message, push=not args.no_push)

        # 第 6 步：把构建好的网页发布到 gh-pages——网站从这个分支伺服，
        # 漏掉这一步就是“源码推上去了、网站却不更新”。
        step(6, "发布网页，让网站上线")
        if args.no_push:
            log("--no-push 模式，跳过网页发布。")
        else:
            deploy_pages(dry_run=args.dry_run)
        log("")
        if args.dry_run:
            log("✅ 预览结束（dry-run），没有改动任何文件。")
        elif args.no_push:
            log("✅ 已在本地提交，未推送。")
        else:
            log("✅ 全部完成！网站正在更新，约 1 分钟后生效。")
            log("   网站地址：https://leesy.cc")
        return 0
    except BlogError as exc:
        log("")
        log(f"❌ 失败：{exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
