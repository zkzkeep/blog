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


def clean_post_name(name: str):
    """
    清理文章名，生成适合放在 images 下的文件夹名
    例如：
    《五一游记》 -> 五一游记
    《人间失格》 -> 人间失格
    """
    name = name.strip()

    # 去掉书名号
    name = name.replace("《", "").replace("》", "")

    # 去掉常见不适合做文件夹名的符号
    bad_chars = [
        "/", "\\", ":", "：", "*", "?", "？",
        '"', "'", "<", ">", "|", "，", ",",
        "。", "！", "!", "、"
    ]

    for ch in bad_chars:
        name = name.replace(ch, "")

    # 多个空格变一个空格
    name = re.sub(r"\s+", " ", name)

    return name.strip()


def clean_img_path(img: str):
    """
    清理 Markdown 里的图片路径
    处理 URL 编码，例如：
    %E4%BA%94 -> 五
    """
    img = img.strip()
    img = img.split("?")[0].split("#")[0]
    img = unquote(img)
    return img


def find_image_path(img: str):
    """
    根据 Markdown 中的图片路径，找到真实图片文件
    """
    img = clean_img_path(img)

    candidates = []

    # 1. 原路径
    candidates.append(Path(img))

    # 2. Hugo 路径：/images/xxx => static/images/xxx
    if img.startswith("/images/"):
        candidates.append(Path("static") / img.lstrip("/"))

    # 3. 去掉开头 /
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

    raw_post_name = md_path.stem
    post_name = clean_post_name(raw_post_name)

    target_dir = Path(images_dir) / post_name
    target_dir.mkdir(parents=True, exist_ok=True)

    log(f"  📦 找到图片: {len(images)} 张")
    log(f"  📁 图片目录: images/{post_name}/")

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

        # 如果图片本来就在正确位置，并且名字也对，就不移动
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
    print("🚀 Hugo 一键发布工具 V1.3")
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