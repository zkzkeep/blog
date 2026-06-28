---
title: "Linux 学习笔记"
date: 2026-06-27T20:36:45+08:00
draft: false
tags: ["Linux", "命令行", "学习笔记"]
categories: ["技术学习"]
description: "Linux 系统学习全记录，从文件系统到权限、进程、网络、Shell脚本，含实操过程和踩坑记录。"
typora-root-url: /Users/leesdove/Documents/blog/static
---

## 第一章·文件系统

### 一、最重要的一个概念：Linux 只有一棵树

Windows 有 C 盘、D 盘，是多个并列的盘。Linux 不一样——**所有东西都挂在一个根目录 `/` 下**，像一棵树，从树根出发，所有文件夹都是树枝。


```
/                        ← 树根，整个文件系统的起点
├── Users/               ← Mac 特有，Linux 是 /home
│   └── leesdove/        ← 你的家目录，即 ~
│       ├── Desktop/
│       ├── Documents/
│       └── ...
├── etc/                 ← 系统配置文件
├── var/                 ← 日志、缓存等动态数据
├── usr/                 ← 软件和程序
└── bin/                 ← 系统基础命令
```

---

### 二、核心目录一句话记忆

| 目录 | 记忆方法 | 放什么 |
|------|---------|--------|
| `/` | 树根 | 整个文件系统的起点，所有人共用 |
| `~` | 你的家 | 展开是 `/Users/你的用户名`，个人文件都在这 |
| `/etc` | Every Thing Config | 所有软件的配置文件 |
| `/var` | variable（变化的）| 日志、缓存、数据库，会随时间增长 |
| `/usr` | Unix System Resources | 软件和程序，大多数命令在 `/usr/bin` |
| `/bin` | binary | 系统基础命令 |
| `/tmp` | temporary | 临时文件，重启后清空 |

**Mac 和 Linux 的一个区别**：Linux 用户目录在 `/home/用户名`，Mac 在 `/Users/用户名`。所以在 Mac 上 `cd /home` 进去是空的，这是正常的。

---

### 三、路径：绝对路径 vs 相对路径

| 符号 | 含义 |
|------|------|
| `/` | 根目录（最顶层） |
| `~` | 家目录（你的用户文件夹） |
| `.` | 当前目录 |
| `..` | 上一层目录 |

**绝对路径**：从根 `/` 出发，不管你在哪，结果都一样：

```bash
/Users/leesdove/Desktop/blog
~/Desktop/blog              # ~ 是绝对路径的缩写
```

**相对路径**：从当前位置出发：

```bash
Desktop/blog                # 假设你现在在 ~ 下
```

**踩坑：`/Documents` 和 `Documents` 不一样**

```bash
/Documents      # 从根目录找，根目录下没有 Documents → 报错
Documents       # 从当前目录找 → 正确（前提是当前在 ~ 下）
~/Documents     # 从家目录找，绝对路径 → 正确
```

记住：**开头有 `/` 就是从根出发，没有 `/` 就是从当前位置出发。**

---

### 四、核心命令详解

#### cd — 切换目录

```bash
cd ~            # 回家目录
cd ..           # 返回上一层
cd ../..        # 返回上两层
cd -            # 回到上一次所在的目录（来回切换很好用）
cd Desktop      # 进入 Desktop（相对路径）
cd ~/Desktop    # 进入 Desktop（绝对路径）
```

**踩坑**：`..` 必须是英文句号，中文的 `。。` 终端不认识。

#### ls — 查看目录内容

```bash
ls              # 列出当前目录的文件
ls Desktop      # 列出 Desktop 里的文件
ls -l           # 显示详细信息（权限、大小、时间）
ls -a           # 显示隐藏文件（以 . 开头的文件）
ls -la          # 两者结合
```

#### pwd — 查看当前位置

```bash
pwd             # 打印当前所在的完整路径
```

不知道自己在哪的时候先敲 `pwd`，就像手机上的"定位"。

#### cp — 复制文件

```bash
cp 源文件 目标位置

cp README.md Desktop/README备份.md          # 复制并重命名
cp Documents/Git/项目/README.md Desktop/   # 复制到另一个目录
cp -r 文件夹名 目标位置                     # 复制整个文件夹（-r 递归）
```

**踩坑**：源文件和目标位置之间必须有空格，写成 `README.mdDesktop/` 终端没法识别。

#### mv — 移动 / 重命名

```bash
mv 源文件 目标位置

mv Desktop/1.md Documents/README备份.md    # 移动 + 改名，一步搞定
mv 旧名字.md 新名字.md                     # 只改名，不移动
mv 文件.md 另一个文件夹/                   # 只移动，不改名
```

`mv` 一条命令可以同时换位置和改名，不需要拆成两步。

#### rm — 删除文件

```bash
rm 文件名               # 删除文件
rm -r 文件夹名          # 删除整个文件夹（-r 递归）
```

**重要警告：Linux 删除没有回收站，删了就没了，不会有任何确认提示。**

好习惯：删除前先 `ls` 看一眼，确认文件名写对了再删。

#### find — 搜索文件

```bash
find 路径 -name '文件名'

find . -name '*.docx'       # 在当前目录搜所有 docx 文件
find ~ -name '*.pdf'        # 在家目录搜所有 pdf
find . -name '恩施*'        # 找所有以"恩施"开头的文件
find . -type f -name '*.md' # 只找文件，不要文件夹
find . -type d              # 只找文件夹
```

`find` 会自动递归进入子文件夹搜索，不管文件藏多深都能找到。

**踩坑一：路径不能省**，`find` 和 `ls`、`cd` 不同，路径是必填的，当前目录用 `.` 代替：

```bash
find -name '*.docx'     # 错误 → 报错
find . -name '*.docx'   # 正确
```

**踩坑二：Mac 的 zsh 里通配符用单引号**，双引号有时会被 zsh 提前展开导致报错：

```bash
find . -name "*.docx"   # 有时报错
find . -name '*.docx'   # 正确
```

**踩坑三：路径要和当前位置对应**：

```bash
# 当时在 / 根目录下
find Desktop -name '恩施*'     # 错误，根目录下没有 Desktop

# 要先 cd ~ 回家，再执行
find Desktop -name '恩施*'     # 正确
```

---

### 五、本章小结

```bash
pwd       # 确认当前位置
ls        # 查看文件
cd        # 跳转目录
cp        # 复制
mv        # 移动/重命名
rm        # 删除（小心！）
find      # 搜索
```

最重要的两个认知：
1. `/` 是根目录，`~` 是家目录，完全不同，不要混淆
2. 路径开头有 `/` 从根出发，没有则从当前位置出发

---

*下一章：权限系统（chmod、sudo、rwx 是什么意思）。*
