# 🍪 X/Twitter Cookie 配置指南

## 📋 当前状态

- ✅ agent-reach 已安装: `/Users/iCloud_GZ/.local/bin/agent-reach`
- ✅ xreach skill 已安装
- ⚠️ Twitter cookie 未配置

---

## 🔧 配置方法

### 方法 1：环境变量（推荐）

```bash
# 1. 获取 cookie（见下方步骤）

# 2. 设置环境变量
export XREACH_AUTH_TOKEN="your_auth_token_here"
export XREACH_CT0="your_ct0_here"

# 3. 验证
xreach search "test" -n 1 --json
```

### 方法 2：配置文件

```bash
# 创建配置目录
mkdir -p ~/.agent-reach

# 创建配置文件
cat > ~/.agent-reach/xreach.json << 'EOF'
{
  "auth_token": "your_auth_token_here",
  "ct0": "your_ct0_here"
}
EOF

# 设置权限
chmod 600 ~/.agent-reach/xreach.json
```

---

## 📖 获取 Cookie 步骤

### Step 1: 登录 Twitter

1. 打开浏览器（Chrome/Safari）
2. 访问 https://x.com
3. 登录你的账号

### Step 2: 打开开发者工具

- **Mac**: `Cmd + Option + I`
- **Windows/Linux**: `F12` 或 `Ctrl + Shift + I`

### Step 3: 查看 Cookie

1. 点击 **Application** 标签
2. 左侧菜单: **Storage → Cookies → https://x.com**
3. 找到以下关键 cookie：

| Cookie 名称 | 用途 | 必需 |
|------------|------|------|
| `auth_token` | 身份认证 | ✅ 必须 |
| `ct0` | CSRF token | ✅ 必须 |
| `guest_id` | 访客 ID | ❌ 可选 |

### Step 4: 复制 Cookie

1. 右键点击 `auth_token` 行
2. 选择 **Copy**
3. 粘贴到配置文件或环境变量

---

## 🧪 验证配置

```bash
# 测试搜索功能
xreach search "AI" -n 5 --json

# 测试读取推文
xreach tweet "https://x.com/username/status/123456789" --json

# 检查配置
xreach doctor
```

---

## ⚠️ 注意事项

### 安全建议

1. **不要分享** cookie 给任何人
2. **定期更新** cookie（Twitter 可能过期）
3. **使用专用账号** 避免影响主账号

### 常见问题

**Q: Cookie 多久过期？**
A: 通常 30-90 天，取决于 Twitter 设置

**Q: 为什么搜索失败？**
A:
- Cookie 过期 → 重新获取
- IP 被限制 → 使用代理
- 账号被限制 → 检查账号状态

**Q: 如何使用代理？**
```bash
export XREACH_PROXY="http://127.0.0.1:7890"
```

---

## 🚀 快速配置脚本

```bash
#!/bin/bash
# 配置 X/Twitter cookie

echo "请输入 auth_token:"
read AUTH_TOKEN

echo "请输入 ct0:"
read CT0

# 创建配置
mkdir -p ~/.agent-reach
cat > ~/.agent-reach/xreach.json << EOF
{
  "auth_token": "$AUTH_TOKEN",
  "ct0": "$CT0"
}
EOF

chmod 600 ~/.agent-reach/xreach.json

# 测试
echo "测试配置..."
xreach search "hello" -n 1 --json && echo "✅ 配置成功！" || echo "❌ 配置失败"
```

---

## 📞 需要帮助？

如果配置遇到问题，请告诉我：
1. 具体错误信息
2. 你使用的方法（环境变量/配置文件）
3. 是否需要使用代理

**创建时间**: 2026-03-26 09:30 GMT+8
