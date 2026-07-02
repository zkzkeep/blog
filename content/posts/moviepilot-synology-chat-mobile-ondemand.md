---
title: "手机上发个片名，回家就能看：Synology Chat + MoviePilot 点播一条龙(附一坨历史遗留问题排障)"
date: 2026-07-02T18:30:00+08:00
draft: false
tags: ["MoviePilot", "Synology Chat", "群晖", "Xpenology", "Docker", "自动化观影", "mihomo", "网络排障"]
categories: ["NAS", "折腾记录"]
description: "想在微信里发个「卧虎藏龙」就自动下载入库?企业微信那套 frp+nginx+VPS 我再也不想碰了。本文用 Synology Chat + MoviePilot v2 实现零公网依赖的手机点播,顺手修完了换路由器和 VPS 消失留下的一堆烂账:死代理、旧网段 IP、隐藏机器人、发错会话、TMDB 被墙。"
typora-root-url: /Users/leesdove/Documents/blog/static
---

## 需求与选型

需求很简单:手机上发一个片名,NAS 上的 MoviePilot 自动搜索、返回列表、我回个数字,它下载、整理、入库,回家打开 Emby 就能看。

最直觉的载体是微信,但微信个人号没有机器人接口,只能走企业微信。这条路我几年前走通过:企业微信要求回调地址公网可达且域名备案、API 调用要可信 IP,于是 VPS + frps + nginx 一层层叠上去——后来 VPS 一挂,整条链路当场去世,重装 VPS 后我就再也没修过它。

这次换思路,选了 **Synology Chat**:

- Chat 套件和 MoviePilot 跑在同一台 NAS 上,回调走本机地址,**不需要公网 IP、域名、备案、frp、nginx 中的任何一样**
- 在外访问用现成的 Tailscale,手机 App 服务器地址填 Tailscale IP 即可
- 交互体验和企业微信里一模一样:发片名 → 列表 → 回数字 → 下载

唯一代价是手机多装一个 App。换来的是这套东西没有任何会过期、会跑路的外部依赖。

## 安装 Synology Chat(国区套件中心没有)

套件中心搜不到 Chat 不是你的问题:**2021 年 3 月起 Chat 相关套件从中国大陆区域下架了**,国际区一直正常维护。解决办法是去群晖官方归档站手动下载 spk:

```
https://archive.synology.com/download/Package/Chat/
```

注意套件名就叫 `Chat`,不叫 Chat Server。选最新版本目录,x86 机型下载 `Chat-x86_64-*.spk`,套件中心「手动安装」。

它有两个前置依赖,一般套件中心直接能装:

- **Node.js v18**(注意:就算别的套件装了 v20/v22 也不算数,DSM 里不同大版本 Node 是独立套件,可共存)
- **Synology Application Service** ≥ 1.7.6-20625

手机 App 国区商店同样没有,iOS 需要外区 Apple ID,安卓去官网下 APK。登录时服务器地址填 NAS 的 Tailscale IP(端口 5000/5001)。

## 对接 MoviePilot

三步:

1. Chat 网页 → 头像 → **整合 → 机器人** → 创建,记下**传入 URL** 和**令牌**
2. MoviePilot → 设定 → 通知 → 添加 **Synology Chat** 渠道,填入传入 URL(域名部分换成 NAS 局域网 IP)和令牌
3. 回到机器人设置,**传出 URL** 填:

```
http://<NAS局域网IP>:3000/api/v1/message/?token=<MP的API_TOKEN>
```

理论上到这里就通了。实际上我卡了整整一个下午——因为这台 NAS 攒了两年的历史遗留问题集中爆发了。下面是排障实录,每一条都够别人踩一次。

## 坑一:站点认证「无法连接站点」——凶手是死代理

MP 长期没用,打开发现用户认证掉了,换了好几个认证站点都提示「认证失败:无法连接站点」。

关键判断:**报错是「无法连接」而不是「密钥错误」,且换任何站点都一样——这是网络层问题,别浪费时间换站点重试**。

查容器环境变量,找到凶手:

```bash
docker exec moviepilot-v2 env | grep -i proxy
# PROXY_HOST=socks5h://192.168.50.9:20170
```

`192.168.50.x` 是我家**上一个路由器的网段**,这台机器现在是 `192.168.1.x`。这个代理地址指向一个不存在的世界,MP 所有出站请求全在上面撞死。compose 里删掉全部代理变量重建容器,认证秒恢复——MP 存着我当年的 UID 和密钥,网一通它自己就重新认证过了。

顺带发现 DSM 控制面板的系统代理里也残留着同一套死地址,一并清理。

## 坑二:仪表盘全空白——配置里的 IP 还活在上个网段

认证恢复后进 MP,存储空间 0.00B、实时速率 0、媒体统计空白。查配置:

```bash
# MP 的设置都在 /config/user.db 的 systemconfig 表里
docker exec moviepilot-v2 python -c "
import sqlite3
con = sqlite3.connect('/config/user.db')
for k,v in con.execute('SELECT key,value FROM systemconfig'):
    if v and '192.168.50' in str(v): print(k)
"
# Downloaders
# MediaServers
```

下载器(qBittorrent)和媒体服务器(Emby/Plex)的 host 全是旧网段 IP。MP 连不上它们,仪表盘自然什么都画不出来。通过 MP 的 API 批量替换成新 IP 即可(`POST /api/v1/system/setting/{key}`)。

**教训:换路由器网段是大动作,NAS 上所有写死 IP 的配置都会变成哑弹。修完记得去路由器给 NAS 做 DHCP 静态绑定。**

## 坑三:机器人只发不收——「隐藏机器人」这个勾不能打

链路配好后测试:MP 能主动推消息到 Chat(通知方向 ✅),但我发给机器人的消息石沉大海,MP 日志里连一条 POST 都没有。

翻 Chat 的 PostgreSQL(数据库叫 `synochat`,`chatbots` 表)发现:

```json
"chatbot_props": {"hide_from_user": true, ...}
```

创建机器人时勾了「隐藏机器人」。**隐藏状态的机器人是单向的:能推送,但用户发给它的消息不会触发传出 URL**。取消勾选保存。

## 坑四:发对机器人,别发给"尸体"

取消隐藏后还是不通。继续翻数据库,`posts` 表里真相大白:

- 我发的片名全进了一个**没有任何成员的频道**——那是当年旧工具用「传入 Webhook」建的通知会话,长得和机器人一模一样,但它只能收通知,发什么都没人理
- 真正的机器人会话是另一个(成员 = 我 + 机器人)

Chat 会话列表里躺着两个「MoviePilot」,我一直在对着尸体说话。切到正确的会话,消息瞬间进来了:

```
synologychat - 收到来自 MP交互 的SynologyChat消息:userid=4, text=卧虎藏龙
media.py - 开始搜索媒体信息:卧虎藏龙
```

**建议:对接成功后立刻把旧的 webhook 会话删掉,不然一定会发错。**

## 坑五:TMDB 被墙——mihomo 本机代理收尾

消息通了,但搜索卡 80 秒后回「没有找到对应的媒体信息」——TMDB API 国内不通,而 MP 搜索第一步就是查 TMDB。

以前靠 VPS 代理,VPS 挂了就全崩。这次改成**代理跑在 NAS 本机**,而且只让"锦上添花"的流量(TMDB/GitHub)走代理,认证、站点、下载全部直连——就算代理再挂,核心功能不受影响:

```yaml
# /volume5/docker/compose/mihomo/docker-compose.yml
services:
  mihomo:
    image: metacubex/mihomo:latest
    container_name: mihomo
    restart: always
    ports:
      - "7890:7890"
    volumes:
      - ./config:/root/.config/mihomo
```

`config/config.yaml` 里写自己的节点(我用的是自己 VPS 上的 vless reality,单节点 `MATCH` 全代理),然后 MP 的 compose 里只加一行:

```yaml
- 'PROXY_HOST=http://<NAS局域网IP>:7890'
```

注意**不要**再配 `HTTP_PROXY/HTTPS_PROXY` 全局环境变量——MP 会自己决定哪些请求走 `PROXY_HOST`,全局代理反而会把本机回调也拖下水(坑一的死法之一)。

另外如果暂时没有代理,MP 设定里把识别源/搜索源(`RECOGNIZE_SOURCE`/`SEARCH_SOURCE`)切成 `douban` 也能凑合用,豆瓣国内直连。

## 最终效果

```
18:17:25  收到消息:卧虎藏龙
18:17:26  TMDB 搜索到 5 条结果(0.7 秒),列表已推送
18:17:37  收到回复:5 → 查 Emby/Plex 均无此片 → 开始找资源下载
```

手机发片名,秒回列表,回个数字,下载入库全自动。零公网暴露、零备案、零外部依赖——当年企业微信那套脚手架,一根都不需要了。

## 总结

1. 报错「无法连接」且全站点一样 → 查网络/代理,别折腾密钥
2. 换路由器网段后,盘点所有写死 IP 的配置(容器代理、下载器、媒体服务器、DSM 系统代理)
3. Chat 机器人「隐藏」= 只发不收
4. 会话列表里同名的旧 webhook 会话是尸体,删
5. 代理这种基础设施尽量放本机,并且只覆盖非核心流量,别让它成为单点
