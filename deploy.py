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

def process_images(md_path: Path, images_dir: str):
    content = md_path.read_text(encoding="utf-8")
    images = IMAGE_PATTERN.findall(content)

    if not images:
        return content

    post_name = md_path.stem
    target_dir = Path(images_dir) / post_name
    target_dir.mkdir(parents=True, exist_ok=True)

    mapping = {}

    for img in images:
        img_path = Path(img)

        # 如果图片路径找不到，尝试 static/
        if not img_path.exists():
            img_path = Path("static") / img
            if not img_path.exists():
                continue

        new_path = target_dir / img_path.name
        shutil.move(str(img_path), str(new_path))

        new_ref = f"/images/{post_name}/{img_path.name}"
        mapping[img] = new_ref

        log(f"✓ 移动图片: {img_path.name}")

    for old, new in mapping.items():
        content = content.replace(old, new)

    md_path.write_text(content, encoding="utf-8")
    return content

def build(cmd):
    log("\n🚧 正在构建 Hugo...")
    os.system(cmd)
    log("✓ 构建完成\n")

def deploy(cmd):
    log("🚀 正在提交 Git...")
    os.system(cmd)
    log("✓ 发布完成\n")

def main():
    print("\n===============================")
    print("Leesy Blog Toolkit")
    print("🚀 Hugo 一键发布工具 V1.0")
    print("===============================\n")

    cfg = load_config()

    content_dir = Path(cfg["content_dir"])
    images_dir = cfg["images_dir"]

    md_files = list(content_dir.glob("**/*.md"))

    if not md_files:
        print("❌ 没找到 Markdown 文件")
        return

    for md in md_files:
        log(f"\n📄 处理文章: {md.name}\n")
        process_images(md, images_dir)

    build(cfg["build_cmd"])
    deploy(cfg["deploy_cmd"])

    print("===============================")
    print("🎉 全部完成发布")
    print("===============================\n")

if __name__ == "__main__":
    main()