import os
import re
import json
import shutil
from pathlib import Path
from urllib.parse import unquote

IMAGE_PATTERN = re.compile(r'!\[.*?\]\((.*?)\)')


def load_config():
    with open("config.json", "r", encoding="utf-8") as f:
        return json.load(f)


def log(msg):
    print(msg)


def clean_img_path(img: str):
    img = img.strip()
    img = img.split("?")[0].split("#")[0]
    img = unquote(img)
    return img


def find_image_path(img: str):
    img = clean_img_path(img)

    candidates = []

    p = Path(img)

    # 1. 绝对路径
    candidates.append(p)

    # 2. Hugo 路径：/images/xxx => static/images/xxx
    if img.startswith("/images/"):
        candidates.append(Path("static") / img.lstrip("/"))

    # 3. 普通相对路径
    candidates.append(Path(img.lstrip("/")))

    # 4. static 兜底
    candidates.append(Path("static") / img.lstrip("/"))

    for c in candidates:
        if c.exists() and c.is_file():
            return c

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
    real_index = 1

    for img in images:
        original_img = img.strip()
        img_path = find_image_path(original_img)

        if img_path is None:
            log(f"  ⚠️ 找不到图片，跳过: {original_img}")
            continue

        suffix = img_path.suffix.lower() or ".jpg"
        new_filename = f"{real_index}{suffix}"
        new_path = target_dir / new_filename

        # 如果原图已经在目标位置，就只改名
        if img_path.resolve() != new_path.resolve():
            if new_path.exists():
                new_path.unlink()
            shutil.move(str(img_path), str(new_path))

        new_ref = f"/images/{post_name}/{new_filename}"
        mapping[original_img] = new_ref

        log(f"  ✓ {img_path.name} → {new_filename}")
        real_index += 1

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
    print("🚀 Hugo 一键发布工具 V1.2")
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