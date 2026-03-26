# OpenSage Sandbox Dockerfile
# 安全隔离的 Python 执行环境

FROM python:3.13-slim

# 设置工作目录
WORKDIR /sandbox

# 安装必要的依赖（最小化）
RUN pip install --no-cache-dir \
    httpx==0.28.1 \
    pydantic==2.12.5

# 创建非 root 用户
RUN useradd -m -u 1000 sandbox

# 设置资源限制（通过 Docker）
# CPU: 50% (在 docker run 时设置)
# Memory: 512MB (在 docker run 时设置)

# 切换到非 root 用户
USER sandbox

# 暴露 JSON RPC 端口
EXPOSE 9000

# 启动沙盒服务
CMD ["python", "sandbox_server.py"]
