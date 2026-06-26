from pathlib import Path

BLOG_ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = BLOG_ROOT / "content"
STATIC_DIR = BLOG_ROOT / "static"
IMAGES_DIR = STATIC_DIR / "images"
BACKUPS_DIR = BLOG_ROOT / ".backups"
IMAGE_EXTENSIONS = {".avif", ".gif", ".jpeg", ".jpg", ".png", ".svg", ".webp"}
# Typora 只识别 YAML front matter；绝对路径不受文章目录层级影响。
TYPORA_ROOT_URL = str(STATIC_DIR)
