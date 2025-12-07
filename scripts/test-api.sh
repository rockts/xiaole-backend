#!/bin/bash
# 测试 API 路由脚本

echo "🔍 测试生产环境 API 路由..."
echo ""

echo "1️⃣ 测试健康检查 (GET /health):"
curl -s http://127.0.0.1:8000/health
echo ""
echo ""

echo "2️⃣ 测试 /api/chat (POST - 应该返回 405 或错误，因为缺少参数):"
curl -s -X POST "http://127.0.0.1:8000/api/chat?prompt=test" -H "Content-Type: application/json" 2>&1 | head -5
echo ""
echo ""

echo "3️⃣ 测试 /chat (POST - 无前缀版本):"
curl -s -X POST "http://127.0.0.1:8000/chat?prompt=test" -H "Content-Type: application/json" 2>&1 | head -5
echo ""
echo ""

echo "4️⃣ 测试 CORS 头（检查是否包含 ai.leke.xyz）:"
curl -s -I -X OPTIONS "http://127.0.0.1:8000/api/chat" \
  -H "Origin: https://ai.leke.xyz" \
  -H "Access-Control-Request-Method: POST" | grep -i "access-control"
echo ""
echo ""

echo "5️⃣ 查看所有注册的路由:"
echo "访问 http://127.0.0.1:8000/docs 查看 Swagger 文档"
echo ""

echo "✅ 测试完成！"

