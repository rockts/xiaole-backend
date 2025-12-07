#!/bin/bash
# 检查 Cloudflare Tunnel 状态

echo "🔍 检查 Cloudflare Tunnel 状态..."
echo ""

echo "1️⃣ 检查 cloudflared 进程："
ps aux | grep cloudflared | grep -v grep
echo ""

echo "2️⃣ 检查 cloudflared 容器（如果使用 Docker）："
sudo docker ps -a | grep cloudflared
echo ""

echo "3️⃣ 检查 cloudflared 日志（如果使用 systemd）："
if systemctl is-active --quiet cloudflared 2>/dev/null; then
    echo "✅ cloudflared service 正在运行"
    sudo journalctl -u cloudflared --no-pager -n 50
else
    echo "⚠️ cloudflared service 未运行或未使用 systemd"
fi
echo ""

echo "4️⃣ 检查 cloudflared 容器日志（如果使用 Docker）："
if sudo docker ps -a | grep -q cloudflared; then
    CONTAINER_NAME=$(sudo docker ps -a | grep cloudflared | awk '{print $NF}' | head -1)
    echo "📋 容器名称: $CONTAINER_NAME"
    sudo docker logs --tail 50 $CONTAINER_NAME 2>&1
else
    echo "ℹ️ 未找到 cloudflared 容器"
fi
echo ""

echo "5️⃣ 测试从外部访问（如果配置了 DNS）："
echo "   访问 https://api.leke.xyz/health 应该返回 {\"status\":\"ok\"}"
echo ""

echo "✅ 检查完成！"

