---
title: "从下载到保种：飞牛 NAS 打造全自动 PT 机的十个坑"
date: 2026-07-20T15:10:00+08:00
draft: false
tags: ["飞牛OS", "NAS", "PT", "MoviePilot", "Prowlarr", "cross-seed", "Emby", "Vaultwarden", "Tailscale", "Docker", "网络排障"]
categories: ["NAS", "折腾记录"]
description: "一天把飞牛 NAS 从空盘重建成影音站只是开始，真正的战争是接下来几天：把它调成『下载→转种→辅种』全自动的 PT 机。这里记录十个真实的坑——MoviePilot 每次重建就崩、PT 站验证码与 IPv6-only 的 .NET 死结、IYUU 收费后换 cross-seed 的注入血泪、Emby 电视剧死活不显示、Bitwarden 同步慢的真相，以及换电脑后 Tailscale 又被代理抢路由。附每个坑的根因与解法。"
typora-root-url: /Users/leesdove/Documents/blog/static
---

上一篇《一天重建飞牛 NAS》讲的是把服务搭起来。但搭起来只是能用，离「下载完什么都不用管、自动转种保种辅种」还差着十万八千里。接下来几天的折腾，才是真正的战争。

这篇按坑记录，每个坑都是：**现象 → 根因 → 解法**。给同样在折腾 PT 自动化的人抄作业，也给未来的自己留个底。

## 坑一：MoviePilot 每次重建容器就崩

**现象**：网页能打开，但全是 `0.00 B`、点什么都提示「暂时无法连接」。容器状态 `unhealthy`，但没退出。

**排查**：前端是静态文件所以能开，后端 API 全 502。进去看后端 Python 进程——没了。日志里翻到真凶：

```
PermissionError: [Errno 13] Permission denied:
'/opt/venv/lib/python3.12/site-packages/cloakbrowser/__init__.py'
```

后端一 import 就崩。扫一遍 venv：**2500 多个包文件权限变成了 `000`（谁都不能读）**。MP 以非 root 用户跑，读不了自然崩。

**根因**：镜像加速站拉下来的镜像，`/opt/venv` 里一批文件权限是坏的。只要 `docker compose up -d` **重建**容器（加挂载、改配置都会触发），权限就重新变 `000`。`docker restart` 不会，因为它不重新解包镜像层。

**解法**：

```sh
docker exec -u 0 moviepilot chmod -R a+rX /opt/venv
docker restart moviepilot
```

血泪教训：**每次重建 MP 容器后，必须补这条 chmod**。这个坑我踩了三次才形成肌肉记忆。

## 坑二：PT 站的图形验证码，Prowlarr 死活过不去

**现象**：往 Prowlarr 加国内 PT 站，一堆报 `Found captcha during automatic login, aborting`，或者验证码填了点保存就过期。

**根因**：这些 NexusPHP 站用「表单 + 图形验证码」登录，Prowlarr 每次会话过期都要重新过验证码，自动化根本没法维持。

**解法**：给每个站做一个 **cookie 登录版**的自定义定义，彻底绕开验证码。Prowlarr 的 Cardigann 定义支持 `method: cookie`：

```yaml
login:
  method: cookie
  inputs:
    cookie: "{{ .Config.cookie }}"
  test:
    path: index.php
    selector: a[href="logout.php"]
```

我扫了一遍所有中文站，把 30 个「表单+验证码」的站用脚本批量转成了 cookie 版（改 id、去掉用户名密码字段、换 login 段、`caps`/`search` 原样保留），丢进 `Definitions/Custom/`，重启 Prowlarr 就多出 30 个「XX (Cookie)」。填浏览器 cookie 即可，一劳永逸。

顺带发现：另有 69 个中文站本来就是 cookie 登录，直接填就行。

## 坑三：有的站 curl 通、浏览器通，唯独 Prowlarr 连不上

这是最诡异、也最让人抓狂的一个，前后耗了大半天。

**现象**：某重要站，Prowlarr 加它一直超时 / `No data available`。但我在同一台机器上 `curl` 带 cookie 访问它的种子页，**200、秒回、内容正常**。

**层层排查**：

1. 不是 UA 问题——任何 UA `curl` 都 200；
2. 不是站点挂了——`curl` 好好的；
3. 用 `curl -4` / `curl -6` 分别测，真相浮现：**这个站只有 IPv6 能通，IPv4 的 Cloudflare 线路从我这条宽带完全不可达**（国内到 Cloudflare IPv4 anycast 路由差，IPv6 反而好，很常见）；
4. 而 Prowlarr 的 .NET 连接层在这个环境**只认 IPv4**——钉死 IPv6 后它直接报 `No data available`。

**尝试的解法**（全试了）：

- Prowlarr 改 **host 网络**，借宿主机的好 IPv6 → 其它 IPv6 站救回来了；
- 给这个站 **钉死 IPv6 主机路由**（`extra_hosts`）；
- 部署 **FlareSolverr**（无头 Chrome 代理）→ 它自己能拿到这个站的 200；
- 但 Prowlarr 的 FlareSolverr 代理**只在检测到 Cloudflare 挑战页时才介入**，而这个站返回的是「连接失败」不是「挑战页」，代理压根不触发；
- 连数据库硬插索引器 + 打 flaresolverr 标签都试了——搜索时还是走 .NET 直连，还是 `No data available`。

**诚实的结论**：这个站**无法接入 Prowlarr**。curl 和 FlareSolverr 都能连，唯独 Prowlarr 底层的 .NET 连不上 IPv6-only + Cloudflare 的组合，要改就得重编译 .NET，我改不动。

好在它**手动下载 + 做种完全正常**（qb/tr 走 IPv6 能连它 tracker），只是进不了自动辅种池。知道什么时候该收手，也是一种能力。

> 附带一个同类：某站用了 **雷池（SafeLine）WAF**，返回自定义状态码 468。连 FlareSolverr 的真实 Chrome 都解不开它的人机验证。这类站认命，手动用。

## 坑四：Redacted 的 API key 错了，别反复重试——IP 会被封

**现象**：加 Redacted，报 `bad credentials`。多点了几次「测试」，突然变成 `your ip has been temporarily banned`。

**根因**：API key 权限不够（创建时没勾 Torrents / User 读取权限），而 **Redacted 对 API 认证失败很敏感，连续失败几次就临时封你的 IP**。

**教训**：这类站 API key 错了**别反复试**，先去站点确认 key 是对的、权限勾全了，再试一次。封了就等它自动解，越试封越久。

## 坑五：IYUU 开始收费了，换 Prowlarr + cross-seed 辅种的血泪

IYUU 免费额度限流限量（一次只能 20 个种），而且它开源但云端接口闭源，命门捏在别人手里。换成全开源的 **cross-seed**（配合 Prowlarr）。

搭的过程踩了一串坑：

- **匹配很好，注入全失败**：种子模式下单个源种匹配到 11 个站，但注入报 `TORRENT_NOT_FOUND`——cross-seed 定位不到源数据去做硬链接。解法：从「数据目录扫描」换成「**直连下载器客户端**」模式，让它拿到每个种子的确切路径和完成状态。
- **空的 tr 把整个注入带崩**：客户端列表里同时放了 qb 和 tr，而 tr 当时是空的，cross-seed 检查空客户端时报 `No torrents found`，**一个错误带崩所有注入**。解法：客户端只留一个。
- **中文/DIY 命名的种标题误判**：数据模式靠「大小 + 标题」匹配，中文命名的种经常因标题解析对不上被拒。种子模式（比对文件结构）准得多。

最终方案：**cross-seed 只连 tr（数据源+注入目标都是它），种子文件匹配模式**。一次 `inject` 成功 81/81，单个源种匹配十几个站，效果炸裂。

## 坑六：qb 下载、tr 保种，但「不能两边同时做种」

PT 圈的硬规则：**同一个种子不能在两个客户端同时做种**，会被判定作弊。

我最初用 MoviePilot 的「自动转移做种」插件转种（qb → tr），但默认 `deletesource=False`——转到 tr 后 qb 不删，**两边一起做种，违规了**。

**解法**：开插件的 `deletesource` + `deleteduplicate`。但这里有个数据安全的坑——qb 和 tr **共用同一份数据文件**做种，删 qb 时**绝不能连文件一起删**。查了插件源码确认：

```python
if self._deletesource:
    from_downloader.delete_torrents(delete_file=False, ids=[...])
```

`delete_file=False`——只删种子、保留文件。tr 继续用同一份文件做种，不断种、不 H&R。确认安全后才敢开。

**看代码再动手，别猜**——尤其涉及删除 PT 种子（断种 = 潜在 H&R 罚分）。

## 坑七：让辅种「即时」，不等每天

cross-seed 默认每天全量搜一次，新种要等下一轮。想要「种子一进 tr 就立即辅种」，用 **Transmission 的完成脚本**：

`settings.json` 里开 `script-torrent-done-enabled`，脚本在种子做种时 curl cross-seed 的 webhook，传 `infoHash`，触发即时搜索：

```sh
#!/bin/sh
curl -s -X POST "http://cross-seed:2468/api/webhook" \
  -H "X-Api-Key: <脱敏>" \
  --data-urlencode "infoHash=${TR_TORRENT_HASH}"
```

cross-seed 很聪明，对自己注入的辅种会识别 `it is a cross seed` 跳过，**避免无限循环**。

至此完整闭环：**下载 → 转种到 tr → 校验完成的瞬间 → 立即全站辅种**，零操作。

## 坑八：Emby 里电视剧死活不显示

**现象**：电影正常，电视剧库空的。

**三层问题层层剥开**：

1. **MoviePilot 只整理「它自己下载的」种子**——我手动加种下的剧全卡在下载目录没被整理进库。解法：把目录监控从 `downloader` 模式改成 `monitor`（目录监控），盯下载目录，谁下的都整理。
2. **整理了但散装**——文件平铺在库根目录，没有 `剧名/季/` 文件夹结构，Emby 识别不良。根因：MP 的重命名格式没生效。最后干脆脚本手动硬链接成 `剧名 (年份)/剧集` 结构。
3. **Emby 刮削卡死在 41%**——连不上 TMDB（国内到境外）。解法：给 Emby 容器挂 `HTTP_PROXY` 指向本地 mihomo，本地流媒体走 `NO_PROXY` 直连。

刮削一恢复，7 部剧 62 季 1051 集全部识别。

## 坑九：Bitwarden 同步慢的真相

**现象**：密码在设备间同步又慢又不及时。

**关键转折**：以为是自托管 Vaultwarden 的配置问题，折腾半天，结果用户一句「我用的是官方的，不是 Docker 里那个」点醒了我——**同步问题出在官方 Bitwarden 云（服务器在美国），国内访问又慢又不稳，这是跨境网络的锅，不是配置能修的**。

而这恰恰是当初自托管 Vaultwarden 的意义：服务器就在家里 NAS 上，走 Cloudflare 隧道，国内秒同步。迁过去（导出 JSON → 自托管注册 → 导入 → 客户端切服务器地址）后，实测「很快，很赞」。

顺带修了自托管 Vaultwarden 一个经典坑：**`DOMAIN` 环境变量没设**，导致浏览器/桌面端的 WebSocket 实时推送根本建立不起来。设上 `DOMAIN=https://<你的域名>` 重启，日志立刻出现 `Accepting Rocket WS connection`，实时同步生效。

## 坑十：换电脑后，Tailscale 又连不上了

**现象**：某天 SSH 连家里 NAS 全超时。但 `tailscale ping` 却通（152ms，走 IPv6 直连）。

**排查**：查路由表，发现发往 Tailscale 网段（`100.64.0.0/10`）的流量，被路由到了**物理网卡 en0 的网关**，而不是 Tailscale 的 utun。也就是——**另一个代理软件抢了 Tailscale 的路由**。

**根因**：换了新电脑，之前配好的「`/32` 主机路由 + 自愈守护」没带过来。而新装的代理（Karing / Shadowrocket 这类 TUN 模式代理）默认会把 CGNAT 网段 `100.64.0.0/10` 甩给物理网关，直接压死 Tailscale 的路由。（这个坑我在《Shadowrocket 与 Tailscale 共存》那篇专门写过，这次是换机重演。）

**解法**：加一条 `/32` 主机路由，用「前缀越长优先级越高」的规则精确碾压代理那条 `/10`，并做成 LaunchDaemon 自愈（开机自启 + 每 30 秒纠正 + 动态找持有 100.x 地址的 utun 网卡）：

```sh
route -n add -host <NAS的Tailscale_IP> -interface <Tailscale的utun>
```

跑一次一键脚本，路由恢复，SSH 立刻通。以后换电脑，把脚本拷过去跑一遍就行。

---

## 尾声

十个坑填完，这台飞牛 NAS 终于成了真正的「傻瓜式」PT 机：

- **qb** 只管下载（保持轻量）；
- **转种插件**每 2 小时把完成的搬到 tr 并清空 qb（保留文件、不双做种）；
- **tr** 校验完成的瞬间触发 **cross-seed 即时全站辅种**；
- **MoviePilot** 目录监控自动整理进库，**Emby** 挂代理刮削出海报；
- 全程零操作。

回头看，这几天真正难的从来不是「搭服务」，而是**一个个环节之间的缝隙**：镜像的坏权限、.NET 的 IPv6 脾气、PT 站的反自动化、跨境网络的延迟、代理与隧道的路由之争。每个坑单独看都不难，但叠在一起、还要保证不断种不违规，就得一层层剥。

工具会越来越好用，但排障的思路——**先复现、再定位每一环指向哪里、curl 通不等于程序通、看代码别猜、知道何时收手**——是抄不来的。
