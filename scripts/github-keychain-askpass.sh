#!/bin/sh
# git 推送博客时的取凭据脚本。
# 用户名固定为 zkzkeep，令牌从 macOS 钥匙串里读取，所以仓库里不保存任何 token。
#
# 一次性配置（生成 GitHub 令牌后，在终端执行一次，按提示粘贴令牌）：
#   security add-internet-password -s github.com -a zkzkeep -w -U -A
#
# 之后每次 git push 都会自动从钥匙串取令牌，无需再手动输入。
case "$1" in
  *[Uu]sername*)
    printf '%s' 'zkzkeep'
    ;;
  *)
    security find-internet-password -a 'zkzkeep' -s 'github.com' -w 2>/dev/null
    ;;
esac
