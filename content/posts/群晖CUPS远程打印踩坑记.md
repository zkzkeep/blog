---
title: '群晖CUPS远程打印踩坑记'
date: 2026-10-21T20:30:00+08:00
draft: false
lastmod: 2026-10-27T15:50:00+08:00
tags: ["群晖", "CUPS", "Tailscale", "打印机", "Shadowrocket", "排障"]
categories: ["折腾记录"]
description: "新到一台兄弟墨仓机，人不在家，想用群晖当打印服务器，在外面通过 Tailscale 打印，顺便每周自动打一张防堵头。一路踩了五个坑：群晖普通用户没有 ping 权限、Tailscale 用户空间模式撞上 CUPS 的本机检查、传文件被 401、小火箭把 Tailscale 流量拐到了美国、通用 PostScript 驱动把 PDF 撑大十几倍。"
typora-root-url: /Users/leesdove/Documents/blog/static
---

家里新到了一台兄弟 DCP-T436W 墨仓机，主要给孩子打作业。装好那天我人不在家，于是给自己定了两个目标：

1. **人在外面也能打印**：老师发来的作业，在外面就能直接打到家里。
2. **每周自动打一张**：墨仓机最怕长期不用堵喷头，让它每周自己出一张纸，冲一冲喷头。

思路很简单：群晖 24 小时开着，让它当打印服务器，外面通过 Tailscale 连回家。实际做下来踩了五个坑，每个坑的原因都不在我一开始以为的地方。记录一下。

## 最终的样子

![](/images/群晖CUPS远程打印踩坑记/1.png)

- 群晖上跑一个 CUPS 容器（`olbat/cupsd`），用 IPP 免驱动方式连到打印机
- 再跑一个 socat 小容器，监听 6631 端口，转发给 CUPS（为什么需要它，见「坑二」）
- Mac 在外面通过 Tailscale 访问 `sa6400:6631`，⌘P 直接打
- 群晖「任务计划」每周打一张四色小方块

## 第一步：人不在家，先找到打印机

打印机只要连上了家里 WiFi，群晖就能找到它。我 SSH 进群晖，想 ping 一遍整个网段：

```bash
for i in $(/usr/bin/seq 1 254); do /bin/ping -c1 -W1 192.168.1.$i >/dev/null 2>&1 & done; wait
/sbin/ip neigh show | /bin/grep -v FAILED
```

结果刷出 254 行 `Done(2)`。

**坑一：群晖普通用户没有 ping 权限。** ping 的退出码 1 表示「对方没回应」，2 表示「根本没发出去」。单独 ping 一次就能看到原因：

```
ping: socket: Operation not permitted
```

换个思路：打印机都开着 631 端口（IPP），用 curl 挨个敲门就行，curl 不需要 root：

```bash
( for i in $(/usr/bin/seq 1 254); do ( /usr/bin/curl -s -m2 -o /dev/null -w "192.168.1.$i %{http_code}\n" http://192.168.1.$i:631/ | /bin/grep -v " 000$" ) & done; wait )
```

只有一个 IP 有响应：

```
192.168.1.240 301
```

认是哪台机器费了点周折。MAC 地址前缀 `08:a1:36` 查到的是富士康旗下的公司，它给很多品牌代工 WiFi 模块，说明不了什么。最后是靠跳转地址认出来的：

```bash
/usr/bin/curl -s -m3 -D - -o /dev/null http://192.168.1.240:631/
# Location: /home/status.html
```

`/home/status.html` 是兄弟打印机网页管理的固定路径。再抓一下网页标题就确认了：

```bash
/usr/bin/curl -s -k -m5 https://192.168.1.240/home/status.html | /bin/grep -i -o -m5 '<title>[^<]*'
# <title>Brother DCP-T436W
```

## 第二步：群晖上部署 CUPS

群晖自带的打印服务器只认 USB 线直连的打印机，支持的型号也少，所以直接上 Docker：

```bash
sudo /bin/mkdir -p /volume6/docker/cups
sudo /usr/local/bin/docker run -d \
  --name cups \
  --restart unless-stopped \
  --network host \
  -e TZ=Asia/Shanghai \
  -v /volume6/docker/cups:/backup \
  olbat/cupsd
```

加打印机，用 `everywhere` 免驱动方式，CUPS 会自己去问打印机支持什么：

```bash
sudo /usr/local/bin/docker exec cups lpadmin -p Brother_T436W -E -v ipp://192.168.1.240/ipp/print -m everywhere
sudo /usr/local/bin/docker exec cups lpoptions -d Brother_T436W
sudo /usr/local/bin/docker exec cups lp -d Brother_T436W /usr/share/cups/data/testprint
```

25 秒后，任务状态变成 completed。我在外面看不到出纸，后来家里确认，纸盘里确实躺着测试页。**群晖 → 打印机这一段，一次就通了。**

## 坑二：从 Tailscale 访问，CUPS 一律回 400

想在外面打开 CUPS 后台，浏览器访问 `100.x.x.x:631`，先得到一个 503：

![](/images/群晖CUPS远程打印踩坑记/2.png)

503 是 Mac 上的代理软件回的，后面再说。绕开代理再试，换成了「无效请求」：

![](/images/群晖CUPS远程打印踩坑记/3.png)

响应头里写着 `Server: CUPS/2.4`，说明请求确实到了 CUPS，是 CUPS 自己拒绝的。看 CUPS 日志：

```
Request from "localhost" using invalid Host: field "sa6400:631".
```

**请求明明是从我外面的 Mac 发来的，CUPS 却认为它来自 localhost。**

原因在群晖的 Tailscale 套件：它默认跑在**用户空间模式**，系统里没有真正的 tailscale0 网卡。从 Tailscale 进来的连接，由 tailscaled 进程**从 127.0.0.1 转交**给本机端口。

而 CUPS 有一条防 DNS 重绑定的规则：**从本机地址来的连接，Host 头必须是 localhost，否则一律 400。** 我一开始在配置里加了 `ServerAlias *`，结果没用。查了才知道，对来自本机的连接，CUPS 根本不看 ServerAlias。

这也解释了一个当时让我很困惑的现象：同样是 `sa6400`，DSM 的 5000 端口能打开，CUPS 的 631 就不行。两者收到的连接其实一模一样，只是 DSM 不做这个检查。

![](/images/群晖CUPS远程打印踩坑记/4.png)

正规解法是把群晖的 Tailscale 改成内核模式（`tailscale configure-host`），但要重启 Tailscale。我当时就是靠 Tailscale 连着群晖，万一切换失败，人在外面就彻底失联了。

所以选了一个不动 Tailscale 的绕法：加一个 socat 中转。

```bash
sudo /usr/local/bin/docker run -d \
  --name cups-ts \
  --restart unless-stopped \
  --network host \
  alpine/socat \
  TCP-LISTEN:6631,fork,reuseaddr TCP:192.168.1.128:631
```

连接先到 socat，socat 再用群晖的局域网 IP 去连 CUPS。CUPS 看到的来源是 192.168.1.128，不再是 127.0.0.1，那条规则就不会触发。剩下的 Host 检查，前面加的 `ServerAlias *` 正好能放行。访问 `sa6400:6631`，返回 200：

![](/images/群晖CUPS远程打印踩坑记/5.png)

## 坑三：Mac 打印，任务建了，文件没传过去

在 Mac 上添加打印机：系统设置 → 打印机与扫描仪 → 添加 → IP，地址填 `sa6400:6631`，队列填 `printers/Brother_T436W`。我当时协议选的是 IPP，「使用」选了「通用 PostScript 打印机」，这一步后来证明是错的，正确选法见「坑五」。

打印了一张，CUPS 里出现一个 **0k、held** 的任务，一直卡着不动。

我第一反应是端口问题：CUPS 告诉 Mac「打印机在 631」，Mac 改去 631 传文件，又撞上了坑二。听起来很合理，但看了 access_log 发现完全不是：

```
192.168.1.128 - - "POST /printers/Brother_T436W" 200 Create-Job successful-ok
192.168.1.128 - - "POST /printers/Brother_T436W" 401 Send-Document successful-ok
```

请求全部经 6631 正常到达。问题是**建任务成功，传文件时被要求身份验证（401）**。

CUPS 默认规定，往任务里追加文件（Send-Document）必须由任务的创建者本人来做（`Require user @OWNER @SYSTEM`）。Mac 建任务和传文件两步报的用户对不上，CUPS 就要求登录。Mac 也不弹登录框，直接放弃，所以 Mac 那边的打印队列是空的，像什么都没发生过一样。

CUPS 只在家里局域网和我自己的 Tailscale 里能访问到，去掉这条限制问题不大：

```bash
sudo /usr/local/bin/docker exec cups cp /etc/cups/cupsd.conf /etc/cups/cupsd.conf.bak
sudo /usr/local/bin/docker exec cups sed -i '/<Limit Send-Document/,/<\/Limit>/{/Require user/d}' /etc/cups/cupsd.conf
sudo /usr/local/bin/docker restart cups
sudo /usr/local/bin/docker exec cups sh -c "cp -a /etc/cups/cupsd.conf /backup/"
```

再打一张，108k，completed：

![](/images/群晖CUPS远程打印踩坑记/6.png)

-4、-5 就是被 401 卡死的两个空任务。

## 坑四：能打了，但是慢

能打了，可点完打印要等很久才出纸。查 Tailscale 的连接状态：

```bash
/Applications/Tailscale.app/Contents/MacOS/Tailscale ping sa6400
# pong from sa6400 via DERP(sfo) in 426ms
# direct connection not established
```

**没有直连，走的是旧金山的中转服务器。** 人在国内，Tailscale 却选了美国节点，这本身就不正常。两边各跑一次 `tailscale netcheck` 对比：

| | Mac | 群晖 |
|---|---|---|
| 出口 IPv4 | 境外 IP（代理节点） | 电信公网 IP |
| NAT 类型 | 难打洞 | 好打洞 |
| 到各中转节点的延迟 | 全部 1 秒左右 | 160～250ms |

结论很清楚：**Mac 上的 Shadowrocket 把 Tailscale 自己的流量也代理出去了。** 出口 IP 变成了代理服务器的，NAT 类型也随之变成难打洞，直连自然建不起来。

Shadowrocket 的 `tun-excluded-routes` 里本来就有 `100.64.0.0/10`。但这条只放行了 Tailscale 的内网流量，Tailscale 自己在外网上的流量没放行：打洞探测（STUN）、连中转服务器、发往家里公网 IP 的包，全进了代理。在 `[Rule]` 最前面补上：

```
IP-CIDR,100.64.0.0/10,DIRECT,no-resolve
DOMAIN-SUFFIX,tailscale.com,DIRECT
DOMAIN-SUFFIX,tailscale.io,DIRECT
AND,((PROTOCOL,UDP),(DEST-PORT,3478)),DIRECT
AND,((PROTOCOL,UDP),(DEST-PORT,41641)),DIRECT
GEOIP,CN,DIRECT
```

两个细节：

- Shadowrocket 不认单独写的 `DEST-PORT` 规则（编辑器里不变色），要包在 `AND` 组合规则里。
- 3478 这条最关键。STUN 探测是直接发往中转服务器 IP 的，不带域名，`tailscale.com` 的域名规则管不到它。

改完重连：

```
pong from sa6400 via [240e:...]:41641 in 40ms
```

**走 IPv6 直连，延迟从 400～1400ms 降到 40ms。** 我当时用的是手机热点，热点有 IPv6，家里电信也有公网 IPv6，两边直接连上了。

顺带一提，浏览器访问 `100.x` 地址时走的是系统代理，`tun-excluded-routes` 管不到这一层。所以还要在 `skip-proxy` 里加上 `100.64.0.0/10`，前面那个 503 也就没了。

## 坑五：通用 PostScript 把 PDF 撑大十几倍（10 月 27 日补）

直连打通以后，有一次在外面打一份 28 页的 PDF，文件本身只有 2 MB 多，结果等了半个多小时才出纸。CUPS 的任务列表里，这个任务的大小是 **26583k**，差不多 26 MB。

CUPS 默认会在 `/var/spool/cups` 里留一份收到的文件，看一眼开头就知道 Mac 发来的是什么：

```bash
sudo /usr/local/bin/docker exec cups sh -c 'for f in /var/spool/cups/d00018-*; do ls -la "$f"; head -c 40 "$f" | tr -c "[:print:]\n" "."; echo; done'
```

```
-rw-r----- 1 root lp 27220036 Oct 27 14:57 /var/spool/cups/d00018-001
%!PS-Adobe-3.0
%APL_DSC_Encoding: UTF8
```

**是 PostScript。** 文件 14:57 开始写入，15:29 才打完，这半个多小时基本都花在传这 26 MB 上。

问题出在添加打印机时选的「通用 PostScript 打印机」驱动。选了它，Mac 不发原 PDF，而是先把每一页转成 PostScript。纯文字页转出来很小，可这份 PDF 主要是扫描页，图片在 PDF 里是 JPEG 压缩的；转成 PostScript 时，图片常被解开成原始像素再编码进去，体积就涨了十几倍。

解决办法是删掉这台打印机重新添加，地址和队列不变：

- **协议选「隔空打印」**（就是 AirPrint，中文版 macOS 这么翻译）
- 等它「收集打印机信息」，「使用」一栏会自动变成 **「DCP-T436W - IPP Everywhere」**

这样 Mac 会先问 CUPS 收什么格式，CUPS 说收 PDF，Mac 就发 PDF 过去，转成打印机格式这一步交给家里的群晖。严格说，Mac 发的不是原文件，而是按纸张、边距等打印设置重新生成的一份 PDF，体积会有些出入：一个 228 KB 的 PDF，CUPS 收到 251 KB；一个 1.9 MB 的，收到约 3 MB。但都在同一个量级，不像 PostScript 那样涨十几倍。

### 顺手：别让群晖留着打印过的文件

上面能看到文件开头，是因为 CUPS 默认会保留打印过的文件，任务列表里那个「Reprint Job」按钮就靠它。家用打印机打的多是孩子作业、体检单这类东西，没必要在 NAS 上留底：

```bash
sudo /usr/local/bin/docker exec cups sh -c "grep -q '^PreserveJobFiles' /etc/cups/cupsd.conf && sed -i 's/^PreserveJobFiles.*/PreserveJobFiles No/' /etc/cups/cupsd.conf || echo 'PreserveJobFiles No' >> /etc/cups/cupsd.conf"
sudo /usr/local/bin/docker exec cups sh -c 'rm -f /var/spool/cups/d000*'
sudo /usr/local/bin/docker restart cups
sudo /usr/local/bin/docker exec cups sh -c "cp -a /etc/cups/cupsd.conf /backup/"
```

第一条让以后打完不留文件，第二条删掉已经留下的。打印记录还在，只是不留内容。

## 每周自动保养

一开始每周打的是 CUPS 自带的测试页。后来发现防堵头只要让四种颜色都喷一下就够了，于是换成一个 PostScript 小文件，左上角四个 2 厘米的色块：

```bash
sudo /usr/bin/tee /volume6/docker/cups/nozzle.ps >/dev/null <<'EOF'
%!PS
/s 57 def
1 0 0 0 setcmykcolor  72 700 s s rectfill
0 1 0 0 setcmykcolor 142 700 s s rectfill
0 0 1 0 setcmykcolor 212 700 s s rectfill
0 0 0 1 setcmykcolor 282 700 s s rectfill
showpage
EOF
```

群晖「任务计划」→ 用户定义的脚本，用户选 root，每周一次：

```bash
/usr/local/bin/docker exec -i cups lp -d Brother_T436W < /volume6/docker/cups/nozzle.ps
```

这张纸顺便还能当喷嘴检查用：哪个色块出现断线或发白，就说明那个颜色开始堵了。

过了一周，查了一下有没有按时跑：

```bash
sudo /usr/syno/bin/synoschedtask --get
sudo /usr/local/bin/docker exec cups lpstat -W completed -o
```

任务计划里显示 `Last Run Time: Sun Oct 25 10:00:01`、`Status: [Success]`；CUPS 那边对应一条 root 提交、1 KB 的任务，10:00:15 打完。每周保养确实在自己跑。

插一句：媳妇儿说彩色墨刚灌满，一下就少了一小半。那不是测试页用掉的，是新机第一次开机做「初始充墨」，要把墨仓到喷头之间的墨管灌满，只有第一次会这样。

## 回头看

五个坑里有三个，我第一次的判断都是错的：

- 加 `ServerAlias *` 去解决 400，结果对本机连接根本不起作用
- 以为 Send-Document 失败是端口对不上，日志一看是 401
- 打印慢的时候，以为换成「通用 PostScript」能让文件变小，结果恰恰是它把文件撑大的

真正把问题钉死的，每次都是那几行原始输出：ping 的退出码、响应头里的 `Server:`、CUPS error_log 里那句 `Request from "localhost"`、access_log 里的 401、netcheck 里那个境外出口 IP、spool 文件开头那行 `%!PS-Adobe`。凭经验猜，猜对了能省时间，猜错了要多绕一圈。所以一旦有了假设，先找一条能证伪它的日志，比直接动手改配置划算。

还有一点感受：Tailscale 用户空间模式、CUPS 的本机检查、Shadowrocket 的代理范围，这三样单独看都是合理的设计，凑在一起就出了问题。家庭网络里叠的东西越多，越要搞清楚一个包到底是从哪儿进、从哪儿出的。

## 还没做的

- 回家后在路由器里给打印机 192.168.1.240 做 DHCP 静态绑定，免得哪天换了 IP，整条链路就断了
- 找个在家的时间，把群晖 Tailscale 改成内核模式，到时候 socat 就可以退役了
- iPhone 打印：iPhone 不能手动按 IP 添加打印机，打算做一个「投递文件夹」，手机用 DS File 把文件传进去，群晖每分钟扫一次，发现新文件就自动打印
