#!/usr/bin/env bash
#
# 有道词典笔桌面 App 的 cleanUnofficialApps 会按 Overmind appWhitelist
# 删除 sideload 小程序（重启或桌面刷新后图标消失）。
#
# 桌面 App 留了一个测试开关：
#   /userdata/.disable_app_whitelist_clean
# 文件存在时跳过清理。本脚本用于创建/移除这个开关。
#
# 用法：
#   ./fix_app_whitelist_clean.sh            # 开启跳过清理
#   ./fix_app_whitelist_clean.sh --restore  # 恢复系统清理策略
#
set -euo pipefail

FLAG="/userdata/.disable_app_whitelist_clean"

if ! command -v adb >/dev/null 2>&1; then
    echo "未找到 adb。请先安装 Android platform-tools，并确认词典笔已连接。"
    exit 1
fi

if ! adb get-state >/dev/null 2>&1; then
    echo "没有检测到词典笔。请用 USB 连接并确认 adb devices 能看到设备。"
    exit 1
fi

if [ "${1:-}" = "--restore" ]; then
    adb shell "rm -f '$FLAG'"
    echo "已移除 $FLAG"
    echo "系统桌面下次刷新/重启时可能重新清理非官方小程序。"
    exit 0
fi

adb shell "touch '$FLAG'"
adb shell "ls -l '$FLAG'"

echo
echo "已创建 $FLAG"
echo "桌面 App 的 cleanUnofficialApps 会跳过清理。"
echo "注意：这是系统测试开关，OTA/恢复出厂后可能丢失；重新运行本脚本即可。"
