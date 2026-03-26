# HEARTBEAT.md

> **最后更新**: 2026-03-26 01:05 GMT+8
> **知识库健康度**: 99% ⭐
> **子目录数**: 40 个

---

## 🌙 夜间监控系统（Night Watch）

**启动时间**：2026-03-26 01:04  
**监控频率**：每 5 分钟  
**监控对象**：`/Volumes/PS1008/Github/autonomous-agent-stack`

### 📋 实时报告

**报告文件**：`~/.openclaw/workspace/AutonomousAgentStack_NightWatch.md`

**查看命令**：
```bash
cat ~/.openclaw/workspace/AutonomousAgentStack_NightWatch.md
# 或
bash ~/.openclaw/scripts/night-watch-status
```

### 🔧 管理命令

| 命令 | 功能 |
|------|------|
| `bash ~/.openclaw/scripts/night-watch-start` | 启动监控 |
| `bash ~/.openclaw/scripts/night-watch-stop` | 停止监控 |
| `bash ~/.openclaw/scripts/night-watch-status` | 查看状态 |

### 📊 监控内容

- ✅ 仓库状态（分支、提交、未提交文件）
- ✅ Agent 状态（Codex/Python 进程）
- ✅ 测试状态（失败测试、覆盖率）
- ✅ 自动建议行动

### 💡 接手指南

1. **查看夜间报告**：`cat ~/.openclaw/workspace/AutonomousAgentStack_NightWatch.md`
2. **检查未提交文件**：如有，建议提交
3. **检查 Agent 状态**：确认所有任务完成
4. **检查测试结果**：修复失败测试

---

## 寏期检查任务

- [x] 检查 PR #51165 状态 ✅ 已完成（2026-03-25 07:55）
  - 状态：OPEN（无变化）
  - 更新时间： 2026-03-24 20:15:41Z（约 12 小时前）
  - 标题：feat(skills): agent-scoped policy parity + reactive snapshot refresh
  - 链接: https://github.com/openclaw/openclaw/pull/51165
  - 备注： 继续监控

- [x] X 书签增量读取 ✅ 已完成（2026-03-25 13:55）
  - 状态：无新增书签
  - 最新书签：2026-03-17（7 天前）
  - 总书签数：58
  - 备注：继续监控
  - 读取新书签（增量)
  - 分析内容（批判性）
  - 生成总结报告
  - 状态文件: `~/.openclaw/workspace/.bookmark-state.json`

- [x] YouTube 频道监控（每次心跳） ✅ 已完成
  - 频道: @bestpartners（最佳拍档）✅ **链接已修复**
  - 监控: 最新视频
  - 下载: 字幕（如有）
  - 整理: 关键内容
  - 配置: `~/.openclaw/workspace/.channel-subscriptions.json`
  - 状态: 5 个活跃频道（2026-03-24 04:52 修复）
  - **最新视频**（2026-03-25 07:55）:
    - 标题: 理科大模型 | 陈天桥 | MiroMind | MiroThinker | AI的接入权 | 碳基沙文主义 | 人类的终极意义
    - 链接: https://youtu.be/6B17RcqwnGE
    - 时长: 22:46
    - 上传: 2026-03-24
    - 主题: 陈天桥、MiroMind、MiroThinker、AI接入权、碳基沙文主义
    - 字幕: ✅ 有中文字幕
    - 数据: 701 观看，35 点赞

- [x] 知识库维护 ✅ 已完成（2026-03-25 13:55）
  - 总文件数：275（+12）
  - 子目录数：40
  - README 覆盖率：26/40（65%）
  - 缺少 README 的子目录：14 个
    - agent-development/, claude-cli-private/, configurations/
    - misc/, monitoring/, multi-agent/, open-source/
    - quality-assurance/, setup/, system-integration/
    - tools/, translation/, upstream-sync/, workflow-optimization/
  - 备注：需要补充 14 个 README

- [x] 搜索 MAS Factory 项目（每周） ✅ 已完成
  - **已 Fork**: https://github.com/srxly888-creator/MASfactory

- [x] PUA 项目fork ✅ 已完成
  - **已 Fork**: https://github.com/srxly888-creator/pua

# Keep this file empty (or with only comments) to skip heartbeat API calls.

# Add tasks below when you want the agent to check something periodically.

## Self-Improving Check
- Read `./skills/self-improving/heartbeat-rules.md`
- Use `~/self-improving/heartbeat-state.md` for last-run markers and action notes
- If no file inside `~/self-improving/` changed since the last reviewed change, return `HEARTBEAT_OK`

## AI 学习资源维护（每周)
- 检查非技术友好资源链接是否有效
- 确认新资源已归档
- 更新 `memory/non-technical-ai-resources.md`

## 非技术人员资源整理（一次性)
- **Prompt Engineering Guide**: 72k stars, 无需编程
- **Awesome ChatGPT Prompts**: 123k stars, 200+ 现成模板
- **Anthropic Academy**: 官方免费课程
- 详见: `memory/non-technical-ai-resources.md`

## Memory Backup (每6小时) ✅ 已完成（2026-03-25 23:36）
- Run: `~/.openclaw/scripts/backup-memory.sh`
- Backup to: https://github.com/srxly888-creator/openclaw-memory
- Only backup if there are changes
- **状态**: 174 个新文件（memory/ 目录），20 个未推送提交
- **Commit**: "heartbeat: 23:36 检查 - Memory 备份（174 新文件）"
- **备注**: Git push 失败（认证问题），需要手动推送

## 自动备份 (每周)
- 运行: `~/.openclaw/scripts/backup-memory.sh`
- 备份内容：AGENTS.md, SOUL.md, MEMORY.md, memory/*, self-improving/*
- 推送到 GitHub: srxly888-creator/openclaw-memory

## MSA 开源监控 (每6小时) ✅ 已完成（2026-03-26 09:22）
- 论文：MSA (Memory Sparse Attention)
- 团队: EverMind（陈天桥）
- 监控方式:
  1. GitHub 搜索 "MSA evermind" "memory sparse attention"
  2. Twitter 关注 @EverMind @elliotchen100
  3. arXiv 论文引用追踪
- 触发条件：代码开源或模型发布时立即通知用户
- 检查频率： 每 6 小时（heartbeat)
- **状态**: 🟢 **有新进展** - 发现官方 MSA 仓库
  - **新仓库**: EverMind-AI/MSA (13 stars, 1 fork)
  - **新闻报道**: 2026-03-19 多家媒体报道 100M Token 突破
  - **官方博客**: evermind.ai 发布技术文章
  - **建议**: Fork EverMind-AI/MSA 仓库
  - **详情**: memory/2026-03-26-msa-monitoring-update.md
  - 下次检查: 2026-03-26 15:22

## 仓库链接健康检查（每晚 23:00）
- **目标**: 确保所有学习仓库链接可用
- **检查内容**:
  1. GitHub 仓库是否存在
  2. README.md 链接是否正常
  3. 重要文档是否可访问
  4. Fork 的项目是否被删除
- **检查频率**: 每晚 23:00（heartbeat）
- **处理方式**:
  - 链接失效 → 立即通知用户
  - 仓库删除 → 寻找替代方案
  - 内容过时 → 标记需要更新

## 仓库描述与状态检查（每晚 23:00）
- **目标**: 确保所有仓库描述贴切、链接有效
- **检查脚本**: `~/.openclaw/scripts/check-repo-description.sh`
- **检查内容**:
  1. 仓库描述是否为空或太短
  2. Stars 数量和更新时间
  3. README.md 中的断链
  4. 仓库是否存在
- **报告位置**: `memory/repo-health-check.md`
- **处理方式**:
  - 描述不当 → 通知用户修改
  - 链接失效 → 自动修复或标记
  - 仓库异常 → 立即告警

## 仓库名称规范检查（每周）
- **目标**: 确保仓库名称清晰、专业
- **检查内容**:
  1. 名称是否符合 GitHub 命名规范
  2. 名称是否准确反映内容
  3. 名称是否易于搜索和理解
- **检查频率**: 每周一（heartbeat）

# Add tasks below when you want the agent to check something periodically.

## 已完成决策（2026-03-24）

- [x] **knowledge-vault 公开** ✅ 已完成（2026-03-24 14:11）
- [x] **GLM-5 适配发布** ✅ 已完成（2026-03-24 14:15）

## 待决策事项

### 🟡 中优先级
- **Docker 安装决策** - 是否安装 Docker（用于 One-API）？
- **多 Agent 系统下一步** - LiteLLM / Skill / OpenClaw 集成？

### 🟢 低优先级
- **OpenClaw Agent Forge 推广**
- **YouTube 字幕下载**（40 个新视频）
- **X 书签深度分析**（58 个书签）

---

## 质量改进（2026-03-22）

### **教训**
- **维护 > 创建**: 用户强调维护才是大事
- **验证胜过假设**: 永远不要假设链接正确
- **频率要够**: 每天检查而不是每周

### **改进**
- ✅ 检查频率: 每周 → **每天**
- ✅ MAS Factory 链接已修复
- ✅ 创建质量分析报告

### **检查频率调整**
- **仓库链接健康**: 每周 → **每天 23:00**
- **仓库描述检查**: 每周 → **每天 23:00**
- **仓库名称规范**: 每周（保持）

## GitHub Stars 自动更新（每天 2:00）

- **目标**: 保持 Stars 数据最新
- **实现方式**: GitHub Actions 自动更新
- **更新频率**: 每天凌晨 2:00 (UTC)
- **文件位置**: `.github/workflows/update-stars.yml`
- **数据文件**: `stars.json`
- **处理方式**:
  - 自动获取最新 Stars
  - 更新 README.md
  - 自动提交变更

**注意**: Stars 数据每天自动更新，无需手动维护
