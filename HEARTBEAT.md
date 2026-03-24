# HEARTBEAT.md

## 寏期检查任务

- [x] 检查 PR #51165 状态 ✅ 已完成（2026-03-22 08:40）
  - 状态：OPEN（无变化）
  - 更新时间： 2026-03-20 19:01:11Z
  - 链接: https://github.com/openclaw/openclaw/pull/51165
  - 备注： 继续监控

- [ ] X 书签增量读取（每次心跳）
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
  - **最新视频**（2026-03-24 17:53）:
    - 标题: 【人工智能】持续自我提升式AI | 斯坦福杨紫童博士答辩
    - 链接: https://youtu.be/aKG7_3bkrvg
    - 主题: SBP、实体图、模型自举、算法演化、自动化AI研究员
    - 字幕: 无可用字幕

- [ ] 知识库维护（每日）
  - 检查热点资料是否需要降级
  - 确认新资料已归档
  - 更新研究进度

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

## Memory Backup (每6小时)
- Run: `~/.openclaw/scripts/backup-memory.sh`
- Backup to: https://github.com/srxly888-creator/openclaw-memory
- Only backup if there are changes

## 自动备份 (每周)
- 运行: `~/.openclaw/scripts/backup-memory.sh`
- 备份内容：AGENTS.md, SOUL.md, MEMORY.md, memory/*, self-improving/*
- 推送到 GitHub: srxly888-creator/openclaw-memory

## MSA 开源监控 (每6小时)
- 论文：MSA (Memory Sparse Attention)
- 团队: EverMind（陈天桥）
- 监控方式:
  1. GitHub 搜索 "MSA evermind" "memory sparse attention"
  2. Twitter 关注 @EverMind @elliotchen100
  3. arXiv 论文引用追踪
- 触发条件：代码开源或模型发布时立即通知用户
- 检查频率： 每 6 小时（heartbeat)

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

## 白天决策提醒（2026-03-24）

### 🔴 高优先级（08:00-12:00 询问）
1. **knowledge-vault 公开评估** ⏰
   - 是否将 https://github.com/srxly888-creator/knowledge-vault 设置为公开？
   - 需要检查敏感信息
   - 决策截止: 2026-03-25 12:00

2. **GLM-5 技术集成路径选择** ⏰
   - A. 魔改 claude-cookbooks-zh（1-2 天）
   - B. autoresearch + GLM-5 集成（2-3 天）
   - C. 不写代码的 Vibe 操作（3-5 天）
   - 决策截止: 2026-03-25 20:00

### 🟡 中优先级（14:00-18:00 询问）
4. **Docker 安装决策**
   - 是否安装 Docker（用于 One-API）？
   - 或继续使用 LiteLLM Proxy？

5. **多 Agent 系统下一步**
   - 是否安装 LiteLLM？
   - 是否添加真实 Skill？
   - 是否集成到 OpenClaw？

### 🟢 低优先级（20:00-22:00 询问）
6. **OpenClaw Agent Forge 推广**
7. **YouTube 字幕下载**（40 个新视频）
8. **X 书签深度分析**（58 个书签）

**详细清单**: `memory/decisions-pending-2026-03-24.md`

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
