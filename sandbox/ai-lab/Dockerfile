FROM python:3.12-bookworm

ENV PATH="/root/.local/bin:/usr/local/bin:${PATH}"

COPY requirements.txt /tmp/requirements.txt

# 1. 安装基础实战工具：curl, git, jq
RUN apt-get update && apt-get install -y \
    ca-certificates \
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

# 3. 安装 uv 和 OpenHands CLI，供外层 launch_ai_lab.sh 直接调用
RUN curl --retry 5 --retry-all-errors -LsSf https://astral.sh/uv/install.sh | sh \
    && ln -sf /root/.local/bin/uv /usr/local/bin/uv \
    && /usr/local/bin/uv tool install openhands --python 3.12 \
    && ln -sf /root/.local/bin/openhands /usr/local/bin/openhands \
    && ln -sf /root/.local/bin/openhands-acp /usr/local/bin/openhands-acp

# 4. 安装项目测试所需的最小依赖，恢复 agent 的自测能力
RUN uv pip install --system -r /tmp/requirements.txt \
    && rm -f /tmp/requirements.txt

# 5. 设置工作目录
WORKDIR /workspace
