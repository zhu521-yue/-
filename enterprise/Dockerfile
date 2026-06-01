FROM python:3.11-slim

WORKDIR /app

# 换国内镜像源（清华）
RUN sed -i 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# 复制依赖文件（先复制依赖，利用 Docker 缓存）
COPY requirements.deploy.txt ./requirements.txt

# 安装 Python 依赖（不装 sentence-transformers，省内存）
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# 复制项目代码
COPY src/ ./src/

# 创建日志目录
RUN mkdir -p logs

EXPOSE 8000

# 生产环境用 1 worker，省内存；3.6G 服务器够用
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
