---
title: "CookieCloud 同步失败排障:cookie 传到了作者的公共服务器,MP 却在自家门口等"
date: 2026-07-02T20:40:00+08:00
draft: false
tags: ["CookieCloud", "MoviePilot", "群晖", "Tailscale", "Shadowrocket", "网络排障"]
categories: ["NAS", "折腾记录"]
description: "MoviePilot 的 CookieCloud 站点同步一直失败?我的问题出在两头没对上:浏览器插件把 cookie 传到了 ccc.ft07.com 公共服务器,而 MP 开着本地模式在等文件。修复过程还顺带踩了一遍 Shadowrocket 系统代理劫持浏览器请求的老坑——用 MagicDNS 短名绕过。"
typora-root-url: /Users/leesdove/Documents/blog/static
---

## 现象

MoviePilot 日志里每隔几小时一条:

```
site.py - 开始同步CookieCloud站点 ...
log.py - 本地CookieCloud文件不存在：/config/cookies/<KEY>.json
site.py - CookieCloud同步失败：未从本地CookieCloud服务加载到cookie数据
```

浏览器里 CookieCloud 插件看起来也"配置过",但两边就是对不上。

## 排查:两头各说各话

**MP 侧**(配置在 `config/app.env`):

```
COOKIECLOUD_ENABLE_LOCAL='False'          ← 本地模式关着
COOKIECLOUD_HOST='http://<NAS>:3000/cookiecloud'  ← 地址却指向自己
```

日志里报"本地文件不存在",说明实际生效的是**本地模式**:MP 内置了一个 CookieCloud 服务器(`http://<MP>:3000/cookiecloud`),等浏览器插件把 cookie 上传过来,存成 `/config/cookies/<KEY>.json`。

**插件侧**(Chrome 的 CookieCloud 扩展,配置存在 leveldb 里,可以直接 strings 出来):

```bash
strings ~/Library/Application\ Support/Google/Chrome/Default/Local\ Extension\ Settings/<扩展ID>/*.log \
  | grep -oE 'endpoint[^,]*'
# endpoint":"https://ccc.ft07.com"
```

真相大白:插件把 cookie 一直上传到 **`ccc.ft07.com`——CookieCloud 作者的公共演示服务器**,而 MP 在自家门口等。两边 KEY 和密码倒是一致的,但方向完全错了。

顺便说:把 PT 站的 cookie 存在第三方公共服务器上,本身就不太妙——加密归加密,人家服务器哪天停了,你的同步链路就无声无息断了。

## 修复

目标架构:**插件 → MP 内置 CookieCloud 服务器**,零第三方依赖。

1. MP 侧,`app.env` 里 `COOKIECLOUD_ENABLE_LOCAL` 改为 `True`,重启容器
2. 插件侧,服务器地址改成 MP 的地址,KEY/密码不动,点手动同步

## 又踩一遍的坑:浏览器 + 代理软件 + Tailscale

插件地址我先填的 Tailscale IP(`http://100.x.x.x:3000/cookiecloud`),好处是 Mac 在家在外都能同步。结果手动同步直接失败——**curl 测明明是通的**。

原因是之前排障过的老问题:Mac 上代理软件(Shadowrocket)设置的系统代理,例外列表里有 10/8、192.168/16,**但没有 100.64/10**(Tailscale 的 CGNAT 段)。curl 不走系统代理所以通,浏览器(以及浏览器扩展)走系统代理,请求被交给远端代理节点——那边当然连不进你的 Tailscale 网络。

解法也是当时定下的规矩:**浏览器访问 NAS 一律用 MagicDNS 短名,不用 IP**:

```
http://sa6400:3000/cookiecloud
```

macOS 系统代理默认开着 `ExcludeSimpleHostnames`(不带点的主机名不走代理),短名绕过代理后由 Tailscale 的 MagicDNS 搜索域解析,正常直连。改完手动同步,秒成功。

## 验证

```bash
# NAS 上文件落地(422KB,时间戳是刚才)
ls -la <MP配置目录>/cookies/
# 手动触发 MP 同步
curl "http://<NAS>:3000/api/v1/site/cookiecloud?token=<API_TOKEN>"
```

## 总结

1. CookieCloud 是"插件推、服务器存、消费者取"三方结构,排障先画清楚数据流向,再看每一环指向哪里
2. MP 开本地模式时,插件的上传地址必须是 MP 自己(`/cookiecloud` 路径),KEY/密码两边一致
3. cookie 这种敏感数据,别放公共演示服务器,自托管就在 MP 里,一行配置的事
4. 系统代理环境下,curl 通 ≠ 浏览器通;Tailscale IP 会被代理劫持,用 MagicDNS 短名绕过
