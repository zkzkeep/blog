#!/bin/bash
# 双击即发布：整理图片、改写 Markdown、构建 Hugo、提交并推送，Cloudflare Pages 自动上线。
# 注意：变量一律写成 ${VAR} 形式。macOS 自带 bash 3.2 在中文 locale 下会把紧跟
# 变量的全角字符（如“（”“。”）误并入变量名，裸写 $VAR 会报 unbound variable。
set -uo pipefail

# 双击（GUI 启动）时 PATH 可能不含 Homebrew，显式补上，保证能找到 hugo / python3。
export PATH="/opt/homebrew/bin:/usr/local/bin:${PATH}"

cd "$(dirname "$0")" || { echo "找不到博客目录"; exit 1; }

LOG="$(mktemp -t blog-publish.XXXXXX.log)"
STAMP="$(date '+%Y-%m-%d %H:%M')"

# 设 BLOG_PUBLISH_NO_DIALOG=1 可关闭弹窗（测试或后台调用时用），只在终端打印。
notify() {
  [ "${BLOG_PUBLISH_NO_DIALOG:-}" = "1" ] && return 0
  osascript -e "display notification \"$2\" with title \"$1\"" >/dev/null 2>&1 || true
}
dialog() {
  [ "${BLOG_PUBLISH_NO_DIALOG:-}" = "1" ] && return 0
  osascript -e "display dialog \"$2\" buttons {\"好的\"} default button \"好的\" with title \"$1\"" >/dev/null 2>&1 || true
}

echo "开始发布博客…（${STAMP}）"
echo "日志：${LOG}"
echo

python3 deploy.py --message "auto deploy ${STAMP}" 2>&1 | tee "${LOG}"
code=${PIPESTATUS[0]}
echo

if [ "${code}" -eq 0 ]; then
  notify "博客发布成功 🎉" "已推送，Cloudflare Pages 正在部署"
  dialog "博客发布" "发布成功！

Cloudflare Pages 正在自动部署，约 1 分钟后生效。

网站：https://leesy.cc"
  echo "发布成功。窗口可以关闭了。"
else
  # 取最后几行日志作为失败原因，转义反斜杠和双引号避免 AppleScript 出错。
  reason="$(tail -n 12 "${LOG}" | sed 's/\\/\\\\/g; s/"/\\"/g')"
  dialog "博客发布失败" "发布没有完成（退出码 ${code}）。

最近日志：
${reason}

完整日志：
${LOG}"
  echo "发布失败，退出码 ${code}。完整日志：${LOG}"
fi

exit "${code}"
