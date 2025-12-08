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

# 禁用人脸识别（避免 dlib/face_recognition 在某些环境下崩溃）
ENV DISABLE_FACE_RECOGNITION=true

# 工作目录
WORKDIR /app

# 复制所有后端代码
COPY . .

# 安装 Python 依赖
RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --no-cache-dir -r requirements.txt

# 暴露端口
EXPOSE 8000

# 启动服务
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
