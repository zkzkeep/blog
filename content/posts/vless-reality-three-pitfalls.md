---
date: 2026-07-25T01:34:21+08:00
draft: false
title: 'VLESS + Reality 节点连不上？我踩的三个坑与完整排查思路'
tags:
  - Xray
  - Reality
  - 3x-ui
  - 网络
  - 技术
---

买了台 VPS，装上 3x-ui 面板，建了个 VLESS + Reality 节点，导入客户端——**连不上**。

这大概是所有自建代理的人都会遇到的场景。麻烦的地方在于：Reality 出问题时**往往一声不吭**，客户端就是转圈、超时，或者「连上了但打不开网页」，日志里也常常什么都看不到。到底是节点参数错了、面板配错了、还是核心有 bug？

这篇文章记录我把一个「怎么都连不上」的 Reality 节点修好的完整过程。最后定位到**三个独立的坑叠在一起**，任何一个都能让节点报废。比起结论，我更想分享的是**中间那套二分定位的排查方法**——它能让你不靠猜，一步步把问题锁死。

> 文中所有 IP、UUID、密钥均为占位符，请替换成你自己的。

## 一、现象

- 面板能打开，节点看起来建好了；
- 客户端导入节点，参数肉眼看都对；
- 开启代理后：**能「连上」（延迟测试有数值），但网页打不开**，浏览器报 `ERR_TUNNEL_CONNECTION_FAILED`。

「能连上但打不开」是最迷惑人的现象——它让你以为握手成功了，其实很可能根本没成。

## 二、排查的核心思路：不要猜，做二分

Reality 链路从客户端到目标网站，中间有一长串环节：

```text
客户端参数 → TCP 到服务器 → Reality 握手 → VLESS 鉴权 → 服务端出网 → 目标网站
```

排障的关键，是**逐段验证，把「好的部分」和「坏的部分」一刀切开**。我用的判据工具很简单：

在任意一台机器上跑一个 xray 客户端（`brew install xray` 或官方二进制都行），配好 socks 入站指向节点，然后：

```bash
curl --socks5-hostname 127.0.0.1:10808 https://api.ipify.org
```

- 返回 **服务器的 IP** → 这一段链路完全通；
- 返回 **空** → 卡在 Reality/鉴权，去看服务端 debug 日志；
- 返回 **本机 IP** → 根本没走代理。

用官方 xray 命令行客户端、而不是直接用 GUI 客户端（Shadowrocket 等）来测，是因为**命令行客户端参数透明、日志详细、可控**，能把「参数问题」和「GUI 客户端自身问题」分开。这一点后面会救命。

服务端这边，把 Xray 的 `loglevel` 调成 `debug`，重点看这行：

```text
transport/internet/tcp: REALITY: processed invalid connection from x.x.x.x: handshake did not complete successfully
```

只要出现它，就说明 **Reality 握手失败**——问题在握手层，跟「网页打不开」这种表象无关。

## 三、三个坑

### 坑 1：dest / SNI 选了 `www.microsoft.com`

**现象**：客户端连上返回空，服务端 debug 反复刷 `handshake did not complete successfully`。

我做了个关键的对照实验，一刀切开「是 Reality 的问题，还是底层 TLS 的问题」：

- 用**普通 TLS（自签证书）的 VLESS** 做回环测试 → **通**；
- 换回 **Reality** → **挂**。

结论很清楚：VLESS、代理链路、服务端出网全都没问题，**问题就死在 Reality 这个机制本身**。

Reality 的原理，是服务端要「借用」一个真实大站（`dest`）的 TLS 握手来伪装。这个目标站**必须 TLS 1.3、握手行为稳定、且能被干净地镜像**。而 `www.microsoft.com` 走 CDN、握手行为多变，并不适合做 Reality 目标——尽管它平时 `curl` 得通。

**修复**：把 `dest` 和 `serverNames` 换成公认可靠的目标：

```text
dest:        www.apple.com:443
serverNames: ["www.apple.com"]
```

换完，Reality 回环立刻通。（`dl.google.com`、`www.icloud.com`、`addons.mozilla.org` 等也都是常用的好目标。）

> **教训**：Reality 的 dest 不是随便填一个能打开的大站就行。优先选握手稳定、非杂牌 CDN 的站点。

### 坑 2：面板生成的配置里，用户凭空消失了（`clients: null`）

修好 dest 后，节点还是不通。我去看服务端**实际运行**的 `config.json`，发现 inbound 里：

```json
"settings": { "clients": null }
```

数据库里明明有这个用户，但面板生成给 Xray 的运行配置里，`clients` 是 `null`——**等于服务端没有任何合法用户**，谁来都鉴权失败。

我一度以为是缺 `client_traffics` 记录、字段不全，补了半天都没用。直到通过面板 API 手动添加用户时，报错一句话点破真相：

```text
json: cannot unmarshal string into Go struct field Client.tgId of type int64
```

**根因**：这个面板/核心构建里，client 的 `tgId` 字段是 **int64**。而当初这个节点是**用脚本直接把数据往数据库里塞的**，`tgId` 写成了空字符串 `""`。面板在生成运行配置时解析 client 失败，索性把整个 `clients` 丢成了 `null`。

**修复**：不要手工往数据库塞 inbound，**走面板的 API 正规添加**，`tgId` 传整数：

```json
{ "id": "<uuid>", "flow": "xtls-rprx-vision", "email": "reality1", "tgId": 0 }
```

添加后重启面板服务，让它重新生成 `config.json`，这时 `clients` 里就有用户了。

> **教训**：能用面板 / 官方 API 就别手改数据库。不同构建对字段类型（尤其 `tgId` 这种）的要求可能不一样，手动灌数据极易埋下「解析失败 → 静默丢弃」的雷。

### 坑 3：内置的是超前 dev 版核心，跟 GUI 客户端不兼容

前两个坑修完，我用官方 xray 命令行客户端测——**完美连通，Google、YouTube 全过**。

但用户的 **Shadowrocket 还是打不开网页**，报 `ERR_TUNNEL_CONNECTION_FAILED`。我逐项核对了 Shadowrocket 里的参数：SNI、公钥、Short ID、指纹、流控——**全对**。甚至怀疑是 ALPN 设了 `h2,http/1.1`，专门复现测试，也照样通。

同样的节点、同样的参数，**官方命令行客户端能连，Shadowrocket 就是不行**。差异只剩一个：

> 服务端跑的 Xray 是个**版本号比官方最新稳定版还高的 dev 构建**。

它跟官方 xray 客户端能握手，但跟 Shadowrocket 的 Reality 实现存在**兼容性问题**。

**修复**：把服务端 Xray 核心换成**官方稳定版**（面板、配置、密钥都不动，只换二进制，可回滚）：

```bash
# 下载官方稳定版
curl -sL -o xray.zip https://github.com/XTLS/Xray-core/releases/download/vX.Y.Z/Xray-linux-64.zip
unzip xray.zip xray geoip.dat geosite.dat

BIN=/usr/local/x-ui/bin/xray-linux-amd64
cp -a "$BIN" "$BIN.bak"          # 备份，方便回滚
systemctl stop x-ui
cp -f xray "$BIN" && chmod +x "$BIN"
cp -f geoip.dat geosite.dat /usr/local/x-ui/bin/
systemctl start x-ui
```

换完，Shadowrocket 立刻正常。

> **教训**：如果你的面板一键脚本给你装了个版本号异常「新」的 dev 核心，别用。**优先跑官方稳定版**——dev 版的协议实现可能跟主流客户端不兼容，而且这种问题极难排查（因为部分客户端还是能连）。

## 四、一张排查 Checklist

下次 Reality 连不上，按这个顺序走，基本不会迷路：

1. **TCP 通不通**：`nc -vz <ip> 443`。不通先查防火墙 / 端口。
2. **是不是 Reality 层的问题**：拿命令行 xray 客户端 `curl --socks5-hostname` 测；服务端开 debug 看有没有 `handshake did not complete`。
3. **换个 dest 试**：`www.apple.com` / `dl.google.com`。dest 选错是最高频的坑。
4. **服务端运行配置里真有用户吗**：`grep <uuid> config.json`，确认 `clients` 不是 `null`。
5. **公私钥是不是一对**：`xray x25519 -i <privateKey>` 反推公钥，跟客户端填的 `publicKey` 对一下。
6. **核心版本**：`xray version`。是不是奇怪的 dev 版？换官方稳定版。
7. **客户端 vs 服务端隔离**：命令行客户端能连、GUI 客户端不能 → 问题在 GUI 客户端或核心兼容性，别再折腾服务端参数。

## 五、写在最后

这次三个坑很典型地说明了一件事：**「节点连不上」从来不是单一原因**，而参数肉眼看全对、却依然不通，才是最耗时的情况。

真正省时间的不是经验，而是**方法**——每一步都用一个能给出明确「通 / 不通」的实验，把链路一段段切开。当你能确定「普通 TLS 通、只有 Reality 挂」「命令行客户端通、只有 Shadowrocket 挂」时，问题的范围就已经小到可以直接下手了。

祝你的节点一次连通。
