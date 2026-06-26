from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from .config import TYPORA_ROOT_URL
from .utils import log

@dataclass
class MarkdownResult: changed_files: set[Path] = field(default_factory=set)
def _with_typora_root(text: str) -> str:
    if text.startswith("+++\n"):
        end = text.find("\n+++\n", 4)
        if end == -1: return text
        # Typora 的 typora-root-url 只支持 YAML；将简单的 Hugo TOML 头安全转换。
        lines = []
        for line in text[4:end].splitlines():
            if line.lstrip().startswith("typora-root-url"):
                continue
            if "=" not in line:
                return text
            key, value = line.split("=", 1)
            lines.append(f"{key.strip()}: {value.strip()}")
        lines.append(f"typora-root-url: {TYPORA_ROOT_URL}")
        return "---\n" + "\n".join(lines) + "\n---\n" + text[end + 5:]
    elif text.startswith("---\n"):
        marker, value = "---", f"typora-root-url: {TYPORA_ROOT_URL}"
    else:
        return text
    end = text.find(f"\n{marker}\n", 4)
    if end == -1: return text
    lines = text[4:end].splitlines()
    for i, line in enumerate(lines):
        if line.startswith("typora-root-url:"):
            lines[i] = value; break
    else: lines.append(value)
    return marker + "\n" + "\n".join(lines) + f"\n{marker}\n" + text[end + len(marker) + 2:]
def fix_markdown(posts: list[Path], *, dry_run: bool = False) -> MarkdownResult:
    result = MarkdownResult()
    for post in posts:
        before = post.read_text(encoding="utf-8"); after = _with_typora_root(before)
        if after == before: continue
        result.changed_files.add(post)
        if dry_run: log(f"[dry-run] 将加入 Typora 图片根目录：{post}")
        else: post.write_text(after, encoding="utf-8")
    return result
