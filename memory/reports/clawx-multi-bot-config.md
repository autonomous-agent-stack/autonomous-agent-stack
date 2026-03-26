# ClawX 多机器人配置方案

> 创建时间：2026-03-24 17:39
> 
> 用途：当需要配置多个 Telegram Bot 时的快速参考

---

## 📋 方案选择

### ✅ 方案 A：手动配置（推荐优先）
- **时间成本**：2 分钟
- **技术要求**：无
- **适用场景**：立即可用，零开发成本

### ⏸️ 方案 B：PR 改进 UI（低优先级后台任务）
- **时间成本**：3 周（碎片时间）
- **技术要求**：React/TypeScript
- **适用场景**：贡献社区，改善用户体验

### ❌ 方案 C：Fork + 魔改（不推荐）
- **原因**：维护成本高，需跟进上游更新

---

## 🛠️ 方案 A：手动配置步骤

### 步骤 1：备份配置

```bash
cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.bak
```

### 步骤 2：编辑配置文件

打开 `~/.openclaw/openclaw.json`，找到 `channels.telegram` 节点，修改为：

```json
{
  "channels": {
    "telegram": {
      "enabled": true,
      "defaultAccount": "default",
      "accounts": {
        "default": {
          "botToken": "YOUR_BOT_TOKEN_1",
          "allowFrom": ["YOUR_USER_ID_1"],
          "enabled": true
        },
        "bot2": {
          "botToken": "YOUR_BOT_TOKEN_2",
          "allowFrom": ["YOUR_USER_ID_2"],
          "enabled": true
        }
      }
    }
  }
}
```

### 步骤 3：重启 Gateway

```bash
# 通过 ClawX 重启
# 或通过命令行
openclaw gateway restart
```

---

## 🤖 自动化脚本（可选）

### 选项 1：Node.js 脚本

**Prompt 模板**：
```
请帮我写一个 Node.js 脚本，用于读取和修改 macOS 下的 ~/.openclaw/openclaw.json 配置文件。

需求如下：
* 解析 JSON，定位到 channels.telegram 节点。
* 如果不存在 accounts 对象，请创建它。
* 在 accounts 中注入多机器人配置：保留原有的 default 账号，并新增一个名为 bot2 的账号结构（包含 botToken, allowFrom, enabled: true 等字段）。
* 在写入文件前，先将原有的 openclaw.json 备份为 openclaw.json.bak。
* 使用原生的 fs 模块，并保持 JSON 的格式化缩进。
```

### 选项 2：Bash + jq 脚本

**Prompt 模板**：
```
请生成一段适用于 macOS 终端的 Bash 脚本。
目标：修改 ~/.openclaw/openclaw.json 以支持 Telegram 多机器人。

具体步骤：
* 检查系统是否安装了 jq，如果没有请提示 brew install jq。
* 备份原配置。
* 使用 jq 命令更新 JSON 文件，在 .channels.telegram 下挂载完整的 accounts 对象（包含 default 和 bot2 两个配置块）。
* 直接输出可以在终端无脑粘贴执行的代码，不需要过多解释。
```

### 选项 3：纯 JSON 结构（最快）

**Prompt 模板**：
```
我正在配置 ClawX 的多机器人（基于 channel-config.ts 逻辑）。请直接输出一段合法的 JSON 代码块，表示 channels 节点下的 telegram 配置。

必须包含：
* enabled: true
* defaultAccount: "default"
* accounts 对象，里面包含 default 和 bot2 两个子对象，各自带有 botToken, allowFrom 和 enabled 属性。

请只输出 JSON，不要任何多余的解释文字，方便我直接复制替换。
```

---

## 📊 配置字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `enabled` | boolean | 是否启用此频道 |
| `defaultAccount` | string | 默认账号 ID |
| `accounts` | object | 账号配置对象 |
| `botToken` | string | Telegram Bot Token（从 @BotFather 获取） |
| `allowFrom` | array | 允许的用户 ID 列表 |
| `enabled` | boolean | 是否启用此账号 |

---

## ⚠️ 注意事项

1. **去重机制**：每个 `botToken` 必须唯一，不能被多个账号使用
2. **用户 ID**：`allowFrom` 填写 Telegram 用户 ID（数字），不是用户名
3. **获取用户 ID**：可以通过 @userinfobot 获取
4. **重启生效**：修改配置后需要重启 Gateway

---

## 🔍 验证配置

### 检查配置是否正确

```bash
# 查看当前配置
cat ~/.openclaw/openclaw.json | jq '.channels.telegram'

# 检查账号列表
cat ~/.openclaw/openclaw.json | jq '.channels.telegram.accounts | keys'
```

### 测试 Bot 是否生效

1. 向 Bot 1 发送消息
2. 向 Bot 2 发送消息
3. 检查 ClawX 是否收到消息

---

## 🚀 方案 B：PR 改进 UI（长期计划）

### MVP 功能（最小可行性产品）

1. **账号切换下拉框**（P0）
   - 显示所有已配置的账号
   - 切换账号时加载对应配置

2. **新建账号按钮**（P0）
   - 输入账号 ID
   - 输入 Bot Token
   - 输入 Allowed Users

3. **删除账号按钮**（P1）
   - 删除确认提示
   - 无法删除默认账号

### 开发文件

- `src/components/channels/ChannelConfigModal.tsx` - UI 组件
- `electron/utils/channel-config.ts` - 配置逻辑
- `src/i18n/locales/zh/channels.json` - 中文翻译

### 时间线

- **Week 1-2**：实现账号切换下拉框
- **Week 3-4**：实现新建/删除账号
- **Week 5**：测试验证，提交 PR

---

## 📚 相关资源

- **ClawX 仓库**：https://github.com/ValueCell-ai/ClawX
- **配置文件位置**：`~/.openclaw/openclaw.json`
- **核心文件**：`electron/utils/channel-config.ts`
- **PR 计划**：`/tmp/clawx-pr-plan.md`

---

## 📝 使用记录

| 时间 | 操作 | 结果 |
|------|------|------|
| 2026-03-24 | 方案归档 | ✅ 已记录 |

---

**最后更新**：2026-03-24 17:39
