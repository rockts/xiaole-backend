#!/bin/bash

# 小乐 AI 重启脚本
# 用法: ./restart.sh

echo "🔄 重启小乐 AI..."

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 停止服务
./stop.sh

echo ""
echo "⏳ 等待 2 秒..."
sleep 2

# 启动服务
./start.sh
