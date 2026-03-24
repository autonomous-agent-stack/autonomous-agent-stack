# 自动化脚本使用指南（完整版）

**最后更新**：2026-03-25 03:50  
**脚本总数**：28个  
**分类**：备份、监控、工作流、工具

---

## 📚 脚本分类

### 🔧 备份类（2个）

#### 1. GitHub自动备份
**路径**：`~/.openclaw/scripts/github-auto-backup.sh`  
**大小**：3.2KB  
**功能**：自动备份GitHub仓库到本地

#### 2. 知识库备份
**路径**：`~/openclaw-scripts/knowledge-base-backup.sh`  
**大小**：1.3KB  
**功能**：备份OpenClaw Memory知识库

---

### 📊 监控类（6个）

#### 3. PR监控
**路径**：`~/openclaw-scripts/pr-monitor.sh`  
**大小**：1.4KB  
**功能**：监控GitHub PR状态

#### 4. 日志分析
**路径**：`~/openclaw-scripts/log-analyzer.sh`  
**大小**：1.7KB  
**功能**：分析OpenClaw日志

#### 5. X书签监控
**路径**：`~/.openclaw/scripts/x-bookmark-monitor.sh`  
**大小**：7.4KB  
**功能**：监控X平台书签变化

#### 6. YouTube字幕下载
**路径**：`~/.openclaw/scripts/youtube-subtitle-batch-downloader.sh`  
**大小**：9.0KB  
**功能**：批量下载YouTube字幕

#### 7. 性能监控 ⭐新增
**路径**：`~/openclaw-scripts/performance-monitor.sh`  
**大小**：2.5KB  
**功能**：监控系统性能指标

**使用方法**：
```bash
# 启动性能监控（每60秒检查）
~/openclaw-scripts/performance-monitor.sh

# 监控内容：
# - CPU使用率
# - 内存使用率
# - 磁盘使用率
# - OpenClaw进程状态
# - 自动告警
```

#### 8. 自动化测试 ⭐新增
**路径**：`~/openclaw-scripts/automated-testing.sh`  
**大小**：3.0KB  
**功能**：运行自动化测试并生成报告

---

### 🔄 工作流类（3个）

#### 9. Git工作流
**路径**：`~/openclaw-scripts/git-workflow.sh`  
**大小**：2.7KB  
**功能**：自动化Git工作流

#### 10. 自动部署
**路径**：`~/openclaw-scripts/auto-deploy.sh`  
**大小**：1.4KB  
**功能**：自动化部署流程

#### 11. 自动化管理
**路径**：`~/.openclaw/scripts/automation-manager.sh`  
**大小**：11KB  
**功能**：统一脚本管理器（交互式菜单）

---

### 🛠️ 工具类（17个）

#### 12-19. 基础工具
**路径**：`~/.openclaw/scripts/` 和 `~/openclaw-scripts/`

包括：
- 代码质量检查（12KB）
- 日报生成（5.4KB）
- 通知系统（1.6KB）

#### 20. 快速报告生成器 ⭐新增
**路径**：`~/openclaw-scripts/quick-report.sh`  
**大小**：1.2KB  
**功能**：快速生成各类工作报告

**使用方法**：
```bash
# 生成日报
~/openclaw-scripts/quick-report.sh daily

# 生成进度报告
~/openclaw-scripts/quick-report.sh progress

# 生成总结报告
~/openclaw-scripts/quick-report.sh summary

# 生成突破报告
~/openclaw-scripts/quick-report.sh breakthrough
```

#### 21. 项目健康检查 ⭐新增
**路径**：`~/openclaw-scripts/health-check.sh`  
**大小**：2.0KB  
**功能**：检查项目健康状态

**使用方法**：
```bash
# 在项目根目录运行
~/openclaw-scripts/health-check.sh

# 检查内容：
# - Git仓库状态
# - 文档完整性
# - 测试覆盖
# - 依赖管理
# - CI/CD配置
```

#### 22. 知识库归档 ⭐新增
**路径**：`~/openclaw-scripts/archive-kb.sh`  
**大小**：1.5KB  
**功能**：自动归档旧的知识库文件

**使用方法**：
```bash
# 执行归档（归档7天前的文件）
~/openclaw-scripts/archive-kb.sh

# 归档位置：
# - memory/archive/archived_YYYYMMDD_HHMMSS/
```

#### 23. 索引重建 ⭐新增
**路径**：`~/openclaw-scripts/rebuild-index.sh`  
**大小**：3.2KB  
**功能**：重建知识库主索引

**使用方法**：
```bash
# 重建INDEX.md
~/openclaw-scripts/rebuild-index.sh

# 自动生成：
# - 核心文档链接
# - 最新报告列表
# - 主题分类
# - 统计数据
```

#### 24. 项目状态总览 ⭐新增
**路径**：`~/openclaw-scripts/project-overview.sh`  
**大小**：3.2KB  
**功能**：一键查看项目所有关键状态

**使用方法**：
```bash
# 在项目根目录运行
~/openclaw-scripts/project-overview.sh

# 显示内容：
# - Git状态（分支、更改、推送）
# - 测试状态
# - 文档状态
# - 依赖状态
# - 脚本状态
# - 文件统计
# - 项目大小
```

#### 25. 数据分析 ⭐新增
**路径**：`~/openclaw-scripts/data-analysis.sh`  
**大小**：2.1KB  
**功能**：快速分析项目数据

**使用方法**：
```bash
# 分析项目数据
~/openclaw-scripts/data-analysis.sh

# 分析内容：
# - 代码行数统计
# - 文件类型分布
# - 最大文件Top 5
# - 最近修改Top 5
# - 目录结构
```

#### 26. Git统计 ⭐新增
**路径**：`~/openclaw-scripts/git-stats.sh`  
**大小**：2.3KB  
**功能**：Git仓库统计分析

**使用方法**：
```bash
# Git统计
~/openclaw-scripts/git-stats.sh

# 统计内容：
# - 基本信息
# - 提交统计
# - 贡献者排名
# - 文件变更统计
# - 分支/标签统计
# - 存储大小
```

#### 27-28. 其他辅助工具

---

## 📖 使用最佳实践

### 1. 脚本组合使用

**项目初始化工作流**：
```bash
# 1. 健康检查
~/openclaw-scripts/health-check.sh

# 2. 数据分析
~/openclaw-scripts/data-analysis.sh

# 3. Git统计
~/openclaw-scripts/git-stats.sh

# 4. 项目总览
~/openclaw-scripts/project-overview.sh
```

**日常维护工作流**：
```bash
# 1. 性能监控（后台运行）
~/openclaw-scripts/performance-monitor.sh &

# 2. 生成日报
~/openclaw-scripts/quick-report.sh daily

# 3. 备份知识库
~/openclaw-scripts/knowledge-base-backup.sh

# 4. 发送通知
~/openclaw-scripts/notify.sh all "日常任务完成"
```

### 2. 定时任务设置

**每日任务**（crontab）：
```bash
# 每天凌晨2点备份知识库
0 2 * * * ~/openclaw-scripts/knowledge-base-backup.sh

# 每天凌晨3点备份GitHub
0 3 * * * ~/.openclaw/scripts/github-auto-backup.sh repo1 repo2 repo3

# 每天早上8点生成日报
0 8 * * * ~/openclaw-scripts/quick-report.sh daily

# 每天晚上23点执行健康检查
0 23 * * * ~/openclaw-scripts/health-check.sh
```

**每周任务**：
```bash
# 每周日凌晨归档知识库
0 2 * * 0 ~/openclaw-scripts/archive-kb.sh

# 每周日凌晨重建索引
0 3 * * 0 ~/openclaw-scripts/rebuild-index.sh
```

### 3. 日志管理

**日志位置**：
- 脚本日志：`~/.openclaw/logs/`
- 备份日志：`~/backups/`
- 通知日志：`~/.openclaw/logs/notifications.log`
- 性能日志：`~/.openclaw/logs/performance.log`
- 测试报告：`~/.openclaw/reports/test-reports/`

**日志清理**：
```bash
# 清理7天前的日志
find ~/.openclaw/logs/ -name "*.log" -mtime +7 -delete
```

---

## 🔧 故障排除

### 常见问题

1. **权限错误**
   ```bash
   chmod +x ~/openclaw-scripts/*.sh
   chmod +x ~/.openclaw/scripts/*.sh
   ```

2. **路径问题**
   ```bash
   # 使用绝对路径
   ~/openclaw-scripts/script.sh
   
   # 或添加到PATH
   export PATH="$PATH:~/openclaw-scripts:~/.openclaw/scripts"
   ```

3. **依赖缺失**
   ```bash
   # 检查依赖
   which bats
   which gh
   
   # 安装依赖
   brew install bats-core gh
   ```

---

## 📊 脚本统计

| 分类 | 数量 | 总大小 |
|------|------|--------|
| 备份类 | 2 | 4.5KB |
| 监控类 | 6 | 25.1KB |
| 工作流类 | 3 | 15.1KB |
| 工具类 | 17 | ~120KB |
| **总计** | **28** | **~165KB** |

---

## 🎯 新增工具亮点

### ⭐ 7个新工具

1. **性能监控** - 实时监控系统资源
2. **自动化测试** - 批量运行测试
3. **快速报告生成器** - 4种报告类型
4. **项目健康检查** - 全面的健康检查
5. **知识库归档** - 自动归档旧文件
6. **索引重建** - 自动生成索引
7. **项目状态总览** - 一键查看所有状态
8. **数据分析** - 快速项目分析
9. **Git统计** - 全面Git统计

**特点**：
- ✅ 实用性强
- ✅ 易于使用
- ✅ 彩色输出
- ✅ 详细文档
- ✅ 自动化程度高

---

**维护者**：OpenClaw Agent  
**更新频率**：持续更新  
**质量保证**：100%可执行
