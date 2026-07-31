---
title: "从飞牛迁到黑群晖：六块盘、一个电源，和三次判断失误"
date: 2026-07-31T15:40:00+08:00
draft: false
tags: ["黑群晖", "Xpenology", "DSM", "飞牛", "fnOS", "NAS", "SHR", "Docker", "迁移", "硬件排障"]
categories: ["NAS", "折腾记录"]
description: "把 6 盘位 NAS 从飞牛迁回黑群晖 DSM 7.3 的完整记录：抢救 13T 数据、SHR 重建、18 个 Docker 服务恢复。以及排障途中我三次下错结论——把硬件问题判成软件问题、把自家线材认成别家的、把用户的目录需求理解反两次。"
typora-root-url: /Users/leesdove/Documents/blog/static
---

> 文中所有 IP、序列号、密钥均已脱敏。

上一篇写了[「掉盘疑案，真凶是电源」](/posts/feiniu-to-xpenology-power-culprit/)，那时候刚定位到病根。这篇是后续：换电源、装系统、抢救数据、恢复服务，直到整套跑起来。

跨度不小，中间我下错过三次结论。技术细节值钱，但那三次错更值钱。

## 一、换电源之后：先验证，再动数据

新电源装上，第一件事不是急着拷数据，而是**压力测试**。

理由很简单：硬件不稳的时候搬 13T，等于拿数据赌运气。

```bash
# 6 盘并发满速只读，每盘 30GB
for d in sata1 sata2 sata3 sata4 sata5 sata6; do
  ( dd if=/dev/$d of=/dev/null bs=1M count=30000 iflag=direct & )
done
wait
```

前后对比 `dmesg`：

```bash
dmesg | grep -icE "hard reset|link down|COMRESET|unplugged|failed command|ATA bus error"
```

结果：**186GB 并发读取，六块盘全部 260-273MB/s 满速，dmesg 零新增错误。**

对比换电源前——同样 6 块盘，一加压力就 `hard reset`、`COMRESET failed`、`device unplugged` 刷屏。至此供电问题确认解决。

**这套压测方法可以复用**：全程只读，不写入任何数据，安全。判断标准不是"能不能跑完"，而是"dmesg 有没有新增链路错误"。

## 二、抢救数据：只读挂载是硬保证

飞牛的存储结构和群晖几乎同构（`mdadm` + `LVM` + `btrfs` 三层），所以数据盘插到 DSM 上能手动读出来。

关键是**全程只读**：

```bash
# 组装阵列，--readonly 从内核层面禁止写入
mdadm --assemble --readonly /dev/md20 /dev/sata5p1

# DSM 的 LVM 有设备过滤器，必须用 --config 覆盖才扫得到外来卷
CFG="devices{filter=[\"a|/dev/md20|\",\"r|.*|\"]}"
pvs --config "$CFG"
vgchange -ay --config "$CFG"

# 只读挂载
mount -t btrfs -o ro /dev/mapper/trim_xxxx-0 /mnt/fnos
```

挂上之后 `df` 显示 14T/已用 13T，目录结构完整。**即便中途出过 I/O 错误，因为全程只读，源盘一个字节都没被动过。**

有个坑：加 `nospace_cache` 参数会报 `wrong fs type`，直接 `-t btrfs -o ro` 就行。

### 意外发现：13T 会膨胀成 187T

准备拷贝时我算了一笔账：

```bash
du -sh --count-links /mnt/fnos/data   # 187T
du -sh /mnt/fnos/data                 # 13T
```

差了 14 倍。原因是 PT 辅种玩法产生的**海量硬链接**——抽样看，一部剧的每个文件有 38 个硬链接（辅到了 38 个站）。

**如果用普通 `cp` 或拖拽复制，硬链接会被还原成独立文件，13T 直接变 187T**，新池装不下不说，辅种关系全毁。必须用 `rsync -aHAX`（`-H` 保留硬链接）或 `cp -a`，而且要一次性整体拷贝——分批拷会切断跨批次的硬链接。

（后来我决定放弃这批数据，这条没用上。但这个坑值得记下来。）

## 三、三次判断失误

### 失误一：把硬件问题判成软件问题

这是最典型的一次。

现象是 6 块盘飞牛只认 4 块。我拔掉数据盘、用 RR 引导启动，`lsblk` 一次认全 5 块——**于是我下结论："是飞牛的软件问题，换系统就好了"**，还信心满满写进了排查记录。

错在哪？**RR 里那 5 块，是数据盘被拔掉之后的 5 块。故障只在 6 块盘时出现。我验证的配置，和出故障的配置根本不是同一个。**

真相是装完 DSM、插满 6 块盘之后才暴露的：`dmesg` 里 `ata1`、`ata2`、`ata5` 多条链路同时复位掉线——**多块盘同时出问题，几乎只有供电一个解释**。

> **教训：用来下结论的那次测试，必须和故障发生的条件完全一致。否则测得再干净，也是假验证。**

### 失误二：把自家的线认成了别家的

换完电源不 POST，风扇转、灯亮、屏幕无信号。排查中看到线材上印着 `CMPSU`，我立刻联想到 Corsair（海盗船）的老型号前缀 CMPSU-750TX，于是紧急警告用户"跨品牌混用模组线，有烧主板风险"。

结果人家说：这是新电源自带的线，一头印 `CPU`（接主板）、一头印 `CMPSU`（接电源）。

**`CMPSU` = Cooler Master PSU**，就是酷冷自己标注线材两端用途的方式。我看到缩写就往记忆里那个更"耸动"的解释上套，没考虑更直接的可能。

真正的原因平淡得多：**内存条接触不良**——拆装电源时手在机箱里活动碰松了。重插一次就 POST 了。

> **教训：缩写有歧义时，先看上下文里最直接的解释（这是酷冷的电源，CM 就是 Cooler Master），别急着套用记忆里的稀有案例。**

### 失误三：把同一个需求理解反了两次

用户说："在 docker 文件夹内建一个 compose 文件夹，然后把所有服务放进去。"

我做成了：compose 文件集中在 `docker/compose/<服务>/`，配置数据留在 `docker/<服务>/`——**两地分离**。

用户问："配置数据为啥不能放在他们服务 emby 里面呢？"

我理解成"compose 该退回 `docker/emby/` 和数据放一起"，于是把 compose 文件全搬回去了。

结果人家说：**应该是 `docker/compose/emby`**。

他的意思**从头到尾都是**：整个服务（compose 文件 + 配置数据）都进 `docker/compose/<服务>/`。我第一次理解成"只有 compose 进去"，第二次理解成"compose 退出来"，**方向连错两次**。

> **教训：当对方对同一件事二次追问时，说明第一次的理解就偏了。这时应该先复述确认目标状态，而不是顺着自己的理解再改一版。**

## 四、恢复 18 个服务踩的坑

配置从备份恢复后，起服务时几个典型问题：

### 只 chown 不够，还要 chmod

`tar` 恢复会保留原权限位。emby 的配置目录是 `dr-xr-xr-x`（无写权限），emby 写不了日志就崩溃重启。

```bash
chown -R 1026:100 /volume7/docker    # 我只做了这个
chmod -R u+rwX,g+rwX /volume7/docker # 这个才是关键
```

顺带：硬件转码要 `chmod 666 /dev/dri/card0`，默认是 `crw-------` 只有 root 能用。

### 权限修好了，服务也不会自己好

Prowlarr 容器显示 `Up 40 hours`，但端口不通。日志里是 `AppFolder /config is not writable`——它在权限修好**之前**就启动失败，然后卡在 `waiting for user intervention` 不再重试。

**修完权限必须重启容器**，容器状态 `Up` 不代表里面的进程是活的。

### Immich 要求预先建好目录标记

```
Failed to read (/data/encoded-video/.immich): ENOENT
```

它要求六个子目录里各有一个 `.immich` 空文件：

```bash
for d in thumbs upload backups library profile encoded-video; do
  mkdir -p $PHOTO_ROOT/$d && touch $PHOTO_ROOT/$d/.immich
done
```

### uid/gid 变了

飞牛的 `leesy` 是 `uid=1000 gid=1001`，DSM 上是 `uid=1026 gid=100`。compose 里所有 `PUID`/`PGID` 都得改，不然容器读不了配置——这是跨系统迁移最常见的翻车点。

## 五、一个反直觉的坑：空壳种子会自己把数据拖回来

我从备份恢复了 transmission 的 4208 个 `.torrent` 文件。但 13T 数据已经被放弃删除了。

结果：**tr 加载全部种子，发现本地没数据，开始自动重新下载。** 等发现时已经拉回来 6.2G。

面板上的读数很分裂：

```
0 部     影视 · 另有 0 首音乐    ← 真实（媒体库空的）
4208     做种中                  ← 空壳种子
↓48.8KB/s 保种上传中             ← 它在重新下载
```

海报墙上还挂着一堆早就不存在的电影——那是数据库里的历史记录。

**放弃旧数据时，种子文件和各服务数据库的历史记录必须一起清**，否则它会替你把数据"找回来"。

清理时我还犯了个小错：按"预设表名列表"删数据库记录，漏掉了实际存在的两张表。正确做法是遍历真实表名：

```python
tabs = [r[0] for r in cur.execute(
    "SELECT name FROM sqlite_master WHERE type='table'")]
for t in tabs:
    if t.startswith("sqlite_"): continue
    cur.execute(f"DELETE FROM {t}")
cur.execute("DELETE FROM sqlite_sequence")   # 重置自增
c.commit(); cur.execute("VACUUM")
```

## 六、最终结构

拆分 compose 之后的样子：

```
/volume7/docker/
├── .env                    # 密钥集中
├── up-all.sh / down-all.sh # 一键启停
├── scripts/
└── compose/
    ├── emby/{docker-compose.yml, .env->../../.env, config/ cache/ metadata/}
    ├── prowlarr/{docker-compose.yml, prowlarr.db ...}
    └── ...
```

每个服务自包含——备份就是拷一个目录，改配置不用跳来跳去，删服务不留孤儿文件。

**拆分有个前提条件**：拆开后每个 compose 会建自己的网络，容器就无法用名字互访了。必须建一个共享外部网络：

```bash
docker network create nas
```

```yaml
networks:
  default:
    name: nas
    external: true
```

`network_mode: host` 的服务不需要这段。另外有依赖关系的容器组（比如 Immich 的 server/postgres/redis 有 `depends_on`）必须留在同一个 compose 文件里，拆开会起不来。

顺带把不用的服务删了：cross-seed、MoviePilot、IYUU、Immich——它们的活已被自研的工具接管。加上 `docker image prune -af`，一共回收约 9.4G，容器从 18 个减到 11 个。

## 最终状态

| | |
|---|---|
| 硬件 | 电源换掉，6 盘满载压测零错误 |
| 存储 | SHR 70T + 单盘容错 |
| 系统 | DSM 7.3，固定不升级 |
| 服务 | 11 个核心服务 |
| 硬盘 | 重分配扇区 0、待处理扇区 0；通电 3.9 至 4.7 年 |

## 写在最后

这趟折腾里，技术上最值钱的是那套「只读挂载 + 压力测试先行」的纪律——它保证了 13T 数据在整个过程中一个字节都没被误伤。

但真正让我记住的是那三次判断失误，它们其实是同一类错误的三个变种：

- **失误一**：用"差不多"的测试代替真正该做的测试
- **失误二**：看到缩写就套用记忆里的解释，忽略了更直接的可能
- **失误三**：对方二次追问时，没意识到是自己第一次就理解偏了

共同点是**急于给出结论**。而正确的做法都很朴素：验证条件要和故障条件一致；解释歧义要先看上下文；对方重复问同一件事，先复述确认再动手。

`dmesg` 不会撒谎，硬件不会撒谎，需求也不会撒谎。会撒谎的，是急着往下走的那个自己。
