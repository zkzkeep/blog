---
title: "Git 学习心得"
date: 2026-06-27T13:49:00+08:00
draft: false
tags:
  - Git
  - 学习
  - 技术
typora-root-url: /Users/leesdove/Documents/blog/static
---

# Git 学习心得

> 一个非程序员的 Git 入门记录，从零开始，亲手操作，真实体验。

---

## 一、为什么要学 Git

作为非技术背景的人，和程序员打交道时经常感觉在看天书。学习 Git、Linux、Python，不是为了转行做程序员，而是为了能看懂他们在做什么，更好地沟通和协作。

Git 是程序员每天都在用的工具，理解它之后，很多"理所当然"的程序员思维就能看懂了。

---

## 二、版本控制是什么

**版本控制就是"时间机器 + 平行宇宙"。**

普通人管理文件的方式：

```
策划案.docx
策划案_v2.docx
策划案_最终版.docx
策划案_真的最终版_改了甲方意见.docx
```

文件夹里一堆，完全不知道哪个改了什么。

Git 解决的正是这个问题。它提供三个超能力：

- **时间机器**：随时回到任何一个"存档点"，哪怕是三个月前
- **平行宇宙（分支）**：开一条新线去尝试大改动，不满意就丢掉，完全不影响原版
- **改动记录**：每次存档都附一句话说明"改了什么、为什么改"，永远查得到

---

## 三、Git 的三个区域

理解这三个区域，Git 的所有操作就都通了：

```
工作区  →  git add  →  暂存区  →  git commit  →  仓库
（编辑文件）           （购物车）                （永久存档）
```

- **工作区**：你实际编辑文件的地方
- **暂存区**：`git add` 之后文件放这里，相当于"购物车"
- **仓库**：`git commit` 之后永久保存，不会丢失

**比喻**：`git add` 是把东西放进购物车，`git commit` 是结账——这次购物就永远记录下来了。

---

## 四、第一次实操记录

### 环境
- 系统：Mac
- Git：已安装（通过 `git --version` 确认）

### 建立第一个仓库

```bash
cd ~/Documents/Git
mkdir 我的第一个项目
cd 我的第一个项目
git init
```

输出：
```
Initialized empty Git repository in /Users/leesdove/Documents/Git/我的第一个项目/.git/
```

看到这句话就说明成功了，Git 开始"监视"这个文件夹了。

### 创建第一个文件

```bash
nano README.md
```

写入内容后，`Control + X` → `Y` → 回车 保存退出。

### 第一次 git status

```bash
git status
```

输出：
```
On branch main

No commits yet

Untracked files:
  (use "git add <file>..." to include in what will be committed)
        README.md
```

`Untracked files` 意思是：Git 发现这个文件了，但还没开始追踪它（显示红色）。

### git add

```bash
git add README.md
git status
```

输出：
```
Changes to be committed:
        new file:   README.md
```

文件变成绿色，进了"购物车"，准备好存档了。

### 第一个 commit

```bash
git commit -m "首次提交：创建了README.md文件，真开心！"
```

输出：
```
[main (root-commit) 8cfeaf0] 首次提交：创建了README.md文件，真开心！
 1 file changed, 2 insertions(+)
 create mode 100644 README.md
```

- `root-commit`：这是仓库的第一个 commit，"根"的意思，只出现这一次
- `8cfeaf0`：这个 commit 的唯一 ID，将来回到这个时间点就用它
- `main`：分支名，一直都存在，不会变

---

## 五、关键概念理解

### git status 是什么

`git status` 是"查看当前状态"，就像问 Git："现在情况怎么样？"

它会告诉你：
1. 哪些文件改了但还没 add（红色）
2. 哪些文件已经 add、等待 commit（绿色）
3. 有没有什么异常

`git status` 不会改变任何东西，随时可以敲，没有副作用。**遇到任何不确定的时候先敲它。**

### 为什么改了文件还要 add，不能直接 commit？

`add` 给你"选择权"。

假设你同时改了三个文件，只想把其中两个存档，第三个还没写完——`git add` 让你挑选这次 commit 打包哪些文件。

**`add` 不是"增加"，更像是"挑选"**——把准备好的东西放进购物车。

如果确实想跳过 add，直接提交所有已追踪文件的改动：

```bash
git commit -a -m "备注"
```

但新文件第一次还是必须 `git add`。

### git add 什么时候加引号

文件名有空格或特殊字符时必须加引号，没有就不用：

```bash
git add README.md          # 没空格，不用引号
git add "my file.md"       # 有空格，必须加引号
```

**好习惯**：命名文件时不用空格，用下划线或短横线代替，永远不用担心引号问题：

```
my_file.md
my-file.md
```

### commit 备注写什么

`-m` 后面的内容完全可以随便写，Git 不限制格式。

将来翻历史记录时，好的备注让你一眼看出"这次改了什么"：

```
# 不好的备注
a1b2c3  改了东西
d4e5f6  又改了

# 好的备注
a1b2c3  新增用户登录功能
d4e5f6  修复了点击按钮没反应的bug
```

**一句话说清楚"做了什么"，将来的自己会感谢现在的自己。**

---

## 六、时间机器——穿越历史

### 查看历史记录

```bash
git log --oneline
```

输出：
```
ae147d5 (HEAD -> main) 第二次提交README.md文件
8cfeaf0 首次提交：创建了README.md文件，真开心！
```

- `HEAD -> main`：箭头指着你现在所在的位置
- 从下往上是时间顺序

### 跳回过去

```bash
git checkout 8cfeaf0
```

输出：
```
HEAD is now at 8cfeaf0 首次提交
```

此刻打开文件，内容变回了最初的样子。

**`detached HEAD` 不用怕**：正常状态下你站在一个分支上，像站在行驶的火车上。`detached HEAD` 是你跳下火车，站在铁轨上的某个固定点，可以四处看看，但不属于任何一列车。

### 跳回现在

```bash
git checkout main
```

文件恢复最新版本。文件夹里始终只有一份文件，Git 在背后管理所有版本。

### checkout 的本质

在 Git 眼里，**分支和版本号本质上是同一种东西——都是指向某个 commit 的指针**。

```
git checkout 8cfeaf0   → 跳到固定坐标，不会移动
git checkout main      → 跳到路标，随新commit自动移动
```

`checkout` 只做一件事：**把 HEAD 挪过去**，目标是什么都行。

新版 Git 把它拆成了两个更清晰的命令：

| 老命令 | 新命令 | 用途 |
|--------|--------|------|
| `git checkout main` | `git switch main` | 切换分支 |
| `git checkout -- README.md` | `git restore README.md` | 恢复文件 |
| `git checkout 8cfeaf0` | 还是用 `git checkout` | 跳到历史版本 |

老命令 `checkout` 依然可以用，网上教程大多也还在用它。

---

## 七、平行宇宙——分支

### 分支是什么

**main 本来就是一个分支**，只不过是默认创建的那个。Git 里所有分支地位完全平等，main 只是名字叫 main 而已。

### 创建并切换分支

```bash
git branch 分支功能        # 创建分支
git branch                 # 查看所有分支（* 号表示当前所在分支）
git checkout 分支功能      # 切换过去
```

输出：
```
* 分支功能
  main
```

星号从 main 跑到了分支功能上，切换成功。

### 在分支里提交

```bash
nano another_README.md
git add another_README.md
git commit -m "分支功能的第一个文件"
```

输出：
```
[分支功能 6c2bbf1] 分支功能的第一个文件
 1 file changed, 1 insertion(+)
 create mode 100644 another_README.md
```

### 平行宇宙的验证

切回 main：

```bash
git checkout main
ls
```

输出：只有 `README.md`，`another_README.md` 消失了！

切回分支功能：

```bash
git checkout 分支功能
ls
```

`another_README.md` 重新出现。

**同一个文件夹，切换分支，文件凭空消失又出现——这就是平行宇宙。**

### 合并分支

实验成功，把分支的成果合并回主线：

```bash
git checkout main
git merge 分支功能
```

输出：
```
Updating ae147d5..6c2bbf1
Fast-forward
 another_README.md | 1 +
 1 file changed, 1 insertion(+)
 create mode 100644 another_README.md
```

`Fast-forward`：main 没有走其他路，分支是从 main 直接长出去的，所以直接把 main 的指针往前推就完成了，是最简单的合并方式。

合并完成后，`another_README.md` 正式出现在主线上。

---

## 八、Git vs GitHub

很多人把这两个混淆，其实是两回事：

- **Git**：装在电脑上的工具，所有操作都在本地，不需要联网，不需要注册账号
- **GitHub**：一个网站，把本地仓库"推"上去，存到云端，别人才能看到

用快递比喻：
- `git commit` = 把东西打包装箱，放在家里
- `git push` = 把箱子交给快递员，发到云端仓库

今天做的所有操作，commit 都存在电脑本地的 `.git` 文件夹里，完全离线，完全私密。

---

## 九、常用命令速查

```bash
git init                    # 在当前文件夹建仓库
git status                  # 查看当前状态（随时可敲）
git add 文件名              # 把文件放入暂存区
git add .                   # 把所有改动放入暂存区
git commit -m "备注"        # 存档，附上说明
git commit -a -m "备注"     # 跳过add，直接提交所有已追踪文件
git log --oneline           # 查看简洁的提交历史
git checkout 版本ID         # 跳到某个历史版本
git checkout 分支名         # 切换分支
git switch 分支名           # 切换分支（新写法）
git branch                  # 查看所有分支
git branch 分支名           # 创建新分支
git merge 分支名            # 把指定分支合并到当前分支
```

---

## 十、今天最大的收获

1. **Git 和 GitHub 不是一回事**，Git 是本地工具，GitHub 是云端平台
2. **`add` 的意义是"挑选"**，不是所有改动都要一起提交
3. **`checkout` 的本质**是把 HEAD 挪过去，不管目标是版本号还是分支名
4. **`detached HEAD` 不用怕**，看完跳回来就行
5. **`git status` 是最好的朋友**，不知道怎么办先敲它
6. **分支就是平行宇宙**，同一个文件夹，切换分支，文件会消失和出现

---

*第一次亲手操作 Git，从建仓库到 commit 到分支到合并，走完了完整的核心流程。下一步：学 GitHub，把本地仓库推到云端。*
