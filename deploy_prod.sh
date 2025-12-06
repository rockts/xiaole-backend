#!/bin/bash
set -e

REPO_DIR="/volume2/docker/xiaole-ai"
LOGS_DIR="$REPO_DIR/logs"

echo "🚀 进入项目目录：$REPO_DIR"
cd $REPO_DIR

echo "🚀 拉取 main 分支最新代码"
git fetch origin main
git reset --hard origin/main

echo "🚀 创建生产用 .env 文件"
cp -f .env.example .env

# 验证必需的环境变量
: "${DB_USER:?必须设置 DB_USER 环境变量}"
: "${DB_PASS:?必须设置 DB_PASS 环境变量}"
: "${DEEPSEEK_API_KEY:?必须设置 DEEPSEEK_API_KEY 环境变量}"
: "${WEBHOOK_SECRET:?必须设置 WEBHOOK_SECRET 环境变量}"

# 替换所有配置
sed -i "s/DB_HOST=.*/DB_HOST=192.168.88.188/" .env
sed -i "s/DB_USER=.*/DB_USER=${DB_USER}/" .env
sed -i "s/DB_PASS=.*/DB_PASS=${DB_PASS}/" .env
sed -i "s/USE_CLAUDE=.*/USE_CLAUDE=false/" .env
sed -i "s/DEEPSEEK_API_KEY=.*/DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}/" .env
sed -i "s/WEBHOOK_SECRET=.*/WEBHOOK_SECRET=${WEBHOOK_SECRET}/" .env

# 如果有其他 API Key,也替换
if [ ! -z "$QWEN_API_KEY" ]; then
    sed -i "s/QWEN_API_KEY=.*/QWEN_API_KEY=${QWEN_API_KEY}/" .env
fi
if [ ! -z "$BAIDU_APP_ID" ]; then
    sed -i "s/BAIDU_APP_ID=.*/BAIDU_APP_ID=${BAIDU_APP_ID}/" .env
    sed -i "s/BAIDU_API_KEY=.*/BAIDU_API_KEY=${BAIDU_API_KEY}/" .env
    sed -i "s/BAIDU_SECRET_KEY=.*/BAIDU_SECRET_KEY=${BAIDU_SECRET_KEY}/" .env
fi

mkdir -p $LOGS_DIR
mkdir -p $REPO_DIR/backend/uploads/images
mkdir -p $REPO_DIR/files

# 确保目录权限开放,防止容器无权写入
chmod -R 777 $REPO_DIR/backend/uploads
chmod -R 777 $REPO_DIR/files
chmod -R 777 $LOGS_DIR

echo "🚀 拉取最新镜像"
sudo docker pull rockts/xiaole-ai:latest

echo "🚀 重启后端容器"
sudo docker rm -f xiaole-ai 2>/dev/null || true
sudo docker run -d --name xiaole-ai \
  --restart=always \
  -p 8000:8000 \
  -p 9000:9000 \
  -v /etc/localtime:/etc/localtime:ro \
  -e TZ=Asia/Shanghai \
  -v $LOGS_DIR:/app/logs \
  -v $REPO_DIR/backend:/app/backend \
  -v $REPO_DIR/tools:/app/tools \
  -v $REPO_DIR/backend/uploads:/app/backend/uploads \
  -v $REPO_DIR/files:/app/files \
  --env-file .env \
  rockts/xiaole-ai:latest

echo "🩺 健康检查..."
# 循环检查服务状态,最多等待 30 秒
for i in {1..15}; do
    if curl -s http://127.0.0.1:8000/health > /dev/null; then
        echo "✅ FastAPI 服务已启动"
        break
    fi
    echo "⏳ 等待服务启动... ($i/15)"
    sleep 2
done

if ! curl -s http://127.0.0.1:8000/health > /dev/null; then
    echo "⚠️ FastAPI 未响应，请检查 docker logs xiaole-ai"
fi



echo "✅ 部署完成！"