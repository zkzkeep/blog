---
title: "让 Shadowrocket 和 Tailscale 在 Mac 上和平共处：一次路由冲突的完整排障记录"
date: 2026-07-02T11:15:00+08:00
draft: false
tags: ["Tailscale", "Shadowrocket", "macOS", "路由", "群晖", "Xpenology", "网络排障"]
categories: ["NAS", "折腾记录"]
description: "Mac 上同时开 Shadowrocket 和 Tailscale 总有一个连不上？本文记录一次完整排障：从路由表被抢、作用域路由陷阱，到系统代理拦截浏览器,最终用「/32 主机路由 + 自愈守护 + MagicDNS 短名」三件套彻底解决,附换电脑/重装系统的一键恢复脚本。"
typora-root-url: /Users/leesdove/Documents/blog/static
---

## 背景

我的场景很典型：

- Mac 上开着 **Shadowrocket**（TUN 模式）用于日常代理；
- 同时需要 **Tailscale** 连回家里的黑群晖 NAS（SA6400，Tailscale IP `100.127.178.15`，MagicDNS 名 `sa6400`）。

症状也很典型：**两个同时开,总有一个不干活**。Shadowrocket 开着的时候，`ping 100.127.178.15` 全部超时，DSM 网页打不开；关掉 Shadowrocket 就正常。

网上常见的答案是「在代理软件里把 `100.64.0.0/10` 加一条 DIRECT 分流规则」。**先说结论：这个答案在 Mac 上的 Shadowrocket 是错的**，而且真正的问题有两层。下面是完整的排障过程。

## 排障过程

### 第一坑：DIRECT 规则反而帮倒忙

按「标准答案」在 Shadowrocket 里加了规则：

```
IP-CIDR, 100.64.0.0/10, DIRECT (不解析域名)
```

结果 ping 出现了诡异的输出：

```
92 bytes from 10.192.0.10: Time to live exceeded
 ... Src 10.100.174.44  Dst 100.127.178.15
```

注意源地址 `10.100.174.44` —— 这不是 Tailscale 的地址，是**物理网卡 en0 的局域网地址**。包被甩给了物理网关，在运营商/校园网里绕圈直到 TTL 耗尽。

原因：**Shadowrocket 的 DIRECT 意思是「从物理网卡直连」，它并不知道也不关心 Tailscale 的存在**。而且这条规则会让 Shadowrocket 往系统路由表里写一条：

```
100.64/10 → 10.100.174.183 (en0 网关)
```

这条路由直接把 Tailscale 的路由压死了。

### 第二坑：Tailscale 的路由是「作用域路由」，打不赢

删掉 DIRECT 规则后查路由表（`netstat -rn -f inet`）：

```
100.64/10   10.100.174.183   UGSc   en0      ← Shadowrocket 的排除路由（全局生效）
100.64/10   link#44          UCSI   utun16   ← Tailscale 的路由（注意 I 标志）
```

关键在 Tailscale 那条的 **`I` 标志（interface-scoped）**：作用域路由只对显式绑定了该网卡的程序生效，**不参与全局选路**。普通程序（浏览器、ping）的流量永远被 en0 那条抢走。

而 en0 那条是 **Shadowrocket 每次连接时自动添加的「排除路由」**（它默认把 CGNAT 网段 `100.64/10` 排除出自己的隧道、甩给物理网关）——所以删规则、调整两个 App 的连接顺序都没用，它每次都会回来。

验证 Tailscale 隧道本身没问题：

```bash
ping -b utun16 100.127.178.15   # 强制从 Tailscale 网卡发包 → 通！
```

### 破局：/32 主机路由，精确度碾压

路由选路规则：**前缀越长（越精确）优先级越高**。`/32` 主机路由必然赢过那条 `/10`：

```bash
sudo route -n add -host 100.127.178.15 -interface utun16
```

加完 `route get 100.127.178.15` 显示走 `utun16`，ping 立刻通了。

> 小坑：如果 `route add` 报 `File exists`，是内核克隆的邻居表项挡路，先 `sudo route -n delete -host <IP>` 再加。

### 第三坑：ping 通了，浏览器还是打不开

`curl --noproxy '*' http://100.127.178.15:5000` 返回 200，但浏览器死活进不去。查系统代理：

```bash
scutil --proxy
```

真相：**Shadowrocket 还设了系统 HTTP 代理 `127.0.0.1:1082`**，浏览器的所有请求都先交给它。它的例外列表（ExceptionsList）里有 `10.0.0.0/8`、`192.168.0.0/16`、`172.16.0.0/12`……**唯独没有 `100.64.0.0/10`**。

于是浏览器用 IP 访问 NAS 时：请求 → 本地代理 → 甩给远端代理服务器 → 远端到不了你家 NAS → 503。用 `curl -x http://127.0.0.1:1082` 模拟浏览器复现了 503，而且 0.026 秒就失败——加回 DIRECT 规则也没用，因为 Shadowrocket 直连时绑定物理网卡，出门就撞墙。

### 最优雅的一步：MagicDNS 短名绕过代理

`scutil --proxy` 的输出里有一行宝藏：

```
ExcludeSimpleHostnames : 1
```

**不带点的「简单主机名」自动绕过系统代理。** 而 Tailscale 的 MagicDNS 正好在系统里配了搜索域（`tailxxxx.ts.net`），短名 `sa6400` 能直接解析成 `100.127.178.15`。

所以浏览器访问：

```
http://sa6400:5000        ← 用这个 ✅
http://100.127.178.15:5000 ← 不要用 IP ❌（会被交给代理）
```

链路变成：短名绕过代理 → MagicDNS 解析 → 命中 /32 主机路由 → 进 Tailscale 隧道 → 到家。

### 最后一块拼图：路由自愈守护

手工加的 `/32` 路由在 **Mac 重启、Tailscale/Shadowrocket 重连**后会丢（当天就丢过一次），而且 Tailscale 的 utun 编号还会变。解法是一个 LaunchDaemon：

- 开机自启 + 每 30 秒 + 网络配置变化时触发；
- 自动找到「持有 100.x 地址的 utun 网卡」（不依赖固定编号）；
- 发现去 NAS 的路由不指向它就自动纠正。

实测 `sudo route delete` 删掉路由后，**15 秒内自动恢复**。

## 最终方案总结

| 层 | 问题 | 解法 |
|---|---|---|
| 路由层 | Shadowrocket 排除路由压死 Tailscale | `/32` 主机路由 + LaunchDaemon 自愈 |
| 代理层 | 系统代理拦截浏览器、例外表缺 CGNAT 段 | 用 MagicDNS 短名 `http://sa6400:5000` 访问 |
| 翻墙 | — | 完全不受影响，规则原样 |

## 一键安装脚本（换电脑 / 重装系统用）

把下面保存为 `install-nas-route.sh`（我在 NAS 和移动硬盘里各存了一份）：

```bash
#!/bin/sh
# =============================================================
# 一键安装:Shadowrocket + Tailscale 共存连 NAS 的路由自愈守护
# 用法:在新 Mac 上先装好并登录 Tailscale,然后执行:
#   sudo sh install-nas-route.sh
# 之后浏览器用 http://sa6400:5000 访问 NAS(不要用 IP)
# 卸载:sudo sh install-nas-route.sh uninstall
# =============================================================

NAS_IP="100.127.178.15"   # NAS 的 Tailscale IP,若变化改这里
LABEL="com.leesdove.tailscale-nas-route"
SCRIPT="/usr/local/bin/tailscale-nas-route.sh"
PLIST="/Library/LaunchDaemons/${LABEL}.plist"

[ "$(id -u)" -ne 0 ] && { echo "请用 sudo 运行:sudo sh $0"; exit 1; }

if [ "$1" = "uninstall" ]; then
    launchctl bootout "system/${LABEL}" 2>/dev/null
    rm -f "$PLIST" "$SCRIPT"
    route -n delete -host "$NAS_IP" 2>/dev/null
    echo "✅ 已卸载"
    exit 0
fi

# ---------- 写入修路脚本 ----------
mkdir -p /usr/local/bin
cat > "$SCRIPT" <<EOF
#!/bin/sh
NAS_IP="$NAS_IP"
TS_IF=\$(ifconfig 2>/dev/null | awk '/^utun[0-9]+:/{iface=\$1; sub(/:\$/,"",iface)} /inet 100\./{print iface; exit}')
[ -z "\$TS_IF" ] && exit 0
CUR_IF=\$(route -n get "\$NAS_IP" 2>/dev/null | awk '/interface:/{print \$2}')
[ "\$CUR_IF" = "\$TS_IF" ] && exit 0
route -n delete -host "\$NAS_IP" >/dev/null 2>&1
route -n add -host "\$NAS_IP" -interface "\$TS_IF" >/dev/null 2>&1
logger -t tailscale-nas-route "已将 \$NAS_IP 路由修正到 \$TS_IF (原: \${CUR_IF:-无})"
EOF
chmod 755 "$SCRIPT"; chown root:wheel "$SCRIPT"

# ---------- 写入 LaunchDaemon ----------
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>Label</key>
	<string>${LABEL}</string>
	<key>ProgramArguments</key>
	<array>
		<string>${SCRIPT}</string>
	</array>
	<key>RunAtLoad</key>
	<true/>
	<key>StartInterval</key>
	<integer>30</integer>
	<key>WatchPaths</key>
	<array>
		<string>/Library/Preferences/SystemConfiguration</string>
	</array>
</dict>
</plist>
EOF
chown root:wheel "$PLIST"; chmod 644 "$PLIST"

# ---------- 加载(先卸旧防重复) ----------
launchctl bootout "system/${LABEL}" 2>/dev/null
launchctl bootstrap system "$PLIST" || { echo "❌ LaunchDaemon 加载失败"; exit 1; }
"$SCRIPT"   # 立即执行一次

echo "✅ 安装完成。浏览器请用 http://sa6400:5000 访问 NAS"
```

## 换电脑 / 重装系统的完整流程

以后拿到新 Mac（或重装系统后），恢复整套环境只需四步：

1. **装 Tailscale**（App Store 或官网），登录同一账号，确认菜单栏图标变绿、能看到 NAS 设备在线；
2. **装 Shadowrocket**，导入原来的配置（节点 + 规则原样即可，不需要为 Tailscale 加任何特殊规则）；
3. **跑一次安装脚本**（从 NAS 的 File Station 或移动硬盘取回）：

   ```bash
   sudo sh install-nas-route.sh
   ```

4. **浏览器书签存 `http://sa6400:5000`**，以后固定用短名访问。

几个关键点：

- **新 Mac 的 Tailscale IP 变了没关系**——脚本动态探测 utun 网卡，不依赖本机 IP；
- **NAS 的 IP 不会变**（只要设备不从 Tailscale 账号里删除重加）；如果真变了，改脚本第一行 `NAS_IP` 重跑即可；
- 旧电脑转手前记得清理：`sudo sh install-nas-route.sh uninstall`，再退出 Tailscale 账号。

## 排障速查

哪天又连不上，按这个顺序查：

```bash
# 1. 路由指向对不对?(应该是 Tailscale 的 utunX)
route -n get 100.127.178.15 | grep interface

# 2. Tailscale 活着吗?
/Applications/Tailscale.app/Contents/MacOS/Tailscale status

# 3. 守护进程干活了吗?
log show --last 10m --predicate 'eventMessage CONTAINS "tailscale-nas-route"'

# 4. 网络层通、浏览器不通?→ 检查是不是用 IP 访问了,换短名
curl -s -o /dev/null -w "%{http_code}\n" --noproxy '*' http://100.127.178.15:5000
```

## 写在最后

这次折腾最大的教训：**「加一条 DIRECT 分流规则」这种网上抄来的答案，在 TUN + 系统代理双拦截的架构下是不够的**。问题实际横跨三层——内核路由表、代理软件的排除路由、系统 HTTP 代理的例外列表——每一层都可能把你拦下，必须逐层验证（`route get` → `ping -b` → `scutil --proxy` → `curl -x`），才能找到真正的断点。

好在 macOS 留了两个后门：**最长前缀匹配**（/32 干翻 /10）和 **ExcludeSimpleHostnames**（短名绕过代理）。把它们拼起来，再用 LaunchDaemon 兜底,就是一套不需要日常维护的共存方案。
