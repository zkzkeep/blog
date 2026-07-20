---
title: "给自托管 MoviePilot 配企业微信：从『收不到通知』到『发个片名就下片』"
date: 2026-07-20T22:30:00+08:00
draft: false
tags: ["MoviePilot", "企业微信", "飞牛OS", "NAS", "Docker", "网络排障", "mihomo"]
categories: ["NAS", "折腾记录"]
description: "MoviePilot 从群晖搬到飞牛后通知全哑了。修的过程一路踩坑：通知渠道其实压根没配、企业微信的『可信IP』撞上家宽动态IP、直接写数据库被 MP 覆盖、双向交互要反查回调 token、还有那个『改一次 compose 就崩』的 venv 权限坑。最后打通到——微信里发『福贵』两个字，MP 就搜好片单让我选着下。"
typora-root-url: /Users/leesdove/Documents/blog/static
---

从群晖转飞牛，MoviePilot 的容器搬过来了，通知却彻底哑了。以前用群晖 Chat 收推送，现在那条路没了。想着"随便换个渠道就行"，结果一路修下来踩了五六个坑，索性记下来。

目标有两层：**单向通知**（下载完/入库/辅种成功自动推给我）和**双向交互**（微信里发个片名，MP 搜出来让我选着下）。

## 坑一：通知渠道其实压根没配

先别急着怀疑网络。我查了下 MP 的数据库，`Notifications` 这个 systemconfig 键——**空的**。

```
没有 Notifications 配置 —— 即从未配置任何通知渠道
```

MP 的通知是两段式：**事件开关**（什么时候发）和**通知渠道**（往哪发）。事件开关我一直开着，但从来没配过渠道，消息自然无处可送。群晖时代用的 SynologyChat 渠道，搬到飞牛后那个渠道类型还在配置里挂着，但对应的服务没了。

方向定了：配一个新渠道。国内自托管，企业微信最顺手——不用代理、直接在微信里收。

## 坑二：企业微信的『可信IP』撞上家宽动态IP

企业微信自建应用的三件套很好拿：企业ID、AgentID、Secret（后台点几下）。拿 `gettoken` 接口一验，`errcode: 0`，凭证没问题。

但真发消息，报错来了：

```
errcode: 60020 | not allow to access from your ip, from ip: 171.114.36.76
```

**60020 = 调用方IP不在应用的『企业可信IP』白名单里**。而 `171.114.36.76` 是我家宽带的公网IP。

问题是：**家宽IP是动态的**。今天加进白名单，过几天 PPPoE 重播IP变了，通知又哑。这不是长久之计。

### 解法：让通知走固定IP出去

我 NAS 上跑着 mihomo，出口是某个 VPS 的**固定IP**。思路：把企业微信 API 的流量单独路由到这个固定出口，白名单里填这个永不变的IP。

两步：

**mihomo 加一条规则**（放在 `GEOIP,CN,DIRECT` 前面，否则企业微信是国内域名会被直连规则截胡）：

```yaml
rules:
  - IP-CIDR,192.168.0.0/16,DIRECT,no-resolve
  - IP-CIDR,100.64.0.0/10,DIRECT,no-resolve
  - DOMAIN-SUFFIX,qyapi.weixin.qq.com,PROXY   # 新增：企业微信API走代理固定IP
  - GEOIP,CN,DIRECT
  - MATCH,PROXY
```

**让 MP 容器走这个代理**。MoviePilot 用 httpx 发请求，httpx 默认 `trust_env=True`，认 `HTTP_PROXY`/`HTTPS_PROXY` 环境变量。给容器加上，再用 `NO_PROXY` 把本地和局域网排除掉，别把内部通信也代理了：

```yaml
environment:
  - HTTP_PROXY=http://<mihomo宿主IP>:7890
  - HTTPS_PROXY=http://<mihomo宿主IP>:7890
  - NO_PROXY=localhost,127.0.0.1,::1,<NAS内网IP>,transmission,qbittorrent,prowlarr,emby
```

改完实测，`message/send` 返回 `errcode: 0, ok`——出口变成了固定IP，白名单里填它，动态IP的问题一劳永逸。

## 坑三：直接写数据库，被 MP 覆盖了

我图省事，把企业微信渠道配置直接 `INSERT` 进了 MP 的 `Notifications` 系统配置表，重启。测试消息（我手搓 httpx 发的）能收到，以为成了。

结果用户在网页上一看——**通知渠道页面空的**。再查库：

```
无配置
```

**MP 启动时会用自己的配置模型重新序列化 systemconfig，我手动 INSERT 的那行不符合它的内部结构，被直接覆盖清掉了。** 之前"测试成功"是假象——那是我绕开 MP 直接调企业微信 API 发的，根本没走 MP 的通知系统。

正确做法是走 MP 自己的 API：

```
POST /api/v1/system/setting/Notifications
```

带上管理员 token，body 是符合 `NotificationConf` 结构的列表：

```python
notif = [{
    "name": "企业微信",
    "type": "wechat",
    "enabled": True,
    "config": {
        "WECHAT_CORPID": "...",
        "WECHAT_APP_SECRET": "...",
        "WECHAT_APP_ID": "...",   # 注意是 AgentID
        "WECHAT_PROXY": ""        # 留空默认官方API
    },
    # switchs 存的是通知类型的中文值，不在列表里的类型不推送
    "switchs": ["资源下载","整理入库","订阅","站点","媒体服务器","手动处理","插件","智能体","其它"]
}]
```

这回保存 `success: true`，回读确认在库里、页面也能看到了。**教训：MP 的配置一律走它的 API，别手戳数据库。**

## 坑四：双向交互，回调要带 MP 的 API token

单向通知通了，接下来是重头戏——**双向交互**。我想要的是：微信里发"福贵"，MP 搜出来回个列表，我回数字就下。

这需要企业微信能把我的消息**回调**给 MP。企业微信应用后台「接收消息 → 设置API接收」填三样：回调URL、Token、EncodingAESKey。后两个我本地随机生成（AESKey 必须正好 43 位），塞进 MP 渠道配置的 `WECHAT_TOKEN` / `WECHAT_ENCODING_AESKEY`。

回调URL的坑在于：MP 的消息接收端点 `POST /api/v1/message/` 挂着 `Depends(verify_apitoken)`——**需要 API 令牌**。翻了下 MP 配置，`API_TOKEN` 是启动时随机生成的。所以回调URL得带上它：

```
https://<你的MP域名>/api/v1/message/?token=<MP的API_TOKEN>
```

（MP 是单个企业微信渠道时，URL 里的 `source` 参数可以省略，它会自动用唯一那个 wechat 配置——省掉了中文渠道名塞进URL要转码的麻烦。）

拿假签名参数先探一下端点：

```
"微信验证失败"  HTTP:200
```

返回 200 且进到了验证逻辑（而不是 401），说明 token 认证过了、路由通了——真实企业微信发来带正确签名的请求时就能验证通过。

## 打通：微信里发『福贵』

用户在企业微信后台保存「接收消息」配置，那一刻企业微信向回调URL发验证请求，MP 解密 echostr 返回，验证通过。然后手机微信里对着 MoviePilot 应用发了俩字：**福贵**。

MP 日志里一条龙：

```
收到来自 企业微信 的微信消息：userid=..., text=福贵
搜索到 3 条相关媒体信息
发送消息：【福贵】共找到3条相关信息，请回复对应数字选择
```

秒回一个片单：1. 福贵（2005，余华《活着》改编，评分9.0）、2. 神厨小福贵、3. 贵人多旺事。回复数字就去搜资源、选种子、下载。

**发片名 → 搜TMDB → 回列表 → 选编号 → 搜资源 → 下载**，全程在微信里点，人在外面也能点播。

## 附赠坑五：改一次 compose，MP 就崩

有个贯穿始终的暗坑值得单说：**每次改 MoviePilot 的 compose（比如加代理环境变量），`docker compose up -d` 会重建容器**，而重建后后端起不来，网页 502、满屏 0.00 B。

根因是 MP 的 Python 虚拟环境 `/opt/venv` 里有一批包文件权限变成了 `000`（谁都不能读，`PermissionError: cloakbrowser/__init__.py`），MP 以非 root 用户跑就 import 崩溃。这个权限修复（`chmod -R a+rX /opt/venv`）是打在容器可写层里的，**容器一重建就没了**。

所以规矩记死：**凡是改 MP 的 compose 导致容器重建，之后必跑一次**

```bash
docker exec -u 0 moviepilot chmod -R a+rX /opt/venv
docker restart moviepilot
```

## 小结

- MP 通知是「事件开关 + 通知渠道」两段式，收不到先查渠道配了没；
- 企业微信 `60020` 是可信IP问题，家宽动态IP别硬刚，用 mihomo 把 `qyapi.weixin.qq.com` 单独路由到固定出口IP，白名单填那个；
- MP 配置一律走 `POST /api/v1/system/setting/{key}` 的官方 API，手戳数据库会被覆盖；
- 双向交互的回调URL要带 `?token=<API_TOKEN>`，单渠道可省 `source`；`WECHAT_ENCODING_AESKEY` 必须 43 位；
- MoviePilot 容器重建后记得修 `/opt/venv` 权限。

配到最后，"人在外地，微信发俩字就把片下上"的体验，值回所有折腾。
