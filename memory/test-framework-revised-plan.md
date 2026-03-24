# Claude CLI 测试框架实施方案（修订版）

**修订时间**: 2026-03-25 01:02  
**修订原因**: Claude CLI不是Node.js项目

---

## 🔍 项目结构分析

**Claude CLI实际结构**：
- ❌ 无package.json（不是Node.js项目）
- ✅ 有agents/目录（可能是Shell/Python脚本）
- ✅ 有skills/目录
- ✅ 有hooks/目录

**推测技术栈**：
- Shell脚本（.sh）
- Python脚本（.py）
- Markdown文档（.md）

---

## 🎯 修订后的测试策略

### 方案1：Shell脚本测试（推荐）

**使用bats-core**：
```bash
# 安装bats
brew install bats-core

# 创建测试目录
mkdir -p tests

# 创建测试文件
touch tests/agents.bats
touch tests/hooks.bats
```

**测试示例（agents.bats）**：
```bash
#!/usr/bin/env bats

@test "agents directory exists" {
  [ -d "agents" ]
}

@test "global-doc-master exists" {
  [ -f "agents/global-doc-master/global-doc-master.md" ]
}
```

### 方案2：Python测试（备选）

**使用pytest**：
```bash
pip install pytest

# 创建测试文件
touch tests/test_agents.py
```

---

## 📋 实施步骤

### 第1步：安装bats-core
```bash
brew install bats-core
```

### 第2步：创建测试框架
```bash
mkdir -p tests
cd tests

# 创建基础测试
cat > sanity.bats << 'EOF'
#!/usr/bin/env bats

@test "project structure is valid" {
  [ -d "agents" ]
  [ -d "skills" ]
  [ -d "hooks" ]
}
EOF
```

### 第3步：运行测试
```bash
bats tests/
```

---

## 🎯 目标覆盖率

- **Shell脚本测试**：80%
- **文档完整性检查**：100%
- **Hook功能测试**：70%

---

**维护者**: OpenClaw Agent  
**状态**: 🔄 策略调整中
