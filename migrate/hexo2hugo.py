import os
import re
import shutil
from datetime import datetime

SRC = "/Volumes/Elements/My_Blog/source/_posts"
DST = "../content/posts"

os.makedirs(DST, exist_ok=True)

def convert_date(date_str):
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        return dt.isoformat() + "+08:00"
    except:
        return date_str

def convert_file(path):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if content.startswith("---"):
        parts = content.split("---")
        front = parts[1]
        body = "---".join(parts[2:])

        # 处理字段
        title = re.search(r"title:\s*(.*)", front)
        date = re.search(r"date:\s*(.*)", front)
        tags = re.findall(r"-\s*(.*)", front.split("tags:")[-1]) if "tags" in front else []

        title = title.group(1).strip() if title else "Untitled"
        date = convert_date(date.group(1).strip()) if date else ""

        new_front = f"""---
title: "{title}"
date: {date}
draft: false
tags:
"""

        for t in tags:
            new_front += f"  - {t}\n"

        new_front += "---\n"

        return new_front + body

    return content

for file in os.listdir(SRC):
    if file.endswith(".md"):
        src_file = os.path.join(SRC, file)
        content = convert_file(src_file)

        new_name = file.replace(".md", ".md")
        dst_file = os.path.join(DST, new_name)

        with open(dst_file, "w", encoding="utf-8") as f:
            f.write(content)

        print("converted:", file)

print("done")
