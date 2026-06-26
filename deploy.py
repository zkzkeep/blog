import os
import re
import json
import shutil
import subprocess
from pathlib import Path
from urllib.parse import unquote

TOOL_NAME = "Leesy Blog Toolkit"
VERSION = "V3.0"

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
    return subprocess.run(cmd, shell=True).returncode == 0


def ensure_config():
    path = Path("config.json")
    if not path.exists():
        path.write_text(
            json.dumps(DEFAULT_CONFIG, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        log("✓ 已自动创建 config.json")

    return json.loads(path.read_text(encoding="utf-8"))


def ensure_gitignore():
    path = Path(".gitignore")
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = old.splitlines()

    changed = False
    for rule in GITIGNORE_RULES:
        if rule not in lines:
            lines.append(rule)
            changed = True

    if changed:
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        log("✓ 已检查并更新 .gitignore")

    if Path("public").exists():
        run_cmd("git rm -r --cached public > /dev/null 2>&1")


def clean_post_name(name):
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


def clean_img_ref(img):
    img = img.strip()
    img = img.split("?")[0].split("#")[0]
    img = unquote(img)
    return img


def search_by_filename(filename, images_root):
    matches = list(Path(images_root).rglob(filename))

    matches = [
        p for p in matches
        if p.is_file()
        and ".DS_Store" not in str(p)
        and "public" not in p.parts
    ]

    if matches:
        return matches[0]

    return None


def find_image_path(img_ref, images_root):
    img = clean_img_ref(img_ref)
    p = Path(img)

    candidates = []

    # 1. 原始路径
    candidates.append(p)

    # 2. /images/xxx => static/images/xxx
    if img.startswith("/images/"):
        candidates.append(Path("static") / img.lstrip("/"))

    # 3. 去掉开头 /
    candidates.append(Path(img.lstrip("/")))

    # 4. static 兜底
    candidates.append(Path("static") / img.lstrip("/"))

    for c in candidates:
        if c.exists() and c.is_file():
            return c

    # 5. 最强兜底：只拿文件名，在 static/images 里全局搜索
    filename = Path(img).name
    if filename:
        found = search_by_filename(filename, images_root)
        if found:
            return found

    return None


def process_markdown(md_path, images_root):
    content = md_path.read_text(encoding="utf-8")
    images = IMAGE_PATTERN.findall(content)

    if not images:
        return 0, 0

    post_name = clean_post_name(md_path.stem)
    target_dir = Path(images_root) / post_name
    target_dir.mkdir(parents=True, exist_ok=True)

    log(f"  📦 找到图片: {len(images)} 张")
    log(f"  📁 图片目录: images/{post_name}/")

    success = 0
    failed = 0
    index = 1
    mapping = {}

    for img_ref in images:
        original_ref = img_ref.strip()
        img_path = find_image_path(original_ref, images_root)

        if not img_path:
            log(f"  ⚠️ 找不到图片，跳过: {original_ref}")
            failed += 1
            continue

        suffix = img_path.suffix.lower() or ".jpg"
        new_name = f"{index}{suffix}"
        new_path = target_dir / new_name

        if img_path.resolve() != new_path.resolve():
            if new_path.exists():
                new_path.unlink()
            shutil.move(str(img_path), str(new_path))

        new_ref = f"/images/{post_name}/{new_name}"
        mapping[original_ref] = new_ref

        log(f"  ✓ {img_path.name} → {new_name}")

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
    print(TOL_NAME if False else TOOL_NAME)
    print(f"🚀 Hugo 一键发布工具 {VERSION}")
    print("===============================\n")

    cfg = ensure_config()
    ensure_gitignore()

    content_dir = Path(cfg["content_dir"])
    images_root = cfg["images_dir"]
    build_cmd = cfg["build_cmd"]
    commit_message = cfg.get("commit_message", "auto deploy")

    if not content_dir.exists():
        log(f"❌ 找不到文章目录: {content_dir}")
        return

    md_files = list(content_dir.glob("**/*.md"))

    total_success = 0
    total_failed = 0

    for md in md_files:
        log(f"\n📄 处理文章: {md.name}")
        success, failed = process_markdown(md, images_root)
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