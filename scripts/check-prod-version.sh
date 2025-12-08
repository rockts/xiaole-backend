#!/bin/bash
# 检查生产环境容器是否运行最新代码

echo "🔍 检查生产环境容器版本..."
echo ""

echo "1️⃣ 检查容器状态："
sudo docker ps -a | grep xiaole-backend
echo ""

echo "2️⃣ 检查容器镜像："
sudo docker inspect xiaole-backend --format='{{.Config.Image}}' 2>/dev/null || echo "容器不存在"
echo ""

echo "3️⃣ 检查镜像创建时间："
sudo docker inspect rockts/xiaole-backend:latest --format='{{.Created}}' 2>/dev/null || echo "镜像不存在"
echo ""

echo "4️⃣ 检查容器内代码版本（通过 /health 端点测试）："
curl -s http://127.0.0.1:8000/health
echo ""
echo ""

echo "5️⃣ 测试 /api/chat 路由是否存在："
curl -s -X POST "http://127.0.0.1:8000/api/chat?prompt=test" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test" 2>&1 | head -3
echo ""
echo ""

echo "6️⃣ 检查容器日志（最后 20 行，查找异常处理器相关日志）："
sudo docker logs --tail 20 xiaole-backend 2>&1 | grep -E "异常|exception|Exception|启动|启动完成" || echo "未找到相关日志"
echo ""

echo "7️⃣ 检查容器内 main.py 是否有全局异常处理器："
sudo docker exec xiaole-backend grep -n "@app.exception_handler" /app/main.py 2>/dev/null || echo "未找到全局异常处理器"
echo ""

echo "8️⃣ 检查容器内 main.py 是否有 /api 前缀路由："
sudo docker exec xiaole-backend grep -n 'prefix="/api"' /app/main.py 2>/dev/null | head -3 || echo "未找到 /api 前缀路由"
echo ""

echo "✅ 检查完成！"

