import os
import re
import json
import shutil
from pathlib import Path

IMAGE_PATTERN = re.compile(r'!\[.*?\]\((.*?)\)')


def load_config():
    with open("config.json", "r", encoding="utf-8") as f:
        return json.load(f)


def log(msg):
    print(msg)


def find_image_path(img: str):
    """
    尝试找到 Markdown 中引用的图片真实位置
    """
    candidates = [
        Path(img),
        Path("static") / img.lstrip("/"),
        Path(img.lstrip("/")),
    ]

    for p in candidates:
        if p.exists() and p.is_file():
            return p

    return None


def process_images(md_path: Path, images_dir: str):
    content = md_path.read_text(encoding="utf-8")
    images = IMAGE_PATTERN.findall(content)

    if not images:
        return

    post_name = md_path.stem
    target_dir = Path(images_dir) / post_name
    target_dir.mkdir(parents=True, exist_ok=True)

    log(f"  📦 找到图片: {len(images)} 张")

    mapping = {}

    for idx, img in enumerate(images, start=1):
        old_img = img.strip()

        # 已经是目标格式的，跳过
        if old_img.startswith(f"/images/{post_name}/"):
            continue

        img_path = find_image_path(old_img)

        if img_path is None:
            log(f"  ⚠️ 找不到图片，跳过: {old_img}")
            continue

        suffix = img_path.suffix.lower()
        if not suffix:
            suffix = ".jpg"

        new_filename = f"{idx}{suffix}"
        new_path = target_dir / new_filename

        # 如果目标文件已存在，先删除，避免报错
        if new_path.exists():
            new_path.unlink()

        shutil.move(str(img_path), str(new_path))

        new_ref = f"/images/{post_name}/{new_filename}"
        mapping[old_img] = new_ref

        log(f"  ✓ {img_path.name} → {new_filename}")

    for old, new in mapping.items():
        content = content.replace(old, new)

    md_path.write_text(content, encoding="utf-8")


def build(cmd):
    log("\n🚧 正在构建 Hugo...")
    result = os.system(cmd)

    if result == 0:
        log("✓ 构建完成\n")
    else:
        log("❌ Hugo 构建失败\n")


def deploy(cmd):
    log("🚀 正在提交 Git...")
    result = os.system(cmd)

    if result == 0:
        log("✓ 发布完成\n")
    else:
        log("⚠️ Git 发布可能失败，请查看上面的提示\n")


def main():
    print("\n===============================")
    print("Leesy Blog Toolkit")
    print("🚀 Hugo 一键发布工具 V1.1")
    print("===============================\n")

    cfg = load_config()

    content_dir = Path(cfg["content_dir"])
    images_dir = cfg["images_dir"]

    md_files = list(content_dir.glob("**/*.md"))

    if not md_files:
        print("❌ 没找到 Markdown 文件")
        return

    for md in md_files:
        log(f"\n📄 处理文章: {md.name}")
        process_images(md, images_dir)

    build(cfg["build_cmd"])
    deploy(cfg["deploy_cmd"])

    print("===============================")
    print("🎉 全部完成发布")
    print("===============================\n")


if __name__ == "__main__":
    main()