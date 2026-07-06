# 写作即发布

图片唯一发布目录为 `static/images/<文章名>/`；图片按文章中出现顺序命名为 `1.png`、`2.jpg` 等，绝不移动原图。

## 一键发布（推荐）

写完文章、在 Typora 里保存后，**双击桌面上的 `发布博客.command`**（或博客目录里的同名文件）即可。终端窗口会按 5 步显示进度：

1. 检查有哪些文章需要发布
2. 整理图片、改写 Markdown
3. 清理无用图片
4. 构建 Hugo 网站（构建失败就不发布）
5. 提交并推送到 GitHub —— Cloudflare Pages 监听 `main` 分支，推送成功即自动构建上线（约 1 分钟）

发布成功或失败都会弹窗提示；失败时弹窗和终端里都会显示具体原因。推送凭据由 `scripts/github-keychain-askpass.sh` 从 macOS 钥匙串读取（令牌只存钥匙串，不进仓库）；令牌过期时重新生成一个，在终端跑一次 `security add-internet-password -s github.com -a zkzkeep -w -U` 按提示粘贴即可。

> 注：仓库里的 `gh-pages` 分支是早年 GitHub Pages 时代的遗留，现已不参与部署，网站完全由 Cloudflare Pages 从 `main` 构建。

- 桌面上的图标是指向 `~/Documents/blog/发布博客.command` 的快捷方式，可以拖进 Dock 常驻，之后写完文章点一下就发布。
- 首次推送时如果 GitHub 弹出授权框，输入一次账号/令牌即可，macOS 钥匙串会记住，之后不再打扰。
- 后台或脚本里调用时，设环境变量 `BLOG_PUBLISH_NO_DIALOG=1` 可关闭弹窗、只在终端打印。

## 边写边发（可选）

如果想“保存即自动发布”，可以启动监听器（保持这个终端开着，写作完成后按 `Ctrl-C` 停止）：

```bash
cd ~/Documents/blog
python3 -m scripts.watch
```

在 Typora 保存文章后，监听器等待 15 秒，自动备份原文、复制图片、写入网页链接、构建 Hugo、提交并推送。它处理相对 Git `HEAD` 新增、修改或删除的 Markdown；删除文章会同步从博客撤下页面，但保留图片文件，避免误删。原文备份在 `.backups/<时间>/markdown/`。本地图片找不到时流程会取消提交，防止坏链接被发布。

自动处理过的文章会有 `typora-root-url: /Users/leesdove/Documents/blog/static`；因此 `/images/...` 在 Typora 本地和网站上都能显示。可先用 `python3 deploy.py --dry-run` 预览，或用 `python3 deploy.py --no-push` 只提交不推送。

## 图片巡检

外链图片和本地图片都会在整理后归档成 `/images/<文章名>/1.jpg`、`2.png` 等形式。历史文章可执行一次：

```bash
cd ~/Documents/blog
python3 deploy.py --all-images
```

只检查、不改动文件则执行：

```bash
python3 -m scripts.audit_images
```

目前不启用 macOS 定时巡检。需要检查时手动执行上面的巡检命令即可；发现问题后，运行 `python3 deploy.py --all-images` 即可备份、整理并发布。
