import os
import re
import json
import shutil
import subprocess
from pathlib import Path
from urllib.parse import unquote

TOOL_NAME = "Leesy Blog Toolkit"
VERSION = "V2.0"

IMAGE_PATTERN = re.compile(r'!\[.*?\]\((.*?)\)')

DEFAULT_CONFIG = {
    "content_dir": "content/posts",
    "images_dir": "static/images",
    "build_cmd": "hugo",
    "commit_message": "auto deploy"
}

GITIGNORE_RULES = [
    "public/",
    "resources/",
    ".DS_Store",
    "__pycache__/",
    "*.pyc",
    "*.log"
]


def log(msg=""):
    print(msg)


def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True)
    return result.returncode == 0


def ensure_config():
    config_path = Path("config.json")

    if not config_path.exists():
        config_path.write_text(
            json.dumps(DEFAULT_CONFIG, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        log("✓ 已自动创建 config.json")

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def ensure_gitignore():
    gitignore = Path(".gitignore")

    old_text = ""
    if gitignore.exists():
        old_text = gitignore.read_text(encoding="utf-8")

    lines = old_text.splitlines()
    changed = False

    for rule in GITIGNORE_RULES:
        if rule not in lines:
            lines.append(rule)
            changed = True

    if changed:
        gitignore.write_text("\n".join(lines) + "\n", encoding="utf-8")
        log("✓ 已检查并更新 .gitignore")

    # 如果 public 已经被 Git 跟踪，则移出跟踪
    if Path("public").exists():
        run_cmd("git rm -r --cached public > /dev/null 2>&1")


def clean_post_name(name: str):
    name = name.strip()

    name = name.replace("《", "").replace("》", "")

    bad_chars = [
        "/", "\\", ":", "：", "*", "?", "？",
        '"', "'", "<", ">", "|", "，", ",",
        "。", "！", "!", "、"
    ]

    for ch in bad_chars:
        name = name.replace(ch, "")

    name = re.sub(r"\s+", " ", name)

    return name.strip()


def clean_img_path(img: str):
    img = img.strip()
    img = img.split("?")[0].split("#")[0]
    img = unquote(img)
    return img


def find_image_path(img: str):
    img = clean_img_path(img)

    candidates = []

    candidates.append(Path(img))

    if img.startswith("/images/"):
        candidates.append(Path("static") / img.lstrip("/"))

    candidates.append(Path(img.lstrip("/")))
    candidates.append(Path("static") / img.lstrip("/"))

    for c in candidates:
        if c.exists() and c.is_file():
            return c

    return None


def process_images(md_path: Path, images_dir: str):
    content = md_path.read_text(encoding="utf-8")
    images = IMAGE_PATTERN.findall(content)

    if not images:
        return 0, 0

    post_name = clean_post_name(md_path.stem)
    target_dir = Path(images_dir) / post_name
    target_dir.mkdir(parents=True, exist_ok=True)

    log(f"  📦 找到图片: {len(images)} 张")
    log(f"  📁 图片目录: images/{post_name}/")

    mapping = {}
    success = 0
    failed = 0
    index = 1

    for img in images:
        original_img = img.strip()
        img_path = find_image_path(original_img)

        if img_path is None:
            log(f"  ⚠️ 找不到图片，跳过: {original_img}")
            failed += 1
            continue

        suffix = img_path.suffix.lower() or ".jpg"
        new_filename = f"{index}{suffix}"
        new_path = target_dir / new_filename

        if img_path.resolve() != new_path.resolve():
            if new_path.exists():
                new_path.unlink()
            shutil.move(str(img_path), str(new_path))

        new_ref = f"/images/{post_name}/{new_filename}"
        mapping[original_img] = new_ref

        log(f"  ✓ {img_path.name} → {new_filename}")

        success += 1
        index += 1

    for old, new in mapping.items():
        content = content.replace(old, new)

    md_path.write_text(content, encoding="utf-8")

    return success, failed


def build_hugo(cmd):
    log("\n🚧 正在构建 Hugo...")
    ok = run_cmd(cmd)

    if ok:
        log("✓ Hugo 构建完成")
    else:
        log("❌ Hugo 构建失败")

    return ok


def git_deploy(commit_message):
    log("\n🚀 正在提交 Git...")

    run_cmd("git add .")

    status = subprocess.run(
        "git status --porcelain",
        shell=True,
        capture_output=True,
        text=True
    )

    if not status.stdout.strip():
        log("✓ 没有新的修改，无需提交")
        return True

    if not run_cmd(f'git commit -m "{commit_message}"'):
        log("❌ Git commit 失败")
        return False

    if not run_cmd("git push"):
        log("❌ Git push 失败")
        return False

    log("✓ Git 发布完成")
    return True


def main():
    print("\n===============================")
    print(TOOL_NAME)
    print(f"🚀 Hugo 一键发布工具 {VERSION}")
    print("===============================\n")

    cfg = ensure_config()
    ensure_gitignore()

    content_dir = Path(cfg["content_dir"])
    images_dir = cfg["images_dir"]
    build_cmd = cfg["build_cmd"]
    commit_message = cfg.get("commit_message", "auto deploy")

    if not content_dir.exists():
        log(f"❌ 找不到文章目录: {content_dir}")
        return

    md_files = list(content_dir.glob("**/*.md"))

    if not md_files:
        log("❌ 没找到 Markdown 文件")
        return

    total_success = 0
    total_failed = 0

    for md in md_files:
        log(f"\n📄 处理文章: {md.name}")
        success, failed = process_images(md, images_dir)
        total_success += success
        total_failed += failed

    log("\n===============================")
    log("图片整理统计")
    log(f"✓ 成功处理: {total_success} 张")
    log(f"⚠️ 跳过图片: {total_failed} 张")
    log("===============================")

    if not build_hugo(build_cmd):
        return

    git_deploy(commit_message)

    print("\n===============================")
    print("🎉 全部完成")
    print("===============================\n")


if __name__ == "__main__":
    main()