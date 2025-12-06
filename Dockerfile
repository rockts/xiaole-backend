# ============================================
# Python 后端 (前端已迁移到 Cloudflare Pages)
# ============================================
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    cmake \
    build-essential \
    libboost-all-dev \
    libopenblas-dev \
    libgtk-3-dev \
    git \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 工作目录
WORKDIR /app

# 复制后端代码
COPY backend/ ./backend/
COPY tools/ ./tools/
COPY scripts/ ./scripts/
COPY requirements.txt ./
COPY start_services.sh ./

# 安装 Python 依赖
RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --no-cache-dir -r requirements.txt

# 添加执行权限
RUN chmod +x start_services.sh

# 暴露端口
EXPOSE 8000 9000

# 启动服务
CMD ["bash", "start_services.sh"]
