---
date: 2026-06-27T09:05:34+08:00
draft: false
title: '我的hugo+cloudflare自动化博客搭建手册'
typora-root-url: /Users/leesdove/Documents/blog/static
tags:
  - 技术
  - 学习
  - 工作
---

# 《我的 Hugo + Cloudflare 自动化博客搭建手册》

> 一套属于自己的博客系统，不只是一个网站，更是一份可以长期维护的数字资产。

------

# 第一章 为什么重建博客

## 1.1 写在前面

从学生时代开始，我就一直有写博客的习惯。

最早接触的是 Hexo + GitHub Pages。那时更多是为了记录折腾电脑、网络和编程的过程。后来因为域名到期、工作繁忙、长期没有维护，博客逐渐停用，最后也无法继续访问。

多年以后，我重新开始思考一个问题：

> 互联网上那么多内容，真正属于自己的还有多少？

朋友圈会被时间淹没，公众号受平台限制，知乎、微博也都有自己的规则。只有自己拥有的博客，文章、图片、域名、排版和访问方式，才真正掌握在自己手里。

这一次，我希望博客不只是一个写文章的网站，而是一套能够长期稳定运行、可以迁移、可以恢复、可以陪伴很多年的知识管理系统。

------

## 1.2 我的目标

重建博客时，我给自己定下了几个目标。

第一，流程要简单。

博客应该把精力放在内容上，而不是每天维护网站本身。理想状态是：打开 Typora 写文章，保存后自动发布。

第二，数据要属于自己。

所有文章用 Markdown 保存，所有图片进入仓库，源码托管在 GitHub，网站部署在 Cloudflare Pages，域名使用自己的 `leesy.cc`。

第三，访问要稳定。

博客采用静态部署，没有数据库，没有后台，没有服务器运维压力。Cloudflare Pages 负责 HTTPS、CDN 和全球访问。

第四，系统要能长期维护。

我希望它不仅能记录读书、生活、技术、工作、健康和思考，也能在几年以后仍然容易恢复、容易修改、容易继续写。

------

## 1.3 为什么选择 Hugo

目前主流静态博客框架很多，例如 Hexo、Hugo、Jekyll、Astro、Next.js。

最终选择 Hugo，主要因为：

- 构建速度快；
- Markdown 原生支持好；
- 没有数据库依赖；
- 主题生态成熟；
- 迁移成本低；
- 长期维护相对省心。

对我来说，Hugo 最重要的优点不是功能多，而是它足够安静。

写作就是写作，不应该被复杂的运行环境绑住。

------

## 1.4 当前真实工作流

现在博客的实际工作流是：

```text
Typora 写作
    ↓
保存 Markdown
    ↓
scripts.watch 监听到变化
    ↓
deploy.py 调度发布流程
    ↓
整理图片、修正文章、补充标签
    ↓
Hugo 本地构建校验
    ↓
Git commit / git push
    ↓
GitHub 保存源码和历史
    ↓
Cloudflare Pages 自动构建部署
    ↓
https://leesy.cc
```

日常使用时，我只需要先启动监听器：

```bash
cd ~/Documents/blog
python3 -m scripts.watch
```

然后在 Typora 里写文章、保存文章。

监听器会等待 15 秒，确认编辑基本结束后，自动运行发布脚本。

------

## 1.5 为什么选择 Cloudflare Pages

以前我使用 GitHub Pages。GitHub Pages 本身很好，但在这个博客系统里，我更希望 GitHub 专注于源码管理，Cloudflare 专注于部署和访问。

迁移后分工变得更清楚：

```text
GitHub：保存源码、提交历史、文章和图片
Cloudflare Pages：构建、部署、HTTPS、CDN、域名入口
```

域名本身就在 Cloudflare 管理，因此 DNS、证书、部署和 CDN 放在同一个平台里，维护成本更低。

最终主站地址是：

```text
https://leesy.cc
```

------

# 第二章 当前环境与目录结构

## 2.1 开发环境

当前博客开发环境如下。

| 项目 | 软件 |
| --- | --- |
| 操作系统 | macOS |
| 包管理器 | Homebrew |
| 静态博客 | Hugo Extended |
| 编辑器 | Typora |
| 版本管理 | Git |
| 代码托管 | GitHub |
| 网站部署 | Cloudflare Pages |
| 域名解析 | Cloudflare DNS |

所有工具尽量使用官方渠道安装，避免依赖复杂的第三方环境。

------

## 2.2 目录结构

当前博客核心目录如下：

```text
blog/
├── archetypes/
├── content/
│   └── posts/
├── static/
│   └── images/
├── scripts/
├── themes/
│   └── PaperMod/
├── deploy.py
├── hugo.toml
└── README-DEPLOY.md
```

几个目录最重要。

`content/posts/` 保存所有 Markdown 文章。

`static/images/` 保存所有文章图片。

`scripts/` 保存自动化脚本。

`themes/PaperMod/` 保存当前主题。

`deploy.py` 是发布总入口。

`README-DEPLOY.md` 是日常发布说明。

------

## 2.3 图片目录规范

所有文章图片最终都进入：

```text
static/images/<文章名>/
```

并按文章中出现顺序编号：

```text
1.jpg
2.png
3.webp
```

文章中的引用统一写成：

```markdown
![](/images/<文章名>/1.jpg)
```

这样同一张图片既能在网站上显示，也能在 Typora 本地显示。

关键在于文章头里有：

```yaml
typora-root-url: /Users/leesdove/Documents/blog/static
```

Typora 看到 `/images/...` 时，就会从本地 `static/images/` 里找。

------

## 2.4 不进 Git 的内容

`.gitignore` 会忽略这些内容：

```text
public/
resources/
.DS_Store
__pycache__/
*.pyc
.hugo_build.lock
.backups/
```

其中 `public/` 是 Hugo 构建产物，不是源文件。只要源码还在，`public/` 随时可以重新生成。

博客真正需要长期保存的是：

- Markdown 文章；
- 图片资源；
- Hugo 配置；
- 自动化脚本；
- 主题文件；
- Git 提交历史。

------

# 第三章 Hugo 建站与迁移取舍

## 3.1 为什么放弃 Hexo

Hexo 陪伴我很久，也留下过不少文章。但长时间不用以后，它的问题也比较明显：

- Node.js 环境依赖较重；
- 插件和主题升级容易遇到兼容问题；
- 换电脑恢复环境比较麻烦；
- 长期不维护后，重新跑起来成本偏高。

重新搭建博客时，我希望系统几年以后仍然容易恢复。

因此最终放弃 Hexo，选择 Hugo。

------

## 3.2 为什么不用 Git Submodule 管主题

一开始考虑过把 PaperMod 作为 Git Submodule 引入。

Submodule 的优点是升级主题方便，但它也会增加部署和恢复复杂度。

后来决定直接把 PaperMod 放进仓库：

```text
themes/PaperMod/
```

这样做的好处是：

- Cloudflare Pages 构建时不需要额外拉子模块；
- 换电脑后直接 clone 仓库即可；
- 主题和文章一起进入 Git 历史；
- 出问题时更容易排查。

对个人博客来说，稳定比“升级方便”更重要。

------

## 3.3 文章命名

文章标题可以是中文，但文件名尽量使用英文 slug。

例如：

```text
hugo-cloudflare-handbook.md
```

这样做是为了：

- 避免命令行处理空格和特殊字符；
- URL 更稳定；
- 分享链接更清晰；
- 以后迁移更轻松。

真正展示给读者看的标题，仍然可以写中文。

------

## 3.4 图片管理是最重要的坑

这次搭建里最值得记录的问题，不是主题，也不是页面样式，而是图片。

Typora 默认插入图片时，可能会产生本机路径、相对路径、临时路径或外链。

如果不统一管理，几年以后很容易出现：

- 本地能看，网站看不到；
- 网站能看，本地看不到；
- 换电脑后图片丢失；
- 图片散落在多个目录；
- 外链图床失效。

现在的方案是：

```text
文章保存
    ↓
监听器触发发布脚本
    ↓
脚本识别图片引用
    ↓
复制到 static/images/<文章名>/
    ↓
按出现顺序编号
    ↓
改写 Markdown 图片链接
```

图片不再是临时附件，而是博客资产的一部分。

------

## 3.5 GitHub Pages 到 Cloudflare Pages

博客最终不再使用 GitHub Pages。

现在的结构是：

```text
本地 Git commit
    ↓
GitHub 仓库
    ↓
Cloudflare Pages
    ↓
https://leesy.cc
```

迁移后做了几件事：

- `hugo.toml` 的 `baseURL` 改为 `https://leesy.cc/`；
- 删除 GitHub Pages workflow；
- 在 GitHub 仓库设置里关闭 GitHub Pages；
- Cloudflare Pages 连接 GitHub 仓库并监听 `main` 分支；
- 域名入口改为 `leesy.cc` 和 `www.leesy.cc`。

GitHub 仍然重要，但它现在只负责源码和历史。

Cloudflare Pages 负责最终构建和访问。

------

# 第四章 自动化发布流程的演进

## 4.1 第一版：先让发布跑起来

最早的目标很简单：

> 在 Typora 里写文章时，本地能看到图片，发布到网站后也能看到图片。

第一版脚本大致是：

```text
整理图片
    ↓
修改 Markdown 图片链接
    ↓
运行 Hugo 构建
    ↓
Git 提交
    ↓
Git 推送
```

这个方向是对的，但第一版也有明显问题：

- 倾向于扫描所有文章；
- 图片、Markdown、Git 操作混在一起；
- 出错后不容易定位；
- 对历史文章不够克制；
- 对原文保护不够强。

所以第一版解决了“能不能自动发布”，但还没有解决“能不能放心长期使用”。

------

## 4.2 第二版：拆成模块

后来把脚本拆成现在的结构：

```text
deploy.py
scripts/
├── organize_images.py
├── markdown.py
├── git_tools.py
├── hugo_tools.py
├── config.py
└── utils.py
```

`deploy.py` 只做调度。

具体事情交给各个模块：

```text
changed_markdown_files()
    ↓
backup_markdown()
    ↓
organize_images()
    ↓
fix_markdown()
    ↓
build_hugo()
    ↓
commit_and_push()
```

这一步很关键。

从这里开始，发布脚本不再是一个大杂烩，而是一套可以继续维护的工具。

------

## 4.3 第三版：只处理改动文章

全量扫描最简单，但风险也最大。

历史文章里可能有教程示例、旧图片路径、外链图片、代码块里的图片写法。如果每次都全量改写，很容易产生不必要的变更。

现在脚本只处理相对 Git `HEAD` 新增、修改或删除的 Markdown。

这个原则很重要：

> 自动化不是越积极越好，而是越克制越可靠。

我今天只改一篇文章，脚本就只处理这一篇。

没有变化的历史文章，不碰。

------

## 4.4 第四版：先备份，再改写

文章不是测试数据。

每次自动改写 Markdown 前，脚本会先备份原文：

```text
.backups/<时间>/markdown/
```

后来的安全原则是：

- 改写前先备份；
- 图片只复制，不随便移动原图；
- 本地图片找不到时取消提交；
- Hugo 构建失败时取消发布；
- 检查通过后才提交和推送。

这让自动化从“方便”变成了“可靠”。

------

## 4.5 第五版：保存后自动发布

有了 `deploy.py` 后，发布已经方便很多。

但每次写完文章还要手动运行命令，仍然有些割裂。

于是增加了监听器：

```bash
python3 -m scripts.watch
```

它会做四件事：

1. 启动时检查是否有未发布文章；
2. 监听 `content/` 下 Markdown 文件变化；
3. 保存后等待 15 秒；
4. 自动运行 `deploy.py`。

等待 15 秒是为了避免 Typora 连续保存时频繁提交。

最终体验变成：

```text
启动监听器
    ↓
Typora 写文章
    ↓
保存
    ↓
自动发布
```

这就是我想要的“写作即发布”。

------

## 4.6 放弃定时巡检

我曾尝试让 macOS 每天定时跑图片巡检。

想法很好，但实际遇到了 macOS 对 `Documents` 目录的权限限制。后台任务不一定能访问 `~/Documents/blog`，容易产生失败日志。

后来决定暂停这个方向。

我的博客不是后台自动生产内容，而是我写文章时才需要检查和发布。

所以更合理的方式是：

- 日常发布走监听器；
- 需要时手动运行图片巡检；
- 不让系统后台定时任务增加复杂度。

自动化的目标不是把所有事都交给后台，而是把合适的事情放在合适的时机。

------

# 第五章 自动化脚本说明

## 5.1 deploy.py

`deploy.py` 是总入口。

它负责调度整个发布流程：

```text
检测变更文章
    ↓
备份原文
    ↓
整理图片
    ↓
修正 Markdown
    ↓
运行 Hugo 构建
    ↓
提交并推送 Git
```

常用命令：

```bash
python3 deploy.py
python3 deploy.py --dry-run
python3 deploy.py --no-push
python3 deploy.py --all-images
```

平时不用直接运行它，因为监听器会自动调用。

------

## 5.2 scripts/watch.py

`watch.py` 是日常写作时最常用的脚本。

启动方式：

```bash
cd ~/Documents/blog
python3 -m scripts.watch
```

它会监听 Markdown 保存动作，等待 15 秒后自动发布。

如果启动时已经有未发布文章，它也会先同步一次。

------

## 5.3 scripts/organize_images.py

`organize_images.py` 负责图片整理。

它会识别：

- 本地图片；
- Typora 临时图片；
- 已归档的 `/images/...` 图片；
- 外链图片；
- 代码块里的示例图片。

需要整理的图片会复制到：

```text
static/images/<文章名>/
```

然后按顺序编号，并改写文章中的图片链接。

它的原则是：

- 不处理代码块示例；
- 本地图片找不到就取消发布；
- 外链图片能下载就归档，不能下载就保留原链接；
- 保护文章和图片，不做危险操作。

------

## 5.4 scripts/markdown.py

`markdown.py` 负责修正 Markdown 本身。

它主要做两件事。

第一，补充 Typora 图片根目录：

```yaml
typora-root-url: /Users/leesdove/Documents/blog/static
```

第二，给缺少标签的文章自动补充 tags。

但如果我已经手动写了 tags，脚本不会覆盖。

自动化可以补漏，但不能替作者做最终判断。

------

## 5.5 scripts/git_tools.py

`git_tools.py` 负责 Git 相关操作。

它会判断：

- 哪些 Markdown 新增；
- 哪些 Markdown 修改；
- 哪些 Markdown 删除；
- 本轮应该提交哪些文章和图片。

它不是简单 `git add .`，而是尽量只提交本轮相关文件。

这样可以减少误提交，也让每次提交更清楚。

------

## 5.6 scripts/hugo_tools.py

`hugo_tools.py` 负责运行：

```bash
hugo --minify
```

构建通过后，流程才会继续提交和推送。

如果 Hugo 构建失败，说明当前内容不适合发布，脚本会停止。

------

## 5.7 config.py、utils.py 与 audit_images.py

`config.py` 保存路径、图片后缀、Typora 根目录、标签规则等配置。

`utils.py` 保存日志、命令执行、备份、目录名处理等公共函数。

`audit_images.py` 用来检查图片引用是否规范。它适合手动巡检，不再做 macOS 定时任务。

------

# 第六章 Git 在博客中的作用

## 6.1 Git 管理什么

Git 管理的不只是代码。

在这个博客里，它管理：

- Markdown 文章；
- 图片资源；
- 自动化脚本；
- Hugo 配置；
- 主题文件；
- 每一次发布历史。

只要这些进入 Git，就有记录，也能恢复。

------

## 6.2 HEAD 是自动化流程的参照点

脚本判断文章有没有变化，靠的是 Git `HEAD`。

可以简单理解为：

> HEAD 就是上一次正式提交的版本。

当前文件和 `HEAD` 对比，如果不同，就说明有新改动。

这比单纯看文件修改时间更可靠。

------

## 6.3 一次发布对应一次提交

理想状态是：

> 每一次自动发布，都对应一次 Git 提交。

这样可以知道每次发布改了什么。

如果某次发布有问题，也能定位到具体提交。

整个链路是：

```text
本地文件修改
    ↓
Git commit
    ↓
Git push
    ↓
GitHub 保存历史
    ↓
Cloudflare Pages 构建网站
```

------

## 6.4 GitHub 的角色

迁移到 Cloudflare Pages 后，GitHub Pages 已经不再托管网站。

但 GitHub 仓库不能关闭。

它仍然负责：

- 保存博客源码；
- 保存提交历史；
- 作为 Cloudflare Pages 的构建来源；
- 在换电脑时恢复博客。

可以关闭 GitHub Pages。

不能删除 GitHub 仓库。

------

## 6.5 Git 是后悔药

如果文章误删、脚本改坏、图片路径异常，第一步先看 Git：

```bash
git status
git log --oneline
git diff
```

Git 让博客有历史。

历史在，就能查，也能恢复。

------

# 第七章 Cloudflare Pages 迁移与部署

## 7.1 迁移前后对比

迁移前：

```text
本地博客
    ↓
GitHub 仓库
    ↓
GitHub Pages
    ↓
blog.leesy.cc
```

迁移后：

```text
本地博客
    ↓
GitHub 仓库
    ↓
Cloudflare Pages
    ↓
leesy.cc / www.leesy.cc
```

这次迁移的核心不是“不要 GitHub”，而是重新分工。

GitHub 保存源码。

Cloudflare Pages 负责部署。

------

## 7.2 迁移时改了什么

主要改动有三类。

第一，修改 `hugo.toml`：

```toml
baseURL = "https://leesy.cc/"
```

第二，删除 GitHub Pages workflow。

原来的 `.github/workflows/hugo.yml` 是给 GitHub Pages 用的，迁移后不再需要。

第三，在 GitHub 仓库设置中关闭 GitHub Pages。

这一步不会删除仓库，也不会影响 Cloudflare Pages，只是停止旧站点继续服务。

------

## 7.3 Cloudflare Pages 怎么部署

Cloudflare Pages 连接 GitHub 仓库后，会监听 `main` 分支。

每次 `git push` 后，它会自动：

```text
拉取 GitHub 仓库
    ↓
运行 Hugo 构建
    ↓
生成 public/
    ↓
发布到 Cloudflare 全球网络
```

因此本地不需要提交 `public/`。

`public/` 是构建产物，不是源码。

------

## 7.4 域名理解

现在主域名是：

```text
https://leesy.cc
```

`www.leesy.cc` 可以作为补充入口。

旧域名 `blog.leesy.cc` 如果还想保留，可以在 Cloudflare 中做跳转。

但博客配置里的 `baseURL` 应该使用最终希望被读者和搜索引擎记住的主域名。

------

# 第八章 常见问题排查

## 8.1 Typora 看不到图片

检查文章头是否有：

```yaml
typora-root-url: /Users/leesdove/Documents/blog/static
```

再检查图片链接是否是：

```markdown
![](/images/<文章名>/1.jpg)
```

如果缺少 `typora-root-url`，Typora 可能不知道 `/images/...` 在本地哪里。

------

## 8.2 网站看不到图片

先确认图片文件存在：

```text
static/images/<文章名>/1.jpg
```

再确认文章引用是：

```text
/images/<文章名>/1.jpg
```

如果本地存在但网站没有，可能是还没提交、还没推送，或者 Cloudflare Pages 还没部署完成。

------

## 8.3 Hugo 构建失败

如果 `hugo --minify` 失败，自动发布会停止。

常见原因包括：

- front matter 格式错误；
- Markdown 语法异常；
- 图片路径写错；
- 主题模板问题；
- 文章里包含 Hugo 不允许的原始 HTML。

构建失败时不要强行发布，先修正错误。

------

## 8.4 Git push 失败

常见原因：

- 网络问题；
- GitHub 登录状态失效；
- 远端仓库地址错误；
- 本地和远端历史冲突；
- GitHub 权限问题。

先看：

```bash
git remote -v
git status --branch --short
```

------

## 8.5 Cloudflare Pages 没更新

如果 GitHub 已经推送成功，但网站没更新，重点看 Cloudflare Pages：

- 是否连接正确仓库；
- 构建分支是否是 `main`；
- 最近一次部署是否成功；
- 构建命令是否正确；
- 输出目录是否是 `public`。

本地可以先确认：

```bash
hugo --minify
git log -1 --oneline
```

------

# 第九章 换电脑与恢复博客

## 9.1 恢复需要什么

理论上，只要 GitHub 仓库还在，大部分内容就能恢复。

新电脑需要：

- Git；
- Hugo Extended；
- Python 3；
- Typora；
- GitHub 访问权限；
- Cloudflare 账号权限。

博客源码从 GitHub 克隆回来后，文章、图片、脚本、主题都应该在仓库里。

这就是图片必须进入 `static/images/` 的原因。

------

## 9.2 新电脑恢复流程

大致顺序：

```text
安装 Homebrew
    ↓
安装 Hugo Extended
    ↓
安装 Git
    ↓
克隆博客仓库到 ~/Documents/blog
    ↓
运行 hugo --minify
    ↓
打开 Typora
    ↓
启动 python3 -m scripts.watch
```

如果 Hugo 构建通过，Typora 也能看到图片，说明恢复基本成功。

------

## 9.3 备份边界

GitHub 是主要备份。

本地 `.backups/` 是自动改写前的临时保险。

Cloudflare Pages 不是源码备份，它只是部署平台。

真正重要的是：

- GitHub 仓库；
- 本地 Git 历史；
- Markdown 原文；
- `static/images/` 图片；
- 域名控制权。

------

# 第十章 长期维护原则

## 10.1 保持结构稳定

当前目录已经比较清楚：

```text
content/posts/
static/images/
scripts/
themes/PaperMod/
deploy.py
hugo.toml
```

以后新增功能时，尽量不要随便打乱结构。

结构稳定，迁移和排查才容易。

------

## 10.2 自动化保持克制

真正适合自动化的是：

- 重复发生；
- 规则明确；
- 出错可回滚；
- 不影响写作节奏。

不适合自动化的是：

- 需要人工判断的内容；
- 系统权限复杂的后台任务；
- 失败后难以察觉的操作；
- 可能误删文章或图片的动作。

这套博客自动化应该继续保持一个原则：

> 帮我做杂事，但不要替我做判断。

------

## 10.3 发布前必须能构建

无论以后脚本怎么改，有一个原则不能变：

> Hugo 构建失败，就不发布。

构建是最低限度的质量检查。

个人博客也不应该把明显坏掉的版本推到线上。

------

## 10.4 文章和图片都是资产

文章是资产。

图片也是资产。

以前容易只重视 Markdown，忽略图片。

但真正迁移博客时会发现，图片一旦散落在电脑各处，恢复成本非常高。

所以现在的规则是：

```text
文章进入 content/posts/
图片进入 static/images/<文章名>/
```

只要文章和图片都在仓库里，博客才算真正属于自己。

------

## 10.5 文档也要维护

这篇手册本身也应该持续更新。

以后每次调整脚本、迁移平台、修改部署方式、踩到新坑，都应该补进来。

因为人会忘。

但文档可以帮未来的自己快速恢复现场。

这也是写这篇手册最大的意义：

> 不是为了证明我搭过一个博客，而是为了让这个博客以后还搭得起来、修得明白、用得安心。

------

## 10.6 最后的目标

这套系统最终要达到的状态很简单：

打开 Typora，写文章。

保存。

等待自动发布。

然后继续生活。

技术不应该挡在写作前面。

它应该在背后安静地托住写作。

如果几年以后，我还能用同样简单的方式继续写文章，那这次折腾就值得。
