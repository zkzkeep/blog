---
title: "MacBook Air M3 重置后恢复开发环境全记录"
date: 2026-06-28T22:50:00+08:00
draft: false
tags:
  - Mac
  - Apple ID
  - Homebrew
  - Hugo
  - Git
  - GitHub
  - SSH
  - Typora
  - DMIT
categories:
  - 折腾记录
typora-root-url: /Users/leesdove/Documents/blog/static
---

# 前言

2026 年 6 月 28 日，终于把困扰几个月的 Mac Apple ID 登录问题彻底解决了！！！！！

这一天从 Apple ID 登录失败开始，最后一路恢复到了 Homebrew、Hugo、Git、SSH、DMIT、GitHub 推送、Typora 图片配置和博客自动发布。过程很折腾，但最后结果是好的：系统干净了，Apple ID 正常了，博客环境也恢复了。

这篇文章作为一次完整复盘，也作为以后重装 Mac 或换新电脑时的恢复手册。

---

# 一、最初的问题：Apple ID 死活登录不上

这台 MacBook Air M3 之前一直有一个很奇怪的问题：

- 网页端 Apple ID 可以正常登录；
- 短信验证码可以正常收到；
- 但是 macOS 系统设置里登录 Apple ID 时，验证完就报错；
- 有时验证码窗口直接卡死；
- 有时 Apple 账户页面变成空白；
- 新建一个本地用户后，问题依旧。

这说明问题大概率不是 Apple ID 本身，而是 Mac 本地系统层面的 Apple Account 数据损坏。

---

# 二、排查过程

## 17:02 左右：检查网络与 Apple 服务

当时先在终端中检查了时间和 Apple 相关服务器连通性：

```bash
date
ping -c 4 gsa.apple.com
ping -c 4 setup.icloud.com
```

结果显示：

- 系统时间正常；
- `gsa.apple.com` 可以 ping 通；
- `setup.icloud.com` ping 不通，但这个不一定说明异常，因为很多 Apple 服务本身不响应 ICMP。

随后继续排查系统代理。

---

## 17:30 左右：检查系统代理

执行：

```bash
scutil --proxy
networksetup -getwebproxy Wi-Fi
networksetup -getsecurewebproxy Wi-Fi
```

结果显示：

- HTTP 代理未开启；
- HTTPS 代理未开启；
- 系统没有残留代理配置。

因此排除了 Clash、Mihomo、VLESS、Cloudflare Tunnel 等网络工具导致的问题。

---

## 17:40 左右：新建本地用户测试

在：

```text
系统设置 → 用户与群组
```

中新建了一个测试用户。

结果：

- 原用户登录 Apple ID 失败；
- 新用户登录同一个 Apple ID 也失败；
- 但同一个 Apple ID 可以在 iPad 上正常登录。

这一步基本确认：

> Apple ID 本身没有问题，问题在这台 Mac。

---

## 18:30 左右：查看 accountsd 日志

执行：

```bash
log stream --predicate 'process == "accountsd" || process == "AppleAccount"' --info
```

日志中出现过类似信息：

```text
No plugin provides credentials for account.
Falling back to legacy behavior.
```

同时也有大量 Keychain 和 Security 相关查询，但没有明确显示密码错误、验证码错误或 Apple ID 锁定。

这进一步说明问题更像是本机 Apple Account 认证数据库或系统数据异常。

---

## 18:40 左右：检查 Secure Boot 与系统完整性

执行：

```bash
system_profiler SPiBridgeDataType
```

结果显示：

- Secure Boot 正常；
- System Integrity Protection 已启用；
- Signed System Volume 已启用；
- 固件与安全状态正常。

因此排除了硬件安全模块异常。

---

# 三、升级系统没有解决问题

当时系统提示可以升级到新版 macOS，于是尝试升级。

升级完成后，系统界面已经变化，说明大版本系统已经安装成功。但 Apple ID 登录问题依然存在，甚至 Apple 账户页面仍然会出现空白。

这说明：

> 普通覆盖升级不会清除损坏的系统账户数据。

---

# 四、最终解决：抹掉所有内容与设置

最后使用 macOS 自带的：

```text
系统设置 → 通用 → 传输或还原 → 抹掉所有内容与设置
```

重置后重新进入系统。

结果：

- Apple ID 可以正常登录；
- 验证码流程正常；
- 系统设置中的 Apple 账户页面恢复正常；
- iCloud、App Store 等服务正常。

最终确认：

> 真正的问题是 Mac 本地 Apple Account / AuthKit / 系统账户数据库损坏。

这类问题不是升级系统能解决的，必须彻底重建系统数据。

---

# 五、重新安装 Homebrew

系统恢复后，开发环境全部需要重新安装。

先安装 Homebrew。

安装完成后，终端提示需要把 Homebrew 加入 PATH，于是执行：

```bash
echo >> ~/.zprofile
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
```

确认：

```bash
brew --version
brew doctor
```

Homebrew 恢复正常。

---

# 六、安装 Hugo

使用 Homebrew 安装 Hugo：

```bash
brew install hugo
```

确认版本：

```bash
hugo version
```

输出显示 Hugo 已成功安装，并且是 extended 版本。

---

# 七、恢复 SSH

之前已经备份了：

```text
~/.ssh
```

其中包括：

```text
config
dmit.pem
dmit.pub
known_hosts
known_hosts.old
```

把 `.ssh` 文件夹放回：

```text
/Users/leesdove/.ssh
```

注意，不是把里面的文件直接放到用户目录，而是要保持这个结构：

```text
/Users/leesdove/.ssh/config
/Users/leesdove/.ssh/dmit.pem
/Users/leesdove/.ssh/dmit.pub
/Users/leesdove/.ssh/known_hosts
```

恢复权限：

```bash
chmod 700 ~/.ssh
chmod 600 ~/.ssh/*
chmod 400 ~/.ssh/dmit.pem
```

随后测试：

```bash
ssh dmit
```

成功进入 DMIT VPS。

这一步说明 SSH 配置完全恢复。

---

# 八、恢复 GitHub 推送

一开始博客脚本运行后，GitHub 推送失败：

```text
Password authentication is not supported for Git operations.
```

原因是 GitHub 已经不支持账户密码推送。

最开始尝试切换到 SSH：

```bash
git remote set-url origin git@github.com:zkzkeep/blog.git
```

但是由于 GitHub 没有配置当前 Mac 的 SSH 公钥，出现：

```text
Permission denied (publickey).
```

最后决定继续使用 HTTPS + GitHub Personal Access Token。

将远程地址改回 HTTPS：

```bash
git remote set-url origin https://github.com/zkzkeep/blog.git
```

推送时输入：

```text
Username: zkzkeep
Password: ghp_xxx
```

注意这里的 Password 不是 GitHub 登录密码，而是 GitHub Personal Access Token。

随后 Git Push 成功。

---

# 九、恢复 Git 全局配置

设置 Git 用户名和邮箱：

```bash
git config --global user.name "zkzkeep"
git config --global user.email "zkzkeep@gmail.com"
```

检查：

```bash
git config --global user.name
git config --global user.email
```

确认输出：

```text
zkzkeep
zkzkeep@gmail.com
```

随后备份：

```bash
cp ~/.gitconfig ~/Macbookair\ 备份/
```

---

# 十、恢复 Hugo 博客

博客目录恢复到：

```text
/Users/leesdove/Documents/blog
```

进入目录：

```bash
cd ~/Documents/blog
```

运行自动脚本：

```bash
python3 -m scripts.watch
```

脚本可以正常启动，Hugo 构建也成功，Git 提交和推送也恢复。

---

# 十一、重要配置：Typora 图片路径

这是整个博客自动化流程最重要的配置。

系统重置后，Typora 的图片路径会恢复默认。如果不重新设置，图片可能会被引用到：

```text
/Users/leesdove/Library/Application...
```

这样脚本无法找到图片，自动发布会失败。

## 正确设置

进入：

```text
Typora → 偏好设置 → 图像
```

选择：

```text
插入图片时：复制到指定路径
```

固定路径必须是：

```text
/Users/leesdove/Documents/blog/static/images
```

## 特别注意

不要写成：

```text
/Users/leesdove/Documents/blog/static/images/未整理
```

以前的“未整理”方案已经废弃。

现在的图片流程是：

1. Typora 把图片复制到：

```text
/Users/leesdove/Documents/blog/static/images
```

2. `watch.py` 自动扫描文章中的图片；

3. 自动创建文章图片目录，例如：

```text
static/images/文章名/
```

4. 自动把图片整理进去并重命名为：

```text
1.png
2.jpg
3.png
```

5. 自动修改 Markdown 中的图片链接；

6. Hugo 构建；

7. Git Commit；

8. Git Push；

9. Cloudflare Pages 自动发布。

一句话记住：

> Typora 永远只负责把图片复制到 `blog/static/images`，其它所有事情交给 `watch.py`。

---

# 十二、备份开发环境

最后整理了一个固定备份目录：

```text
Macbookair 备份
```

其中包括：

```text
.ssh
blog
Codex
.zprofile
.gitconfig
Brewfile
README.md.textbundle
桌面文件夹
```

## 备份 Homebrew 软件清单

执行：

```bash
brew bundle dump --force
```

生成：

```text
Brewfile
```

以后新 Mac 恢复时，只需要：

```bash
brew bundle
```

即可恢复 Homebrew 安装的软件。

---

# 十三、以后重装 Mac 的恢复顺序

以后重装或换 Mac，可以按照下面顺序恢复：

```text
1. 登录 Apple ID
2. 安装 Homebrew
3. 恢复 ~/.zprofile
4. 执行 brew bundle
5. 恢复 ~/.ssh
6. 执行 chmod 700 ~/.ssh
7. 执行 chmod 600 ~/.ssh/*
8. 执行 chmod 400 ~/.ssh/dmit.pem
9. 恢复 ~/.gitconfig
10. 恢复 ~/Documents/blog
11. 设置 Typora 图片路径为 /Users/leesdove/Documents/blog/static/images
12. 进入 ~/Documents/blog
13. 执行 python3 -m scripts.watch
```

---

# 十四、这次排查的结论

这次问题最终确认：

不是：

- Apple ID 密码错误；
- 不是验证码问题；
- 不是 iCloud 服务器问题；
- 不是代理；
- 不是 Mihomo；
- 不是 Cloudflare；
- 不是 DMIT；
- 不是 GitHub；
- 不是 Hugo；
- 不是 Typora。

真正问题是：

> Mac 本地 Apple Account 系统数据损坏。

最终通过：

```text
抹掉所有内容与设置
```

彻底解决。

---

# 总结

今天虽然折腾了很久，但收获很大。

不仅修好了困扰几个月的 Apple ID 登录问题，还顺便完整恢复并整理了整套开发环境：

- Homebrew
- Hugo
- Git
- GitHub
- SSH
- DMIT
- Typora
- 博客自动发布
- 开发环境备份

以后再重装 Mac，就不会像今天这样从零开始摸索了。

这篇文章就是以后恢复 Mac 的第一份手册。
