from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from .config import TAG_RULES, TYPORA_ROOT_URL
from .utils import log

@dataclass
class MarkdownResult: changed_files: set[Path] = field(default_factory=set)


def _suggest_tags(text: str) -> list[str]:
    """从受控标签库中按关键词命中选择 1–3 个标签。"""
    lowered = text.lower()
    scores = [
        (sum(lowered.count(word.lower()) for word in keywords), tag)
        for tag, keywords in TAG_RULES.items()
    ]
    tags = [tag for score, tag in sorted(scores, key=lambda item: (-item[0], item[1])) if score][:3]
    return tags or ["随笔"]


def _ensure_tags(text: str) -> str:
    """只补充缺失标签，绝不覆盖作者手动填写的 tags。"""
    if not text.startswith("---\n"):
        return text
    end = text.find("\n---\n", 4)
    if end == -1:
        return text
    lines, body = text[4:end].splitlines(), text[end + 5:]
    if any(line.startswith("tags:") for line in lines):
        return text
    tags = _suggest_tags("\n".join(lines) + body)
    lines.extend(["tags:", *(f"  - {tag}" for tag in tags)])
    return "---\n" + "\n".join(lines) + "\n---\n" + body
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
        before = post.read_text(encoding="utf-8")
        after = _ensure_tags(_with_typora_root(before))
        if after == before: continue
        result.changed_files.add(post)
        if dry_run: log(f"[dry-run] 将加入 Typora 图片根目录：{post}")
        else: post.write_text(after, encoding="utf-8")
    return result
