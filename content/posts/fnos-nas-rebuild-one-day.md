---
title: "从格式化到满血复活：飞牛 NAS 一天重建记（附两桩网速悬案的破案过程）"
date: 2026-07-15T23:30:00+08:00
draft: false
tags: ["飞牛OS", "NAS", "Docker", "Cloudflare Tunnel", "qBittorrent", "MoviePilot", "Tailscale", "PT", "网络排障"]
categories: ["NAS", "折腾记录"]
description: "从群晖转投飞牛，全盘格式化推倒重来。一天之内把 11 个 Docker 容器、9 个二级域名、PT 下载保种链路全部搞回来——而且大半程我人在火车和酒店，全靠 Tailscale 远程操作。顺手破了两桩悬案：『运营商限速』其实是种子没人做种，keepfrds 连不上是因为人家 tracker 只有 IPv6。"
typora-root-url: /Users/leesdove/Documents/blog/static
---

## 起因

用了几年群晖，最终还是转投了飞牛（fnOS）。硬件是自组的：两条 NVMe（256G 系统 + 512G 致态）加五块西数 HC550 16T 氦气盘。既然换系统，索性全盘格式化推倒重来——代价是之前攒的一堆服务全没了：MoviePilot、Vaultwarden、Navidrome、Mihomo、qBittorrent、Transmission、Emby、IYUU……

这次重建有个特殊情况：我当天要出差。所以整个过程变成了一场行为艺术——**人在火车上和酒店里，通过 Tailscale 远程把一台刚格式化的 NAS 从零建成满血影音站**。动手的主力是 Claude Code，我负责在手机上点头和输密码。

## 底座：SSH、Docker 和镜像加速

飞牛底层是 Debian 12，开 SSH 后第一件事是配免密钥登录（专用 ed25519 密钥，不跟其它服务器混用）。普通用户没有免密 sudo，但把用户加进 docker 组后，容器相关操作就完全不需要 root 了：

```bash
sudo usermod -aG docker <用户名>
```

真正的第一道坎是**拉镜像**。Docker Hub 直连超时，国内镜像加速站又各有各的脾气：

- `docker.m.daocloud.io`：稳定，但**有白名单**——`metacubex/mihomo`、`iyuucn/iyuuplus-dev`、`hisatri/lrcapi` 这类小众镜像会被它明确拒绝（错误信息里还带 emoji 🚫）；
- `docker.1ms.run`：没有白名单，但偶发 `unknown blob`，重试就好；
- 策略：主流镜像走 daocloud，被拒的换 1ms.run，全部在 compose 里写死镜像前缀，不依赖 daemon.json（那需要 root）。

## 服务栈与硬盘规划

十一个容器一个 compose 管完，核心规划两条：

**配置与数据分家**：所有容器的配置/数据库放 512G SSD（小文件随机读写快，Emby 元数据受益最明显），下载和媒体库放 16T 机械盘。

**下载和媒体库必须同盘**：MoviePilot 整理用硬链接，跨盘就退化成复制。qb、tr、MP、Emby 四个容器挂载同一个宿主目录、容器内路径统一叫 `/data`——这是整条自动化链路无缝衔接的前提：

```
/data/downloads/qb/{movies,tv}   ← qb 分类下载
/data/media/{movies,tv,music}    ← MP 硬链接入库，Emby 直接读
```

五块机械盘的分工：一块主战场（下载+保种+媒体库），一块留作扩容，一块个人数据/相册，一块备份，一块冷备。SSD 上的容器配置以后定期往备份盘倒。

## Cloudflare Tunnel 复活

之前群晖时代用 Cloudflare Tunnel 发布了一堆二级域名（影视、下载器、密码库……）。格式化只干掉了 NAS 上的连接器，隧道和主机名配置在 Cloudflare 云端都还活着——所以恢复只需要：

1. Zero Trust 后台把隧道 Token 复制出来；
2. NAS 上跑一个 `cloudflared` 容器（**host 网络模式**，这样云端配置里的 `localhost:端口` 原样生效）；
3. 把两条端口变化的路由改掉（群晖后台 5000 → 飞牛 5666，Vaultwarden 换了宿主端口）。

十来分钟，九个域名全部回线。整个过程不需要公网 IP、不碰路由器。

## PT 玩家的版本执念

下载器版本是 PT 站的硬约束，`latest` 是万万用不得的：

- **qBittorrent 锁 `4.6.7-libtorrentv1`**：5.x 很多站不认；libtorrent 1.2 内核对 PT tracker 的兼容性和做种稳定性也比 2.x 靠谱，linuxserver 镜像有现成的 `-libtorrentv1` 标签；
- **Transmission 锁 `4.0.6`**：4.0 系最终版，各站普遍白名单。

紧接着踩了第二个 PT 特色坑：种子添加后 tracker 直接甩脸——

> Port 6881 is blacklisted.

6881 是 BT 默认端口段，正经 PT 站直接拉黑。换成高位随机端口（5 万段），tracker 立刻转绿。

## 悬案一：「运营商把我限速了」

晚上下载跑起来，速度只有 10MB/s 出头。千兆宽带啊，第一反应：运营商限速，而且限得超级狠。

但 10MB/s ≈ 80Mbps 这个数字太"整"了，先别急着骂运营商，**撇开 BT 直接对 CDN 测速**：

```bash
curl -o /dev/null -w "%{speed_download}" https://mirrors.tuna.tsinghua.edu.cn/speedtest/1000mb.bin
# 100217509 B/s ≈ 800 Mbps
```

管道根本没问题。回头看 qb 里那几个种子：做种人数 3、3、0。**几百 GB 的冷门大包，全网就三个人在做种，人家上行就那么点，你管道再粗也没用。**换了几个几十人做种的热种，三个任务合计瞬间怼到 100MiB/s，千兆跑满。

> 教训：BT 速度慢，先看做种人数，再测裸管道，最后才轮到怀疑运营商。

## 悬案二：keepfrds 的种子死活不动

另一个站的种子卡在"等待"，tracker 报 `skipping tracker announce (unreachable)`。

逐层排查：

```bash
# 宿主机上直连 tracker —— 通（403 是 Cloudflare 对裸请求的正常响应）
curl https://tracker.keepfrds.com/announce.php   # 403 ✓

# qb 容器里 —— 完全不通
docker exec qbittorrent curl ...                  # code=000 ✗

# 宿主机强制 IPv4 —— 不通！强制 IPv6 —— 通！
curl -4 ...  # 000 ✗
curl -6 ...  # 403 ✓
```

真相：**这家 tracker 是 IPv6-only**。宿主机有电信下发的公网 IPv6 所以能通，qb 蹲在 Docker 默认的桥接网络里只有 IPv4，announce 根本发不出去。

修法简单粗暴：qb 改 **host 网络模式**。副作用全是正面的——qb 直接监听在公网 IPv6 上，IPv6 的 peer 可以主动连进来，连通性白赚一截（这在双栈普及的今天对上传量是实打实的加成）。唯一注意：host 模式后其它容器不能再用容器名访问 qb，MP 和 IYUU 里的地址要改成宿主机 IP。

## 全程远程的几个小技巧

- **Tailscale 是生命线**。出门前五分钟在 NAS 上装好，人在酒店照样 SSH。中途它的 SSH 会话检查要求浏览器重新验证一次，属正常机制别慌；
- **光猫管理页也能远程看**：`ssh -L 8181:192.168.1.1:80 <NAS>`，本地浏览器开 `127.0.0.1:8181` 就是家里光猫的管理界面。查每个 LAN 口的协商速率不用等回家；
- **人在外地时别远程改桥接**。光猫一切桥接就停止拨号，NAS 跟着失联，现场没人救——这种操作留给回家的周末；
- MoviePilot 拉不到 GitHub 插件库？NAS 上反正跑着 mihomo，给 MP 加一行 `PROXY_HOST` 指过去，306 个插件立刻列出来。

## 硬盘温度与休眠的小尾巴

下载高峰期五块盘 39-42°C，有人会慌。不用：HC550 这类氦气企业盘工作上限 60°C，30-45 是舒适区，Backblaze 的统计甚至说太凉（<25°C）故障率反而高。

休眠还是不休眠？企业盘按 7×24 旋转设计，**不休眠完全没问题**；真正伤盘的是频繁启停循环。闲置盘一年空转电费几十块，买个省心，值。

## 总结

- 全盘格式化不可怕，可怕的是没有一套**可复现的重建方案**。一个 compose 文件 + 云端还活着的隧道配置，一天全量恢复；
- 镜像加速站要备两三个，白名单和 unknown blob 都是日常；
- PT 三定律：**版本要老（白名单内）、端口要高（避开 6881）、速度先怪种子再怪网**；
- 容器网络的 IPv6 是个盲区——tracker/站点连不上时，记得测一把 `curl -4` vs `curl -6`；
- 下载目录和媒体库同盘 + 统一容器内路径，是硬链接自动化的地基,规划的时候就要想好；
- Tailscale + SSH 隧道，人在天边也能把家里的网络设备摸个遍。

至此，从一块白盘到 11 个容器、9 个域名、千兆跑满的 PT 影音站，用时一天，其中大半程在时速三百公里的高铁上。工具越来越顺手，折腾越来越像享受。
