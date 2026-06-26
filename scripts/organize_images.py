from __future__ import annotations
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen
from .config import BLOG_ROOT, IMAGE_EXTENSIONS, IMAGES_DIR, STATIC_DIR
from .utils import log, safe_directory_name

IMAGE = re.compile(r"!\[([^\]]*)\]\((<[^>]+>|[^)\s]+)(\s+[^)]*)?\)")
FENCED_CODE = re.compile(r"(?ms)^[ \t]*(?P<fence>`{3,}|~{3,}).*?^[ \t]*(?P=fence)[ \t]*$")
@dataclass
class ImageResult:
    created_files: set[Path] = field(default_factory=set)
    unresolved_refs: list[str] = field(default_factory=list)
    removed_temp_files: set[Path] = field(default_factory=set)


def _must_import_locally(reference: str) -> bool:
    """仅阻止 Typora 刚插入、必须复制到博客的本地图片路径。

    历史文章中的 /images/... 和 ../images/... 可能是教程示例；保留警告但不阻断发布。
    """
    return reference.startswith(("/../", "file://", "/Users/", "/private/"))
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


def _remote_extension(reference: str, content_type: str = "") -> str:
    """优先使用 URL 后缀；没有后缀时再根据响应类型判断。"""
    suffix = Path(urlparse(reference).path).suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        return suffix
    subtype = content_type.split(";", 1)[0].lower().removeprefix("image/")
    aliases = {"jpeg": ".jpg", "svg+xml": ".svg", "x-icon": ".ico"}
    suffix = aliases.get(subtype, f".{subtype}" if subtype else "")
    return suffix if suffix in IMAGE_EXTENSIONS else ".jpg"


def _download_remote_image(reference: str, target: Path, *, dry_run: bool) -> bool:
    """将文章中的外链图片收归到 static；失败时保持原链接，绝不破坏文章。"""
    if target.exists():
        return True
    if dry_run:
        log(f"[dry-run] 将下载外链图片：{reference} → {target}"); return True
    try:
        request = Request(reference, headers={"User-Agent": "Mozilla/5.0 (blog image organizer)"})
        with urlopen(request, timeout=20) as response:
            content_type = response.headers.get_content_type()
            if not content_type.startswith("image/"):
                log(f"警告：外链不是图片，保持原链接不动：{reference}"); return False
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("wb") as output:
                shutil.copyfileobj(response, output)
        log(f"已下载外链图片：{target.relative_to(BLOG_ROOT)}")
        return True
    except Exception as exc:
        log(f"警告：外链图片下载失败，保持原链接不动：{reference}（{exc}）")
        return False


def is_managed_image_reference(reference: str, post: Path) -> bool:
    """返回图片是否已经是该文章下编号且实际存在的静态资源。"""
    raw = reference.strip().strip("<>")
    folder = safe_directory_name(post.stem)
    prefix = f"/images/{folder}/"
    if not raw.startswith(prefix):
        return False
    filename = raw.removeprefix(prefix)
    if not re.fullmatch(r"[1-9]\d*\.(?:avif|gif|jpeg|jpg|png|svg|webp)", filename, flags=re.I):
        return False
    return (STATIC_DIR / raw.lstrip("/")).is_file()


def image_references(text: str) -> list[str]:
    references: list[str] = []
    cursor = 0
    for code_block in FENCED_CODE.finditer(text):
        references.extend(match.group(2).strip("<>") for match in IMAGE.finditer(text[cursor:code_block.start()]))
        cursor = code_block.end()
    references.extend(match.group(2).strip("<>") for match in IMAGE.finditer(text[cursor:]))
    return references
def organize_images(posts: list[Path], *, dry_run: bool = False) -> ImageResult:
    """复制本轮文章的本地图片；从不移动、覆盖或删除原图。"""
    result = ImageResult()
    temporary_root_copies: set[Path] = set()
    for post in posts:
        text, missing = post.read_text(encoding="utf-8"), []
        image_number = 0
        def replace(match: re.Match[str]) -> str:
            nonlocal image_number
            alt, reference, title = match.groups(); raw = reference.strip("<>")
            # 外链图片也归档到博客本地，避免图床失效，并与本地图片一样按顺序编号。
            if raw.startswith(("http://", "https://")):
                image_number += 1
                target = IMAGES_DIR / safe_directory_name(post.stem) / f"{image_number}{_remote_extension(raw)}"
                if _download_remote_image(raw, target, dry_run=dry_run):
                    if not dry_run:
                        result.created_files.add(target)
                    return f"![{alt}](/{target.relative_to(STATIC_DIR).as_posix()}{title or ''})"
                return match.group(0)
            source = _local_source(reference, post)
            if source is None:
                if not raw.startswith("data:"): missing.append(raw)
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
            # Typora 在设置图片根目录后，粘贴图片会生成 /../文件名：
            # 这是博客根目录的临时副本，待全部文章处理完再安全清理。
            if raw.startswith("/../") and source.parent.resolve() == BLOG_ROOT:
                temporary_root_copies.add(source)
            return f"![{alt}](/{target.relative_to(STATIC_DIR).as_posix()}{title or ''})"
        # 教程中的 Markdown 示例常包含图片写法；代码块原样保留，不应当被当成真实图片。
        fragments: list[str] = []
        cursor = 0
        for code_block in FENCED_CODE.finditer(text):
            fragments.append(IMAGE.sub(replace, text[cursor:code_block.start()]))
            fragments.append(code_block.group(0))
            cursor = code_block.end()
        fragments.append(IMAGE.sub(replace, text[cursor:]))
        updated = "".join(fragments)
        for reference in missing: log(f"警告：未找到图片，保持原链接不动：{post.name} → {reference}")
        result.unresolved_refs.extend(
            f"{post.name} → {reference}" for reference in missing if _must_import_locally(reference)
        )
        if updated != text:
            if dry_run: log(f"[dry-run] 将标准化图片链接：{post.relative_to(BLOG_ROOT)}")
            else: post.write_text(updated, encoding="utf-8")
    # 只有整轮图片检查都通过才删除临时副本；失败时保留现场供修复。
    if not dry_run and not result.unresolved_refs:
        for source in temporary_root_copies:
            if source.is_file():
                source.unlink()
                result.removed_temp_files.add(source)
                log(f"已清理 Typora 根目录临时图片：{source.name}")
    return result
