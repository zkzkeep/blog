# 写作即发布

图片唯一发布目录为 `static/images/<文章名>/`；图片按文章中出现顺序命名为 `1.png`、`2.jpg` 等，绝不移动原图。

写作结束后启动监听器（保持这个终端开着，写作完成后按 `Ctrl-C` 停止）：

```bash
cd ~/Documents/blog
python3 -m scripts.watch
```

在 Typora 保存文章后，监听器等待 15 秒，自动备份原文、复制图片、写入网页链接、构建 Hugo、提交并推送。它只处理相对 Git `HEAD` 新增或修改的 Markdown；未改动历史文章不扫描、不改写。原文备份在 `.backups/<时间>/markdown/`。本地图片找不到时流程会取消提交，防止坏链接被发布。

自动处理过的文章会有 `typora-root-url: ../../static`；因此 `/images/...` 在 Typora 本地和网站上都能显示。可先用 `python3 deploy.py --dry-run` 预览，或用 `python3 deploy.py --no-push` 只提交不推送。
