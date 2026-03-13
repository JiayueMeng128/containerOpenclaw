#!/bin/bash
if ! pgrep -f "openclaw gateway" > /dev/null; then
    echo "🚀 启动 OpenClaw 服务..."
    nohup openclaw gateway --verbose > /workspaces/$(basename $PWD)/openclaw.log 2>&1 &
    echo "✅ OpenClaw 服务已启动"
else
    echo "✅ OpenClaw 服务已在运行"
fi

echo "🌐 访问 Web UI: https://${CODESPACE_NAME}-18789.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}"
