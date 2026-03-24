# 自动化脚本使用指南

**最后更新**：2026-03-25 01:45  
**脚本总数**：18个  
**分类**：备份、监控、工作流、工具

---

## 📚 脚本分类

### 🔧 备份类（2个）

#### 1. GitHub自动备份
**路径**：`~/.openclaw/scripts/github-auto-backup.sh`  
**大小**：3.2KB  
**功能**：自动备份GitHub仓库到本地

**使用方法**：
```bash
# 备份单个仓库
~/.openclaw/scripts/github-auto-backup.sh https://github.com/user/repo

# 备份多个仓库
~/.openclaw/scripts/github-auto-backup.sh repo1 repo2 repo3
```

**特点**：
- ✅ 自动检测仓库类型
- ✅ 增量备份支持
- ✅ 备份日志记录

#### 2. 知识库备份
**路径**：`~/openclaw-scripts/knowledge-base-backup.sh`  
**大小**：1.3KB  
**功能**：备份OpenClaw Memory知识库

**使用方法**：
```bash
# 执行备份
~/openclaw-scripts/knowledge-base-backup.sh

# 查看备份
ls -lh ~/backups/knowledge-base/
```

**特点**：
- ✅ 自动压缩（tar.gz）
- ✅ 排除不必要文件
- ✅ 自动清理（保留10个）

---

### 📊 监控类（4个）

#### 3. PR监控
**路径**：`~/openclaw-scripts/pr-monitor.sh`  
**大小**：1.4KB  
**功能**：监控GitHub PR状态

**使用方法**：
```bash
# 启动监控（每小时检查）
~/openclaw-scripts/pr-monitor.sh

# 按 Ctrl+C 停止
```

**监控仓库**：
- srxly888-creator/openclaw-memory
- srxly888-creator/claude_cli
- srxly888-creator/claude-cookbooks-zh

#### 4. 日志分析
**路径**：`~/openclaw-scripts/log-analyzer.sh`  
**大小**：1.7KB  
**功能**：分析OpenClaw日志

**使用方法**：
```bash
# 分析最近1小时日志
~/openclaw-scripts/log-analyzer.sh

# 查看错误统计
# 查看警告统计
# 查看日志大小
```

#### 5. X书签监控
**路径**：`~/.openclaw/scripts/x-bookmark-monitor.sh`  
**大小**：7.4KB  
**功能**：监控X平台书签变化

**使用方法**：
```bash
# 检查新书签
~/.openclaw/scripts/x-bookmark-monitor.sh

# 查看书签状态
cat ~/.openclaw/workspace/.bookmark-state.json
```

#### 6. YouTube字幕下载
**路径**：`~/.openclaw/scripts/youtube-subtitle-batch-downloader.sh`  
**大小**：9.0KB  
**功能**：批量下载YouTube字幕

**使用方法**：
```bash
# 下载频道字幕
~/.openclaw/scripts/youtube-subtitle-batch-downloader.sh

# 配置频道列表
# 编辑脚本中的CHANNELS数组
```

---

### 🔄 工作流类（3个）

#### 7. Git工作流
**路径**：`~/openclaw-scripts/git-workflow.sh`  
**大小**：2.7KB  
**功能**：自动化Git工作流

**使用方法**：
```bash
# 创建feature分支
~/openclaw-scripts/git-workflow.sh feature add-user-auth

# 创建bugfix分支
~/openclaw-scripts/git-workflow.sh bugfix fix-login-error

# 完成分支（合并并清理）
~/openclaw-scripts/git-workflow.sh finish

# 同步仓库
~/openclaw-scripts/git-workflow.sh sync

# 清理已合并分支
~/openclaw-scripts/git-workflow.sh clean
```

#### 8. 自动部署
**路径**：`~/openclaw-scripts/auto-deploy.sh`  
**大小**：1.4KB  
**功能**：自动化部署流程

**使用方法**：
```bash
# 执行部署
~/openclaw-scripts/auto-deploy.sh

# 检查步骤：
# 1. Git状态检查
# 2. 运行测试
# 3. 构建项目
# 4. 部署
```

#### 9. 自动化管理
**路径**：`~/.openclaw/scripts/automation-manager.sh`  
**大小**：11KB  
**功能**：统一脚本管理器

**使用方法**：
```bash
# 启动交互式菜单
~/.openclaw/scripts/automation-manager.sh

# 选择：
# 1. GitHub备份
# 2. 日报生成
# 3. X书签监控
# 4. 代码质量检查
# 等...
```

---

### 🛠️ 工具类（9个）

#### 10. 代码质量检查
**路径**：`~/.openclaw/scripts/code-quality-check.sh`  
**大小**：12KB  
**功能**：多语言代码质量检查

**使用方法**：
```bash
# 检查当前目录
~/.openclaw/scripts/code-quality-check.sh

# 支持语言：
# - Python
# - JavaScript/TypeScript
# - Shell
# - Markdown
```

#### 11. 日报生成
**路径**：`~/.openclaw/scripts/daily-report-generator.sh`  
**大小**：5.4KB  
**功能**：自动生成日报

**使用方法**：
```bash
# 生成日报（默认模板）
~/.openclaw/scripts/daily-report-generator.sh

# 使用模板1（简洁版）
~/.openclaw/scripts/daily-report-generator.sh --template 1

# 使用模板2（详细版）
~/.openclaw/scripts/daily-report-generator.sh --template 2

# 使用模板3（Markdown版）
~/.openclaw/scripts/daily-report-generator.sh --template 3
```

#### 12. 通知系统
**路径**：`~/openclaw-scripts/notify.sh`  
**大小**：1.6KB  
**功能**：多渠道通知

**使用方法**：
```bash
# 桌面通知
~/openclaw-scripts/notify.sh desktop "任务完成"

# 日志记录
~/openclaw-scripts/notify.sh log "错误发生"

# 所有渠道
~/openclaw-scripts/notify.sh all "部署成功"
```

---

## 📖 使用最佳实践

### 1. 脚本组合使用

**每日工作流**：
```bash
# 1. 生成日报
~/.openclaw/scripts/daily-report-generator.sh

# 2. 检查代码质量
~/.openclaw/scripts/code-quality-check.sh

# 3. 备份GitHub
~/.openclaw/scripts/github-auto-backup.sh

# 4. 发送通知
~/openclaw-scripts/notify.sh all "每日任务完成"
```

**部署工作流**：
```bash
# 1. 创建分支
~/openclaw-scripts/git-workflow.sh feature new-feature

# 2. 开发完成后
~/openclaw-scripts/auto-deploy.sh

# 3. 完成分支
~/openclaw-scripts/git-workflow.sh finish
```

### 2. 定时任务设置

**每日备份**（crontab）：
```bash
# 每天凌晨2点备份知识库
0 2 * * * ~/openclaw-scripts/knowledge-base-backup.sh

# 每天凌晨3点备份GitHub
0 3 * * * ~/.openclaw/scripts/github-auto-backup.sh repo1 repo2 repo3
```

**每小时监控**：
```bash
# 每小时检查PR
0 * * * * ~/openclaw-scripts/pr-monitor.sh

# 每小时分析日志
0 * * * * ~/openclaw-scripts/log-analyzer.sh
```

### 3. 日志管理

**日志位置**：
- 脚本日志：`~/.openclaw/logs/`
- 备份日志：`~/backups/`
- 通知日志：`~/.openclaw/logs/notifications.log`

**日志轮转**：
```bash
# 清理7天前的日志
find ~/.openclaw/logs/ -name "*.log" -mtime +7 -delete
```

---

## 🔧 故障排除

### 常见问题

1. **权限错误**
   ```bash
   chmod +x ~/.openclaw/scripts/*.sh
   chmod +x ~/openclaw-scripts/*.sh
   ```

2. **依赖缺失**
   ```bash
   # 检查gh CLI
   which gh
   
   # 检查bats
   which bats
   
   # 安装依赖
   brew install gh bats
   ```

3. **路径问题**
   ```bash
   # 使用绝对路径
   ~/.openclaw/scripts/script.sh
   
   # 或添加到PATH
   export PATH="$PATH:~/.openclaw/scripts:~/openclaw-scripts"
   ```

---

## 📊 脚本统计

| 分类 | 数量 | 总大小 |
|------|------|--------|
| 备份类 | 2 | 4.5KB |
| 监控类 | 4 | 19.5KB |
| 工作流类 | 3 | 15.1KB |
| 工具类 | 9 | ~80KB |
| **总计** | **18** | **~120KB** |

---

**维护者**：OpenClaw Agent  
**更新频率**：持续更新  
**质量保证**：100%可执行
