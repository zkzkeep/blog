from __future__ import annotations
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote, urlparse
from .config import BLOG_ROOT, IMAGE_EXTENSIONS, IMAGES_DIR, STATIC_DIR
from .utils import log, safe_directory_name

IMAGE = re.compile(r"!\[([^\]]*)\]\((<[^>]+>|[^)\s]+)(\s+[^)]*)?\)")
@dataclass
class ImageResult: created_files: set[Path] = field(default_factory=set)
def _local_source(reference: str, post: Path) -> Path | None:
    reference = unquote(reference.strip().strip("<>"))
    if reference.startswith(("http://", "https://", "data:")): return None
    if reference.startswith("file://"): reference = urlparse(reference).path
    if reference.startswith("/images/"):
        candidate = STATIC_DIR / reference.lstrip("/")
    elif reference.startswith("/../"):
        # Typora 的图片根目录设为 static 后，根目录图片会写成 /../文件名。
        candidate = (STATIC_DIR / reference.lstrip("/")).resolve()
    else:
        candidate = Path(reference) if reference.startswith("/") else (post.parent / reference).resolve()
    return candidate if candidate.is_file() else None
def organize_images(posts: list[Path], *, dry_run: bool = False) -> ImageResult:
    """复制本轮文章的本地图片；从不移动、覆盖或删除原图。"""
    result = ImageResult()
    for post in posts:
        text, missing = post.read_text(encoding="utf-8"), []
        image_number = 0
        def replace(match: re.Match[str]) -> str:
            nonlocal image_number
            alt, reference, title = match.groups(); source = _local_source(reference, post); raw = reference.strip("<>")
            if source is None:
                if not raw.startswith(("http://", "https://", "data:")): missing.append(raw)
                return match.group(0)
            if source.suffix.lower() not in IMAGE_EXTENSIONS: return match.group(0)
            image_number += 1
            # 同一篇文章按出现顺序编号：1.png、2.jpg……，便于人工管理。
            target = IMAGES_DIR / safe_directory_name(post.stem) / f"{image_number}{source.suffix.lower()}"
            if source.resolve() != target.resolve() and not target.exists():
                if dry_run: log(f"[dry-run] 将复制图片：{source} → {target}")
                else:
                    target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, target); result.created_files.add(target)
                    log(f"已复制图片：{source.name} → {target.relative_to(BLOG_ROOT)}")
            return f"![{alt}](/{target.relative_to(STATIC_DIR).as_posix()}{title or ''})"
        updated = IMAGE.sub(replace, text)
        for reference in missing: log(f"警告：未找到图片，保持原链接不动：{post.name} → {reference}")
        if updated != text:
            if dry_run: log(f"[dry-run] 将标准化图片链接：{post.relative_to(BLOG_ROOT)}")
            else: post.write_text(updated, encoding="utf-8")
    return result
