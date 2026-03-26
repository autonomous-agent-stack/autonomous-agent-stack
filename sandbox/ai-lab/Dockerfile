FROM python:3.11-bookworm

# 1. 安装基础实战工具：curl, git, jq
RUN apt-get update && apt-get install -y \
    curl \
    git \
    jq \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# 2. 安装 GitHub CLI (gh) —— 龙虾的灵魂扳手
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update && apt-get install -y gh \
    && rm -rf /var/lib/apt/lists/*

# 3. 设置工作目录
WORKDIR /workspace
