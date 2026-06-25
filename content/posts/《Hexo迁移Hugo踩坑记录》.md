+++
date = '2026-06-25T19:52:37+08:00'
draft = false
title = '《Hexo迁移Hugo踩坑记录》'

+++

说实话，我感觉自己是个笨人。别人两个小时就可以干完的，我需要花费差不多两天才能搞定。尤其是对于这个编程软件之类的，自己总是勤勤恳恳学习，但收获总是不大。从23年在公司安监部借调期间，搭建的hexo博客，上线不到3个月就因为工作太忙而弃之不用。一直到26年年中，才因为一个偶然的机会，主要是AI技术发展太快了，让我这等笨人，也能在自然语言的交流下，实现了github、hugo、cloudflare的一些实用功能。从而让我尘封已久的想法慢慢变成了现实。

第一个，再次搭建一个hugo博客。按照AI的话说，这个很简单，十分钟就帮我搞定。结果我从上午折腾到了下午，又从下午折腾到了晚间，终于经过不断的努力尝试排错，让我这个简陋的博客，正式上线啦。

附上美美的照片：

![image-20260625210146996](/Users/leesdove/Documents/blog/static/images/《Hexo迁移Hugo踩坑记录》/image-20260625210146996.png)

期间主要经历了以下坑：

1、Hexo → Hugo 迁移

2、图片路径调整

3、GitHub 仓库管理

4、Git 基本操作（commit、push、pull、rebase）

5、GitHub Actions 自动部署

6、GitHub Pages

7、Cloudflare 自定义域名

8、DNS 排查

9、Hugo Front Matter 格式

这每一个，对我来说都是全新内容，加上AI，它的信息并不是最新的，导致它说的很多地方找不到，然后就再次询问，一来二去的，导致一个小问题，别人1秒可以搞定，我却需要半小时才搞明白。

为了不让以后的写博客之路出现故障，在此，我对其中的主要操作细节和流程进行一个记录和复盘，便于以后回顾。

博客地址：

###### https://blog.leesy.cc

源码仓库：

###### https://github.com/zkzkeep/blog

# 一、博客目录位置

Mac 本地博客目录：

这是正文

```toml
~/Documents/blog
```

进入博客目录：

```
cd ~/Documents/blog
```

确认是否进入成功：

```
pwd
```

应该显示：

```
/Users/leesdove/Documents/blog
```

------

# 二、本地预览博客

进入博客目录：

```
cd ~/Documents/blog
```

启动 Hugo：

```
hugo server
```

浏览器访问：

```
http://localhost:1313
```

停止服务：

```
Ctrl + C
```

------

# 三、新建文章

## 方法一（推荐）

打开 Typora

新建文件

保存到：

```
~/Documents/blog/content/posts/
```

文件名例如：

```
我的第一篇文章.md
```

文章模板：

```
+++
title = "我的第一篇文章"
date = 2026-06-25
draft = false
tags = ["生活"]
categories = ["随笔"]
+++

这里开始写正文
```

------

## 方法二（Hugo命令）

必须先进入博客目录：

```
cd ~/Documents/blog
```

创建文章：

```
hugo new posts/我的第一篇文章.md
```

生成内容类似：

```
+++
title = '我的第一篇文章'
date = '2026-06-25T20:00:00+08:00'
draft = true
+++
```

注意：

```
draft = true
```

表示草稿。

发布前必须改：

```
draft = false
```

否则网站不会显示。

------

# 四、图片管理

统一放到：

```
~/Documents/blog/static/images/
```

例如：

```
static/images/book/pride.jpg
```

文章引用：

```
![](/images/book/pride.jpg)
```

注意：

正确：

```
/images/book/pride.jpg
```

错误（Hexo旧格式）：

```
./../images/book/pride.jpg
```

------

# 五、发布文章

进入博客目录：

```
cd ~/Documents/blog
```

添加修改：

```
git add .
```

提交：

```
git commit -m "新增文章"
```

上传：

```
git push
```

------

# 六、如果 git push 被拒绝

错误类似：

```
rejected
fetch first
```

解决：

```
git pull origin main --rebase
```

然后：

```
git push
```

------

# 七、查看部署状态

打开 GitHub 仓库。

点击：

```
Actions
```

查看最新任务。

正常情况：

```
Deploy Hugo site to Pages
✔ build
✔ deploy
```

全部绿色。

------

# 八、查看网站是否更新

等待约：

```
1~2分钟
```

访问：

blog.leesy.cc

确认新文章是否出现。

------

# 九、Cloudflare DNS 配置

正确配置：

```
Type: CNAME

Name: blog

Target: zkzkeep.github.io

Proxy Status:
DNS Only（灰云）
```

不要使用：

```
Proxied（橙云）
```

------

# 十、GitHub Pages 配置

仓库：

```
blog
```

进入：

```
Settings
→ Pages
```

配置：

```
Source:
GitHub Actions
```

不是：

```
Deploy from branch
```

------

# 十一、常见故障排查

## 网站404

先检查：

```
Actions
```

是否全部绿色。

然后检查：

```
Settings
→ Pages
```

是否：

```
Source = GitHub Actions
```

------

## 图片不显示

检查路径是否为：

```
![](/images/xxx.jpg)
```

不要使用：

```
![](./../images/xxx.jpg)
```

------

## 文章不显示

检查：

```
draft = false
```

如果：

```
draft = true
```

网站不会显示。

------

## Hugo报错

例如：

```
ERROR no existing content directory configured for this project
```

原因：

没有进入博客目录。

正确：

```
cd ~/Documents/blog
```

然后再执行：

```
hugo new
```

------

# 十二、备份关键文件

工作流文件：

```
~/Documents/blog/.github/workflows/hugo.yml
```

建议备份一份到桌面：

```
cp .github/workflows/hugo.yml ~/Desktop/
```

------

# 十三、我的日常博客流程

以后写文章只需要：

```
Typora写文章
↓
保存到content/posts
↓
本地预览(hugo server)
↓
git add .
↓
git commit -m "新增文章"
↓
git push
↓
等待1~2分钟
↓
博客自动更新
```

------

这份文档建议你直接保存为：

```
博客维护手册.md
```

放到：

```
~/Documents/blog/
```



