---
title: "用家里的 NAS 做私有云盘：公司电脑与 Mac 之间的文件中转方案"
date: 2026-07-04T13:30:00+08:00
lastmod: 2026-07-04T13:30:00+08:00
draft: false
tags: ["群晖", "Xpenology", "File Station", "Cloudflare Tunnel", "Tailscale", "私有云盘"]
categories: ["NAS", "折腾记录"]
description: "公司 Mac 用不了内网U盘，传个文件很麻烦。用家里黑群晖自带的 File Station + Cloudflare 隧道搭了个零成本文件中转盘：Mac 走 Tailscale 上传，公司 Windows 浏览器直接下载。附 DSM 权限隔离的坑（NA 其实是 ACL deny）和一个意外收获——顺手发现一块卷的文件系统坏了。"
typora-root-url: /Users/leesdove/Documents/blog/static
---

## 背景

公司的 Mac 出于安全策略用不了内网U盘，每次想把一个文件从 Mac 挪到旁边能上外网的 Windows 上，都得折腾半天。家里有台黑群晖（SA6400，DSM 7.2），自然就想到：能不能做个私有云盘中转一下？

结论先说：**能，而且一个新东西都不用装**。DSM 自带的 File Station + 已有的 Cloudflare 隧道就够了，全程大概半小时。

## 思路与选型

需求拆开就两条路径：

- **上传**（我的 Mac → NAS）：Mac 上有 Tailscale，直连 NAS，走 SMB 挂载就行，速度等于内网。
- **下载**（NAS → 公司 Windows）：公司电脑只能用浏览器，不能装软件。所以必须有一个 **HTTPS 的公网入口**。

几个方案的取舍：

| 方案 | 结论 |
|---|---|
| Synology Drive 套件 | 功能全，但对"中转文件"这个需求属于杀鸡用牛刀，没装 |
| QuickConnect | **黑群晖别碰**，要绑 Synology 账号和序列号，有被封风险 |
| DDNS + 端口转发 | 需要公网 IP，还得自己管证书和暴露面 |
| **Cloudflare Tunnel（已有）** | 之前就部署了 cloudflared 容器发布 DSM 网页，直接复用 ✅ |

也就是说公网入口是现成的：`https://nas.example.com`（本文域名、账号、密码均已脱敏）反代到 NAS 的 5000 端口，File Station 网页里就能上传下载。

## 实施

### 1. 建一个专用中转共享

不要拿现有的共享文件夹凑合——中转盘要暴露给"公司电脑"这种不可控环境，必须是独立的、可牺牲的。SSH 进 NAS 用 `synoshare` 直接建：

```bash
# 建共享文件夹（放在 SSD 卷上，中转文件读写快）
synoshare --add exchange "文件中转" /volume5/exchange "" "" "" 1 0
```

### 2. 建一个低权限专用账号

**千万不要在公司电脑上登录自己的管理员账号。** 单独建一个账号，密码泄露了也只暴露中转文件夹本身：

```bash
synouser --add exchange-user '<强密码>' "文件中转专用" 0 "" 0
synoshare --setuser exchange /volume5/exchange RW = admin用户,exchange-user
```

### 3. 权限隔离——这里有坑

新建的本地用户默认在 `users` 组里，一测发现它能看到我所有的媒体共享。需要逐个设"禁止访问"（NA）：

```bash
for s in docker media1 media3 media4 media6; do
    synoshare --setuser $s NA + exchange-user
done
```

两个有意思的发现：

1. **DSM 的"禁止访问"底层其实是往目录 ACL 里插一条 deny 条目**（`user:xxx:deny:rwxpdDaARWcCo:fd--`，排在所有 allow 之前）。
2. 但你**不能**自己用 `synoacltool -add` 去加 deny 条目——会报 `unknown error: [8400]`。必须走 `synoshare --setuser <共享名> NA + <用户>`，让 DSM 自己去写。

验证隔离效果可以直接调 File Station 的 WebAPI，看该账号还能列出哪些共享：

```bash
# 登录拿 sid，然后：
curl "https://nas.example.com/webapi/entry.cgi?api=SYNO.FileStation.List&version=2&method=list_share&_sid=$SID"
```

最终该账号只能看到 `exchange` 一个文件夹。

### 4. 全链路验证

从公网走了一遍完整流程：API 登录 → 列目录 → 下载测试文件，HTTP 200，下载响应 1.2 秒。通。

## 日常用法

- **Mac 上传**：Finder ⌘K 连 `smb://nas主机名/exchange`（走 Tailscale），拖文件进去。
- **公司 Windows 下载**：浏览器打开 `https://nas.example.com` → 用专用账号登录 → File Station 里下载。
- 也可以反向：公司电脑上传，Mac 下载，双向皆可。

两个注意事项：

1. **Cloudflare 免费版代理的上传单请求限制约 100MB**，大文件上传走 Tailscale/SMB 那条路；下载不受这个限制。
2. 下载速度上限 = 家里宽带的**上行**带宽，传文档安装包无压力，几十 GB 的大文件要有耐心。

安全清单：只暴露 HTTPS（CF 隧道天然如此）、专用低权限账号、其他共享全部 NA、DSM 开自动封锁和两步验证。最后还是要说一句：如果公司对数据外传有保密管控，这套东西再方便也得先确认合规。

## 插曲：顺手查出一块卷的文件系统坏了

给某个媒体共享设 NA 时一直失败，排查发现它的根目录 `ls` 直接报 `Input/output error`。往下挖：

```bash
btrfs device stats /volume2
# read_io_errs 17376  ← 一万七千多次读错误

dmesg | tail
# BTRFS error: failed to repair parent transid verify failure ...
# md6: [Self Heal] ... error: cannot find a suitable device（单盘卷，无冗余可自愈）
```

但 SMART 显示磁盘本身健康（无坏扇区、无待映射扇区），只有 **UDMA_CRC_Error_Count = 21**——这个特征指向 **SATA 线缆或背板接触不良**，而不是盘要挂了。接触不良导致传输出错，进而把 btrfs 元数据写坏了。

处理思路（还没做完，另开一篇）：先抢救可读数据 → 关机重插/更换 SATA 线 → 走 DSM 存储管理器做文件系统检查。切记**不要**上来就 `btrfs check --repair`，那玩意儿修坏的案例比修好的多。

所以说折腾 NAS 的意外收获：本来只是建个网盘，结果提前发现了一块正在悄悄腐烂的卷。要是等媒体库整个读不出来才发现，哭都来不及。

## 小结

- 黑群晖做私有中转盘，File Station + Cloudflare Tunnel 是最省事的组合，零新增组件。
- 暴露给不可控环境的入口，一定用**专用低权限账号**，并把其他共享显式 NA 掉——新用户默认权限比你想象的大。
- DSM 的 NA 是 ACL deny 条目，只能通过 `synoshare --setuser` 设置，手动 `synoacltool` 加 deny 会报 8400。
- `btrfs device stats` + `dmesg` + SMART 三件套，能把"文件系统报错"定位到"线缆接触不良"这个层面。
