---
title: "ChatGPT 总是「正在重新连接」：一次被 MagicDNS 转手投毒的排障"
date: 2026-07-25T23:35:00+08:00
draft: false
tags: ["Tailscale", "MagicDNS", "Shadowrocket", "DNS污染", "ChatGPT", "网络排障", "macOS"]
categories: ["折腾记录"]
description: "页面能打开，但流式响应总断、反复「正在重新连接」。查到最后发现是 Tailscale 的 MagicDNS 抢占了系统第一顺位 DNS，自己又没配上游，把查询转手交给了运营商 DNS。本文记录完整证据链，以及五条走不通的弯路。"
typora-root-url: /Users/leesdove/Documents/blog/static
---

> 本文所有 IP、UUID、tailnet 域名均已脱敏，思路和命令不受影响。

## 症状

ChatGPT 网页能打开、能登录，但只要开始对话就出问题：

- 回答流式输出到一半卡住
- 反复弹「正在重新连接」
- 「正在思考」转很久才出字

代理是通的——别的网站都正常。这种**半通不通**的状态最难查，因为它同时排除了「完全没代理」和「代理挂了」两种最简单的解释。

## 先说结论

系统的第一顺位 DNS 是 Tailscale 的 MagicDNS（`100.100.100.100`），而 **MagicDNS 自己没有配上游解析器**，于是把非 tailnet 域名的查询转手交给了运营商 DNS——那正是投毒最严重的地方。

关键的一行，出自 `tailscale dns status`：

```
Resolvers (in preference order):
  (no resolvers configured, system default will be used)
```

结果就是：

| 域名 | 解析到 | 归属 |
|---|---|---|
| `chatgpt.com` | 108.160.163.116 | **Dropbox** |
| `api.openai.com` | 128.242.240.221 | **Verizon** |
| `ab.chatgpt.com` | 162.125.32.12 | **Dropbox** |

而且 `chatgpt.com` 每查一次返回的假 IP 都不一样，前后测到过 Facebook、Dropbox、还有几个查不到归属的——**随机投毒的典型特征**。

`ab.chatgpt.com` 是 ChatGPT 的实时配置和流式通道之一。它被指到 Dropbox 的 IP，「正在重新连接」就是这么来的。

## 为什么是「半通不通」

因为机器上同时存在两套 DNS，而它们的干净程度完全相反：

```
$ scutil --dns | grep 'nameserver\[0\]'
  nameserver[0] : 100.100.100.100     ← Tailscale MagicDNS（被污染）
  nameserver[0] : 198.18.0.2          ← Shadowrocket TUN DNS（干净）
```

`198.18.0.2` 是代理软件自己的 DNS，它返回的是 fake-IP，域名交给远端节点解析，**完全不受投毒影响**。但它排在第二顺位，轮不到它。

于是走代理透明转发的请求解析正常，页面能开；而任何走系统 resolver 的路径——桌面 App、浏览器重建长连接——拿到假 IP，连不上就死循环重连。

再看一眼路由，问题就闭合了：

```
$ route -n get 100.100.100.100
  interface: utun5      ← Tailscale 自己的接口

$ route -n get 198.18.0.2
  interface: utun4      ← 代理软件的接口
```

**发往 MagicDNS 的查询走 utun5，从一开始就绕开了代理。**

## 五条走不通的路

这次绕了很多弯，失败的尝试比成功的方案更值得记：

### 1. 改代理软件的 `dns.conf` —— 那不是配置文件

Shadowrocket 的 group container 里有个 `dns.conf`，看起来就是 DNS 设置。改成 DoH 后重启，一看又变回去了：

```xml
<array>
  <string>100.100.100.100</string>
  <string>240e:xxxx::13</string>   ← 运营商 DNS
</array>
```

**它是运行时快照，不是配置源**。软件每次启动都抓一份当前系统 DNS 写进去，手改等于没改。

### 2. 后台加 global nameserver，但不开 Override

在 Tailscale 管理后台加了 Cloudflare / Google / Quad9 三个 global nameserver，`Override DNS servers` 开关没开。结果 `dns status` 里 `Resolvers` 依然是空——**关着开关时根本不下发**，加了等于没加。

### 3. Split DNS 指向明文 `1.1.1.1` —— 还是被抢答

给 `chatgpt.com` 和 `openai.com` 配了 Split DNS 指向 `1.1.1.1`，路由确实下发了，解析结果照旧是假 IP。

这里有个坑差点骗过我：我在终端 `dig @1.1.1.1` 测出来是**干净的**。但那是因为终端的查询经过了代理出去。**`tailscaled` 自己发的转发查询绕开代理、明文出境，照样被抢答。**

### 4. Split DNS 指向 `198.18.0.2` —— 比原来更糟

既然代理的 DNS 是干净的，那把 Split DNS 指过去？结果所有相关域名**直接解析超时**：

```
chatgpt.com  -> ;; connection timed out; no servers could be reached
```

原因同上：`tailscaled` 进不了代理的 `utun4`，那个地址对它根本不存在。**明文查询被污染，指向本机代理又够不着，两头堵。**

### 5. Split DNS 填 DoH URL —— 输入框不收

最干净的思路本该是让 `tailscaled` 走加密查询（DoH 加密，GFW 插不进手，实测 `https://doh.pub/dns-query` 直连 6/6 成功、延迟 0.36s）。但 Tailscale 管理后台的 custom nameserver **不接受 `https://` 开头的地址**，这条路在 Tailscale 侧走不通。

## 正解

既然 MagicDNS 这一层怎么都绕不过去，那就别让它管 DNS：

```bash
tailscale set --accept-dns=false
```

系统 DNS 第一顺位立刻退回代理软件的 `198.18.0.2`，所有域名解析全部由代理处理，零污染、零明文出境查询。**Tailscale 的隧道本身完全不受影响**——设备该 direct 还是 direct。

代价是 MagicDNS 短名（`nas`、`server` 这种不带点的主机名）失效。补回来很简单，写死到 hosts 即可：

```bash
sudo cp /etc/hosts /etc/hosts.bak-$(date +%Y%m%d) && sudo tee -a /etc/hosts >/dev/null <<'EOF'

# Tailscale 短名（accept-dns=false 后替代 MagicDNS）
100.x.x.x   nas
100.x.x.x   server
EOF
```

Tailscale 的设备 IP 是固定分配的，写死一次长期有效。改完 `ping nas` 和浏览器里的 `http://nas:8080` 都照常。

想退回去也只要一条命令：

```bash
tailscale set --accept-dns=true
```

## 两条假验证路径

这次又踩到「测试手段本身不成立」的坑，记下来提醒自己：

**其一，ping 代理目标会被 TUN 伪造应答。** 我 ping 一台美国 VPS，显示 **0.4ms**。TUN 模式下代理软件会对代理目标直接伪造 ICMP 回复，这个数字毫无意义。想量真实 RTT，得去服务端看：

```bash
ss -tin state established '( sport = :443 )' | grep -oE "rtt:[0-9.]+/[0-9.]+"
```

**其二，`curl --resolve` 在有代理环境变量时完全失效。** 我想做「指定 IP 对比」实验，发现三组结果一模一样，`remote_ip` 恒为 `127.0.0.1`——因为 shell 里有 `HTTP_PROXY=127.0.0.1:1082`，域名交给代理解析了，`--resolve` 根本没参与。要绕过得加 `--noproxy '*'`。

假数据从源头把推理带偏，比没有数据更危险。**下结论前先确认测试路径本身成立**，这个教训我已经吃了不止一次。

## 顺带一提：DNS 修好了，慢的问题还在

DNS 干净之后，「正在重新连接」彻底消失了。但「正在思考」偏慢的问题只解决了一部分——那是另一个变量。

在服务端量了一下真实的跨境 RTT：**190 到 310ms，抖动（mdev）16 到 124ms**。而同一台 VPS 到 ChatGPT 只要 **0.03s**。也就是说端到端 1.75s 的延迟里，几乎全部消耗在跨境这一段，服务器本身健康得很。

这类问题换协议是治不好的——光在中美之间跑一个来回就要 150ms 左右。要么换线路（日本 / 香港节点能到 50 至 80ms），要么用 Hysteria2 这类抗丢包协议缓解抖动带来的卡顿。**但延迟数字本身，是物理距离决定的。**

## 排查顺序小结

遇到「代理通着但某个服务反复重连」，建议按这个顺序查：

1. `dig +short <域名> A`，把结果拿去查归属——**解析到完全不相干的厂商就是投毒**
2. `scutil --dns | grep nameserver` 看系统 DNS 的**真实优先级**，别假设你以为的那个在生效
3. `route -n get <DNS的IP>` 看查询**从哪个接口出去**，是否绕过了代理
4. `tailscale dns status` 确认 MagicDNS **有没有配上游**（这次的元凶就藏在这行）

注意第 1 步不是所有「不一致」都算污染——Cloudflare 的 anycast 本来就会按解析位置返回不同 IP，`104.18.x` 和 `172.64.x` 都是它自家的段。**要看归属厂商对不对，而不是 IP 一不一样。**
