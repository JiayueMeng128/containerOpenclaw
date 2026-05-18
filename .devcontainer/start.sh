#!/bin/bash

# ========== 1. 启动 NapCat ==========
QQ_NUMBER="1729203925"                # 请替换为你的实际QQ号
NAPCMD="/usr/local/bin/napcat"

if pgrep -f "napcat.*$QQ_NUMBER" > /dev/null; then
    echo "✅ NapCat 服务已在运行"
else
    echo "🚀 启动 NapCat 服务..."
    nohup sudo $NAPCMD start $QQ_NUMBER > /tmp/napcat.log 2>&1 &
    sleep 2
    if pgrep -f "napcat.*$QQ_NUMBER" > /dev/null; then
        echo "✅ NapCat 已启动 (日志: /tmp/napcat.log)"
    else
        echo "❌ NapCat 启动失败，请检查 /tmp/napcat.log"
    fi
fi

# ========== 2. 启动 OpenClaw 网关 ==========
if ! pgrep -f "openclaw gateway" > /dev/null; then
    echo "🚀 启动 OpenClaw 服务..."
    nohup openclaw gateway --verbose > /workspaces/$(basename $PWD)/openclaw.log 2>&1 &
    echo "✅ OpenClaw 服务已启动"
else
    echo "✅ OpenClaw 服务已在运行"
fi

# ========== 3. 输出访问地址 ==========
echo "🌐 OpenClaw Web UI: https://${CODESPACE_NAME}-18789.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}"

# 提示 NapCat 端口访问方式（无论 JSON 是否转发，都给出说明）
echo "📌 NapCat WebUI 端口: 6099, WebSocket 端口: 3001"
echo "   如果端口未自动转发，请手动在 Codespace 的“端口”标签页添加转发"
