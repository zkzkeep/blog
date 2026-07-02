---
title: "NAS 上十来个 Docker 容器的镜像管理:代理、更新、清理、通知一次搞定"
date: 2026-07-02T21:15:00+08:00
draft: false
tags: ["Docker", "群晖", "Diun", "Watchtower", "mihomo", "Synology Chat", "Container Manager"]
categories: ["NAS", "折腾记录"]
description: "NAS 上容器越攒越多,镜像有的七个月没更过,Container Manager 拉镜像还时灵时不灵。这次一并解决:给 dockerd 配上 mihomo 代理、把过期容器更新掉、清出 9GB 垃圾,最后部署 Diun 每天检查镜像更新并推送到 Synology Chat——只通知不自动更,更不更我说了算。"
typora-root-url: /Users/leesdove/Documents/blog/static
---

## 起因

NAS 上的容器不知不觉攒到了 10 个:MoviePilot、Emby、Plex、Navidrome、qBittorrent、Transmission、Vaultwarden、IYUUPlus、cloudflared、mihomo。用是都好用,但一查镜像日期吓一跳:

```
cloudflare/cloudflared:latest    7 months ago
emby/embyserver:latest           7 months ago
linuxserver/plex:latest          7 months ago
deluan/navidrome:latest          4 months ago
vaultwarden/server:latest        2 months ago
```

媒体服务器这种东西七个月不更,安全补丁全欠着。`docker system df` 再一看,还有 6.6GB 的孤儿卷和 900MB 构建缓存躺着吃硬盘。

问题拆开是四件事:

1. Container Manager 拉镜像时灵时不灵(国内镜像加速站不稳定);
2. 一堆容器该更新了;
3. 垃圾没人清;
4. 以后怎么**知道**有更新——总不能定期手动挨个查。

## 思路:通知我,但别替我动手

先说最关键的决策:**不用 Watchtower 全自动更新**。

自动更新在家用 NAS 场景里有几个雷:

- **PT 下载器绝对不能乱升**。qBittorrent 4.6.7 和 Transmission 4.0.5 是故意钉死的版本,PT 站对客户端版本有白名单,自动升级一时爽,账号被 ban 火葬场;
- Vaultwarden、Emby 这类有状态服务,大版本升级偶尔涉及数据迁移,半夜自动升挂了都不知道;
- `:latest` 标签偶尔也有翻车版本,晚几天更新反而是优势。

所以最终形态是:**Diun 每天检查一遍所有镜像,有新版就推送到 Synology Chat;我看到通知后,想更就 SSH 上去两条命令,不想更就无视**。主动权在人手里。

## 第一步:给 dockerd 配上代理

先解决"拉不动镜像"的底层问题。之前 Container Manager 靠四个国内镜像加速站续命,这些站时好时坏。正好 NAS 上跑着 mihomo(7890 端口映射到主机),让 dockerd 自己走代理就行。

DSM 7.2 的 Container Manager 是 Docker 24.0.2,支持在 daemon 配置里直接写 `proxies`,不用碰 systemd。配置文件在 `/var/packages/ContainerManager/etc/dockerd.json`:

```json
{
  "data-root": "/var/packages/ContainerManager/var/docker",
  "log-driver": "journald",
  "log-opts": { "tag": "synology-container" },
  "registry-mirrors": [
    "https://docker.1ms.run",
    "https://docker.xuanyuan.me",
    "https://docker.1panel.live",
    "https://hub.rat.dev"
  ],
  "storage-driver": "btrfs",
  "proxies": {
    "http-proxy": "http://127.0.0.1:7890",
    "https-proxy": "http://127.0.0.1:7890",
    "no-proxy": "localhost,127.0.0.1,192.168.0.0/16,10.0.0.0/8,172.16.0.0/12,100.64.0.0/10"
  }
}
```

三个细节:

- **代理地址用 `127.0.0.1` 而不是局域网 IP**。mihomo 的 7890 映射在主机所有网卡上,dockerd 是主机进程,走回环就行——上次换路由器网段废掉一串配置的教训还热乎着,能不绑 IP 就不绑;
- **镜像加速站保留**。拉镜像时先试加速站,全挂了再直连 docker.io 走代理,双保险;
- `no-proxy` 把内网段都排掉,免得访问本地 registry 之类的流量绕远路。

改完重启守护进程:

```bash
# 注意:会重启所有容器,先确认它们都有 restart 策略
docker ps -a --format '{{.Names}}' | xargs -I{} docker inspect -f '{} {{.HostConfig.RestartPolicy.Name}}' {}

systemctl restart pkg-ContainerManager-dockerd.service
```

十几秒后容器全部自动拉起,`docker info | grep -i proxy` 能看到代理已生效。

## 第二步:更新过期容器

我的容器基本都是 compose 管的(每个应用一个目录,`/volume5/docker/compose/<app>/`),更新就是标准两连:

```bash
cd /volume5/docker/compose/plex && docker compose pull && docker compose up -d
```

Plex、Emby、Navidrome 依次更完,配置和数据都在卷/绑定目录里,无痛。

唯一的例外是 cloudflared——当年图省事直接 `docker run` 起的,没有 compose 文件。重建它有个偷懒神器:**一次性 Watchtower**。它会拉新镜像,然后用**原容器一模一样的配置**重建,用完即走:

```bash
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  containrrr/watchtower --run-once --cleanup cloudflared
```

日志里 `Found new image → Stopping → Creating → Updated=1`,十秒搞定,连旧镜像都帮你清了。

qBittorrent 和 Transmission 原地不动,理由上面说过了。

## 第三步:大扫除

```bash
docker image prune -f          # 悬空镜像(更新后旧镜像都变成 <none>)
docker builder prune -f        # 构建缓存
docker volume prune --all -f   # 无容器引用的卷(清之前先 docker volume ls 过一眼!)
```

孤儿卷清之前我挨个看了内容:6.1GB 是早就删掉的 ChineseSubFinder 留下的缓存,剩下是几个 frpc 和 immich 的残留,都是死数据。三条命令下去:

```
Total reclaimed space: 1.586GB   # 镜像
Total reclaimed space: 900.4MB   # 构建缓存
Total reclaimed space: 6.639GB   # 卷
```

**9.1GB 回来了。** 注意 `volume prune` 是有杀伤力的,别学我无脑 `-f`,先确认里面没有你要的东西。

## 第四步:Diun 更新通知,推到 Synology Chat

[Diun](https://github.com/crazy-max/diun) 是专门干"镜像有新版就通知"这一件事的工具,天生只报信不动手,比 Watchtower 的 monitor-only 模式更纯粹。它自带 cron,不用碰群晖的任务计划。

`/volume5/docker/compose/diun/docker-compose.yml`:

```yaml
services:
  diun:
    image: crazymax/diun:latest
    container_name: diun
    restart: always
    volumes:
      - ./data:/data
      - ./notify.sh:/notify.sh:ro
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - TZ=Asia/Shanghai
      - DIUN_WATCH_WORKERS=5
      - DIUN_WATCH_SCHEDULE=0 9 * * *        # 每天早上 9 点查一遍
      - DIUN_WATCH_JITTER=30s
      - DIUN_PROVIDERS_DOCKER=true
      - DIUN_PROVIDERS_DOCKER_WATCHBYDEFAULT=true   # 默认监控所有运行中容器
      - DIUN_NOTIF_SCRIPT_CMD=/notify.sh
      # Diun 查 docker hub 的 API 也是国外流量,同样走 mihomo
      - HTTP_PROXY=http://192.168.1.48:7890
      - HTTPS_PROXY=http://192.168.1.48:7890
      - NO_PROXY=localhost,127.0.0.1,192.168.0.0/16
```

通知渠道我没用 Diun 内置的那堆(Telegram/Discord/Slack……国内环境都别扭),而是用它的 **script notifier** 调 Synology Chat 的机器人接口——之前折腾 MoviePilot 点播时已经建好了 Chat 机器人,直接复用它的 token,消息发到手机上的 Chat App,零新增依赖。

`notify.sh`(token 自己换):

```sh
#!/bin/sh
# Diun script notifier -> Synology Chat 机器人
WEBHOOK='http://192.168.1.48:5000/webapi/entry.cgi?api=SYNO.Chat.External&method=chatbot&version=2&token=%22YOUR_BOT_TOKEN%22'

# busybox 环境没有 curl 的 --data-urlencode,手动把 payload percent-encode
enc() {
  printf '%s' "$1" | sed \
    -e 's/%/%25/g' \
    -e 's/{/%7B/g' -e 's/}/%7D/g' \
    -e 's/"/%22/g' \
    -e 's/\[/%5B/g' -e 's/\]/%5D/g' \
    -e 's/:/%3A/g' -e 's/,/%2C/g' \
    -e 's;/;%2F;g' -e 's/ /%20/g' -e 's/&/%26/g'
}

TEXT="Docker镜像有更新: ${DIUN_ENTRY_IMAGE} (${DIUN_ENTRY_STATUS})。更新命令: cd compose目录 && docker compose pull && docker compose up -d"
JSON="{\"text\":\"${TEXT}\",\"user_ids\":[4]}"   # user_ids 换成你的 Chat 用户 id

wget -q -O- --post-data "payload=$(enc "$JSON")" "$WEBHOOK"
```

几个踩坑点:

- Chat 机器人的 `chatbot` 接口要的是 `payload=<JSON>` 这种 form 格式,JSON 里的特殊字符得 percent-encode,Diun 镜像里只有 busybox 的 wget,没有 curl 的 `--data-urlencode`,所以自己写了个 `enc()`;
- **用户 id 怎么查**:调机器人的 `user_list` 接口,`method=user_list&version=2&token=...`,返回里有每个人的 `user_id`;
- Diun 主进程走代理查 registry,但 busybox wget 不认大写的 `HTTP_PROXY` 变量,发通知恰好直连 NAS 本机,歪打正着不用配 no_proxy;
- 部署完用 `docker exec diun diun notif test` 发条测试消息,确认链路再收工。

起来之后日志很舒服:

```
Found 10 image(s) to analyze  provider=docker
...
Jobs completed  added=10 failed=0 skipped=0 unchanged=0
Cron initialized with schedule 0 9 * * *
Next run in 11 hours (2026-07-03 09:00)
```

首次运行会把当前所有镜像的 digest 记进本地数据库当基线,之后哪个镜像在 registry 上发了新版,第二天早上九点手机就会"叮"一声。

## 最终形态

| 环节 | 方案 |
|---|---|
| 拉镜像 | 国内加速站优先,失败回落 docker.io 走 mihomo 代理 |
| 发现更新 | Diun 每天 09:00 扫描,推送 Synology Chat |
| 执行更新 | 人工决定:`docker compose pull && up -d` |
| 禁区 | PT 下载器版本钉死,永不自动升级 |
| 清理 | `image prune` + `builder prune` 随手跑,`volume prune` 看清楚再跑 |

整套东西没有引入任何面板类服务,增量只有一个 20MB 的 Diun 容器。镜像更不更新从"想起来才查"变成"有更新自动找上门",这事儿算是闭环了。
