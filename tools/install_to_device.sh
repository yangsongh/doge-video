#!/usr/bin/env bash
#
# 安装 Doge视频 .amr，并顺手创建“跳过非官方小程序清理”的开关。
#
# 用法：
#   ./install_to_device.sh /path/to/8001145141919820.1_0_0.amr
#
set -euo pipefail

AMR="${1:-}"
if [ -z "$AMR" ] || [ ! -f "$AMR" ]; then
    echo "用法: $0 <amr 文件路径>"
    echo "AMR 可从 GitHub Releases 下载。"
    exit 1
fi

if ! command -v adb >/dev/null 2>&1; then
    echo "未找到 adb。"
    exit 1
fi

NAME="$(basename "$AMR")"
adb push "$AMR" "/userdisk/Favorite/$NAME"
adb shell "miniapp_cli install '/userdisk/Favorite/$NAME'"

# 避免重启后被桌面 App 的 cleanUnofficialApps 删除
adb shell "touch /userdata/.disable_app_whitelist_clean"

echo
echo "安装完成。"
echo "已创建 /userdata/.disable_app_whitelist_clean，重启后应用不会被自动清理。"
echo "桌面图标名称：Doge视频"
