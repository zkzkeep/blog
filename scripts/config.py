from pathlib import Path

BLOG_ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = BLOG_ROOT / "content"
STATIC_DIR = BLOG_ROOT / "static"
IMAGES_DIR = STATIC_DIR / "images"
BACKUPS_DIR = BLOG_ROOT / ".backups"
IMAGE_EXTENSIONS = {".avif", ".gif", ".jpeg", ".jpg", ".png", ".svg", ".webp"}
# Typora 只识别 YAML front matter；绝对路径不受文章目录层级影响。
TYPORA_ROOT_URL = str(STATIC_DIR)

# 自动标签只会从固定库中选择，避免同义词造成分类碎片。
TAG_RULES = {
    "读书": ("读后感", "小说", "作者", "文学", "书", "阅读"),
    "影评": ("电影", "影片", "导演", "观后感", "剧集"),
    "旅行": ("旅行", "旅游", "游记", "出行", "景区"),
    "工作": ("工作", "公司", "会议", "培训", "应急", "演练"),
    "学习": ("学习", "课程", "笔记", "知识", "教程"),
    "技术": ("代码", "编程", "Git", "Hugo", "Hexo", "Python", "软件"),
    "AI": ("AI", "人工智能", "ChatGPT", "大模型", "机器人"),
    "新闻": ("新闻", "采访", "报道", "媒体"),
    "健康": ("健康", "医院", "医生", "血压", "血脂", "疾病", "吃药"),
    "生活": ("生活", "家庭", "日常", "朋友", "人生"),
    "思考": ("思考", "意义", "社会", "人性", "感想"),
}
