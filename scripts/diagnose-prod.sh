#!/bin/bash
# 生产环境诊断脚本

echo "🔍 诊断生产环境后端服务..."
echo ""

echo "1️⃣ 检查容器状态："
sudo docker ps -a | grep xiaole-backend
echo ""

echo "2️⃣ 检查容器日志（最后 50 行）："
sudo docker logs --tail 50 xiaole-backend
echo ""

echo "3️⃣ 检查容器端口映射："
sudo docker port xiaole-backend
echo ""

echo "4️⃣ 测试本地健康检查："
curl -v http://127.0.0.1:8000/health
echo ""

echo "5️⃣ 测试本地 /api/chat 路由："
curl -v -X GET "http://127.0.0.1:8000/api/chat?prompt=test" 2>&1 | head -20
echo ""

echo "6️⃣ 检查容器内服务是否运行："
sudo docker exec xiaole-backend ps aux | grep uvicorn
echo ""

echo "7️⃣ 检查容器内端口监听："
sudo docker exec xiaole-backend netstat -tlnp 2>/dev/null || sudo docker exec xiaole-backend ss -tlnp
echo ""

echo "8️⃣ 检查环境变量（CORS_ORIGINS）："
sudo docker exec xiaole-backend env | grep CORS
echo ""

echo "✅ 诊断完成！"

