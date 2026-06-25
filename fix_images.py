import os
import re

ROOT = "/Users/" + os.getlogin() + "/Documents/blog/content/posts"

pattern = re.compile(r'!\[(.*?)\]\((.*?\.\./.*?images.*?)\)')

for root, dirs, files in os.walk(ROOT):
    for file in files:
        if file.endswith(".md"):
            path = os.path.join(root, file)

            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            # 把 ../images 或 ./../images 改成 /images
            content_new = re.sub(
                r'(!\[[^\]]*\]\()\.\.\/.*?images',
                r'\1/images',
                content
            )

            with open(path, "w", encoding="utf-8") as f:
                f.write(content_new)

            print("fixed:", file)

print("done")
