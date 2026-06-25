import os
import re

ROOT = "/Users/" + os.getlogin() + "/Documents/blog/content/posts"

patterns = [
    r'!\[([^\]]*)\]\(\./\.\./images',
    r'!\[([^\]]*)\]\(\.\./images',
    r'!\[([^\]]*)\]\(images'
]

for root, dirs, files in os.walk(ROOT):
    for file in files:
        if file.endswith(".md"):
            path = os.path.join(root, file)

            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            original = content

            # 统一替换成 /images
            content = re.sub(r'!\[([^\]]*)\]\(.*?images', r'![](/images', content)

            if content != original:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                print("fixed:", file)

print("done")
