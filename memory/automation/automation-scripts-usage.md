# 自动化脚本使用指南

**版本**: 1.0
**更新日期**: 2026-03-25
**维护者**: OpenClaw Automation

---

## 📑 目录

1. [快速开始](#快速开始)
2. [脚本列表](#脚本列表)
3. [详细使用指南](#详细使用指南)
4. [集成到工作流](#集成到工作流)
5. [常见问题](#常见问题)
6. [高级配置](#高级配置)

---

## 🚀 快速开始

### 安装前提条件

```bash
# 1. 确保脚本目录存在
mkdir -p ~/.openclaw/scripts

# 2. 设置可执行权限（所有脚本）
chmod +x ~/.openclaw/scripts/*.sh

# 3. 创建符号链接（可选，方便全局调用）
sudo ln -s ~/.openclaw/scripts/*.sh /usr/local/bin/

# 4. 安装特定脚本依赖
# YouTube 字幕下载
pip install yt-dlp
brew install yt-dlp ffmpeg

# 代码质量检查
pip install pylint black mypy
npm install -g eslint prettier
brew install shellcheck go
```

### 快速测试

```bash
# 测试日报生成
~/.openclaw/scripts/daily-report-generator.sh

# 查看帮助
~/.openclaw/scripts/github-auto-backup.sh --help
```

---

## 📋 脚本列表

| 脚本名称 | 优先级 | 功能 | 难度 | 依赖 |
|---------|--------|------|------|------|
| github-auto-backup.sh | ⭐⭐⭐ | GitHub 仓库自动备份 | 简单 | git |
| daily-report-generator.sh | ⭐⭐⭐ | 日报自动生成 | 简单 | 无 |
| x-bookmark-monitor.sh | ⭐⭐⭐ | X 书签监控 | 中等 | Twitter API (可选) |
| youtube-subtitle-downloader.sh | ⭐⭐ | YouTube 字幕下载 | 中等 | yt-dlp, ffmpeg |
| code-quality-check.sh | ⭐⭐ | 代码质量检查 | 中等 | 各种检查工具 |

---

## 📖 详细使用指南

### 1. GitHub 自动备份脚本

**功能**: 批量备份 GitHub 仓库到本地，支持完整镜像备份

#### 基本用法

```bash
# 备份单个仓库
~/.openclaw/scripts/github-auto-backup.sh https://github.com/user/repo.git

# 批量备份多个仓库
~/.openclaw/scripts/github-auto-backup.sh \
  https://github.com/user/repo1.git \
  https://github.com/user/repo2.git \
  https://github.com/user/repo3.git
```

#### 配置选项

编辑脚本中的配置部分：

```bash
# 备份目录（默认: ~/github-backups）
BACKUP_BASE_DIR="$HOME/github-backups"

# 日志文件
LOG_FILE="$BACKUP_BASE_DIR/backup.log"
```

#### 定时备份

添加到 crontab（每天凌晨 2 点执行）：

```bash
# 编辑 crontab
crontab -e

# 添加以下行
0 2 * * * ~/.openclaw/scripts/github-auto-backup.sh https://github.com/user/repo1.git >> ~/github-backups/cron.log 2>&1
```

#### 备份内容

- ✅ 所有分支
- ✅ 所有标签
- ✅ 完整提交历史
- ✅ Git LFS 文件（如果支持）
- ✅ 备份元数据

#### 查看备份

```bash
# 列出所有备份
ls -lh ~/github-backups/

# 查看特定仓库备份信息
cat ~/github-backups/repo-name/backup_info.txt

# 查看备份日志
tail -f ~/github-backups/backup.log
```

---

### 2. 日报自动生成脚本

**功能**: 根据模板自动生成每日工作报告

#### 基本用法

```bash
# 生成标准版日报
~/.openclaw/scripts/daily-report-generator.sh

# 生成简洁版日报
~/.openclaw/scripts/daily-report-generator.sh simple

# 生成详细版日报
~/.openclaw/scripts/daily-report-generator.sh detailed
```

#### 命令选项

```bash
# 查看帮助
~/.openclaw/scripts/daily-report-generator.sh --help

# 列出所有历史日报
~/.openclaw/scripts/daily-report-generator.sh --list

# 查看今日日报
~/.openclaw/scripts/daily-report-generator.sh --view
```

#### 自定义模板

创建自定义模板：

```bash
# 创建模板目录
mkdir -p ~/.openclaw/templates

# 复制并修改模板
cp ~/.openclaw/templates/custom-template.md
```

#### 集成待办事项

创建待办事项文件：

```bash
# 创建待办文件
cat > ~/.openclaw/todo.txt << EOF
[高优先级] 完成项目A的模块开发
[中优先级] 代码审查
[低优先级] 更新文档
EOF

# 生成日报时会自动引用
~/.openclaw/scripts/daily-report-generator.sh
```

#### 定时生成

```bash
# 每天下班前 17:30 生成日报
crontab -e

# 添加以下行
30 17 * * * ~/.openclaw/scripts/daily-report-generator.sh standard
```

---

### 3. X 书签自动监控脚本

**功能**: 监控 Twitter/X 书签变化，生成差异报告

#### 基本用法

```bash
# 1. 初始化监控系统
~/.openclaw/scripts/x-bookmark-monitor.sh init

# 2. 开始监控（默认1小时检查一次）
~/.openclaw/scripts/x-bookmark-monitor.sh monitor

# 3. 自定义检查间隔（30分钟）
~/.openclaw/scripts/x-bookmark-monitor.sh monitor -i 1800

# 4. 限制运行次数（运行5次后停止）
~/.openclaw/scripts/x-bookmark-monitor.sh monitor -n 5

# 5. 生成报告
~/.openclaw/scripts/x-bookmark-monitor.sh report

# 6. 清理旧快照
~/.openclaw/scripts/x-bookmark-monitor.sh cleanup
```

#### 配置 Twitter API

为了获取真实数据，需要配置 Twitter API：

```bash
# 创建配置文件
cat > ~/.openclaw/config/twitter.conf << EOF
API_KEY="your_api_key"
API_SECRET="your_api_secret"
ACCESS_TOKEN="your_access_token"
ACCESS_SECRET="your_access_secret"
BEARER_TOKEN="your_bearer_token"
EOF

chmod 600 ~/.openclaw/config/twitter.conf
```

#### 查看监控结果

```bash
# 列出所有快照
~/.openclaw/scripts/x-bookmark-monitor.sh list-snapshots

# 列出所有差异报告
~/.openclaw/scripts/x-bookmark-monitor.sh list-reports

# 查看最新报告
cat ~/twitter-monitor/diff-reports/diff_*.md | tail -100
```

#### 后台运行

```bash
# 后台运行监控
nohup ~/.openclaw/scripts/x-bookmark-monitor.sh monitor -i 3600 > /dev/null 2>&1 &

# 查看运行状态
ps aux | grep x-bookmark-monitor

# 停止监控
pkill -f x-bookmark-monitor
```

---

### 4. YouTube 字幕批量下载脚本

**功能**: 批量下载 YouTube 视频字幕，支持多语言和格式转换

#### 安装依赖

```bash
# 安装 yt-dlp
pip install yt-dlp

# 或使用 Homebrew（macOS）
brew install yt-dlp

# 安装 ffmpeg（用于格式转换）
brew install ffmpeg
```

#### 基本用法

```bash
# 1. 检查依赖
~/.openclaw/scripts/youtube-subtitle-downloader.sh check

# 2. 创建 URL 模板
~/.openclaw/scripts/youtube-subtitle-downloader.sh template

# 3. 编辑模板文件，添加 YouTube 链接
vim ~/youtube-subtitles/urls_template.txt

# 4. 下载单个视频字幕（英文，SRT 格式）
~/.openclaw/scripts/youtube-subtitle-downloader.sh single \
  "https://www.youtube.com/watch?v=VIDEO_ID"

# 5. 下载中文字幕
~/.openclaw/scripts/youtube-subtitle-downloader.sh single \
  "https://www.youtube.com/watch?v=VIDEO_ID" zh-Hans

# 6. 批量下载
~/.openclaw/scripts/youtube-subtitle-downloader.sh batch \
  ~/youtube-subtitles/urls_template.txt

# 7. 转换字幕格式
~/.openclaw/scripts/youtube-subtitle-downloader.sh convert \
  subtitle.srt vtt
```

#### 支持的语言

| 语言代码 | 语言 |
|---------|------|
| en | 英文 |
| zh-Hans | 简体中文 |
| zh-Hant | 繁体中文 |
| ja | 日语 |
| ko | 韩语 |
| es | 西班牙语 |
| fr | 法语 |
| de | 德语 |

#### 支持的格式

| 格式 | 扩展名 | 说明 |
|------|--------|------|
| SubRip | .srt | 最常见，通用性强 |
| WebVTT | .vtt | Web 标准格式 |
| SSA/ASS | .ass | 支持样式和特效 |
| LRC | .lrc | 歌词格式 |

#### 高级用法

```bash
# 下载自动生成的字幕（如果无人工字幕）
yt-dlp --write-auto-subs --sub-lang en --skip-download "URL"

# 下载所有可用语言的字幕
yt-dlp --write-subs --sub-langs all --skip-download "URL"

# 下载字幕并转换为特定格式
yt-dlp --write-subs --sub-format srt --convert-subs vtt "URL"
```

#### 查看已下载的字幕

```bash
# 列出所有字幕文件
~/.openclaw/scripts/youtube-subtitle-downloader.sh list

# 查看下载目录
ls -lh ~/youtube-subtitles/
```

---

### 5. 代码质量检查脚本

**功能**: 自动检测项目类型并执行相应的代码质量检查

#### 安装依赖

```bash
# Shell 脚本检查
brew install shellcheck

# Python 检查
pip install pylint black mypy

# Node.js 检查
npm install -g eslint prettier

# Go 检查
brew install go
go install golang.org/x/lint/golint@latest

# Rust 检查
rustup component add clippy
```

#### 基本用法

```bash
# 检查当前目录
~/.openclaw/scripts/code-quality-check.sh

# 检查指定项目
~/.openclaw/scripts/code-quality-check.sh ~/projects/myapp

# 查看帮助
~/.openclaw/scripts/code-quality-check.sh --help
```

#### 检查项目类型

脚本会自动检测以下项目类型：

- **Node.js**: 存在 `package.json`
- **Python**: 存在 `requirements.txt`, `setup.py`, 或 `pyproject.toml`
- **Go**: 存在 `go.mod`
- **Rust**: 存在 `Cargo.toml`
- **Java**: 存在 `pom.xml` 或 `build.gradle`

#### 查看报告

```bash
# 报告保存在项目的 quality-reports/ 目录
ls -lh ~/projects/myapp/quality-reports/

# 查看汇总报告（Markdown 格式）
cat ~/projects/myapp/quality-reports/summary_*.md

# 查看特定检查报告
cat ~/projects/myapp/quality-reports/eslint_*.txt
cat ~/projects/myapp/quality-reports/pylint_*.txt
```

#### 自定义检查

编辑脚本添加自定义检查工具：

```bash
# 在相应的 check_* 函数中添加自定义命令
# 例如：添加 TypeScript 检查
check_typescript() {
    npx tsc --noEmit
}
```

#### 集成到 CI/CD

GitHub Actions 示例：

```yaml
name: Code Quality Check
on: [push, pull_request]
jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run quality check
        run: ~/.openclaw/scripts/code-quality-check.sh
```

---

## 🔧 集成到工作流

### 创建统一入口脚本

```bash
cat > ~/.openclaw/scripts/runner.sh << 'EOF'
#!/bin/bash
# 统一脚本管理工具

case "$1" in
  backup)
    ~/.openclaw/scripts/github-auto-backup.sh "${@:2}"
    ;;
  report)
    ~/.openclaw/scripts/daily-report-generator.sh "${@:2}"
    ;;
  monitor)
    ~/.openclaw/scripts/x-bookmark-monitor.sh "${@:2}"
    ;;
  subtitle)
    ~/.openclaw/scripts/youtube-subtitle-downloader.sh "${@:2}"
    ;;
  quality)
    ~/.openclaw/scripts/code-quality-check.sh "${@:2}"
    ;;
  *)
    echo "用法: $0 <command> [options]"
    echo "命令: backup, report, monitor, subtitle, quality"
    exit 1
    ;;
esac
EOF

chmod +x ~/.openclaw/scripts/runner.sh

# 使用示例
~/.openclaw/scripts/runner.sh backup https://github.com/user/repo.git
~/.openclaw/scripts/runner.sh report detailed
```

### 创建每日工作流

```bash
cat > ~/.openclaw/scripts/daily-workflow.sh << 'EOF'
#!/bin/bash
# 每日自动化工作流

DATE=$(date +"%Y-%m-%d")
LOG="$HOME/.openclaw/logs/daily-$DATE.log"

echo "=== 开始每日工作流 ===" | tee -a "$LOG"
echo "时间: $(date)" | tee -a "$LOG"

# 1. 生成日报
echo "1. 生成日报..." | tee -a "$LOG"
~/.openclaw/scripts/daily-report-generator.sh standard | tee -a "$LOG"

# 2. GitHub 备份（如果有配置）
echo "2. GitHub 备份..." | tee -a "$LOG"
# ~/.openclaw/scripts/github-auto-backup.sh ... | tee -a "$LOG"

# 3. 代码质量检查（如果在项目目录）
if [ -f "package.json" ] || [ -f "requirements.txt" ]; then
    echo "3. 代码质量检查..." | tee -a "$LOG"
    ~/.openclaw/scripts/code-quality-check.sh . | tee -a "$LOG"
fi

echo "=== 每日工作流完成 ===" | tee -a "$LOG"
EOF

chmod +x ~/.openclaw/scripts/daily-workflow.sh

# 添加到 crontab
# 0 9 * * * ~/.openclaw/scripts/daily-workflow.sh
```

---

## ❓ 常见问题

### Q1: 脚本没有执行权限？

```bash
chmod +x ~/.openclaw/scripts/*.sh
```

### Q2: 找不到命令？

```bash
# 使用完整路径
~/.openclaw/scripts/script-name.sh

# 或添加到 PATH
export PATH="$HOME/.openclaw/scripts:$PATH"
echo 'export PATH="$HOME/.openclaw/scripts:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### Q3: 如何查看日志？

```bash
# GitHub 备份日志
tail -f ~/github-backups/backup.log

# 日报生成日志
tail -f ~/daily-reports/generation.log

# X 书签监控日志
tail -f ~/twitter-monitor/monitor.log

# YouTube 字幕下载日志
tail -f ~/youtube-subtitles/download.log

# 代码质量检查日志
tail -f ~/projects/myapp/quality-reports/check.log
```

### Q4: 如何停止后台运行的脚本？

```bash
# 查找进程
ps aux | grep script-name

# 停止进程
kill <PID>

# 或使用 pkill
pkill -f script-name
```

### Q5: 定时任务不执行？

```bash
# 查看 cron 日志
log show --predicate 'process == "cron"' --last 1h

# 检查 crontab 语法
crontab -l | crontab -

# 确保使用完整路径
which script-name  # 获取完整路径
```

---

## 🔐 高级配置

### 环境变量配置

创建 `~/.openclaw/config/env`：

```bash
# GitHub 配置
GITHUB_BACKUP_DIR="$HOME/github-backups"
GITHUB_TOKEN="your_token"

# Twitter 配置
TWITTER_API_KEY="your_api_key"
TWITTER_API_SECRET="your_api_secret"

# YouTube 配置
YOUTUBE_DOWNLOAD_DIR="$HOME/youtube-subtitles"
YOUTUBE_DEFAULT_LANG="en"
YOUTUBE_DEFAULT_FORMAT="srt"

# 报告配置
DAILY_REPORT_DIR="$HOME/daily-reports"
DAILY_REPORT_TEMPLATE="standard"

# 日志配置
LOG_LEVEL="INFO"
LOG_RETENTION_DAYS=7
```

加载配置：

```bash
source ~/.openclaw/config/env
```

### 配置文件支持

为每个脚本创建配置文件：

```bash
# GitHub 备份配置
cat > ~/.openclaw/config/backup.conf << EOF
REPOS=(
  "https://github.com/user/repo1.git"
  "https://github.com/user/repo2.git"
)
BACKUP_DIR="$HOME/github-backups"
RETENTION_DAYS=7
EOF

# 监控配置
cat > ~/.openclaw/config/monitor.conf << EOF
CHECK_INTERVAL=3600
MAX_SNAPHTOS=100
NOTIFICATION_ENABLED=true
NOTIFICATION_EMAIL="your@email.com"
EOF
```

---

## 📞 获取帮助

每个脚本都支持 `--help` 选项：

```bash
~/.openclaw/scripts/github-auto-backup.sh --help
~/.openclaw/scripts/daily-report-generator.sh --help
~/.openclaw/scripts/x-bookmark-monitor.sh --help
~/.openclaw/scripts/youtube-subtitle-downloader.sh --help
~/.openclaw/scripts/code-quality-check.sh --help
```

---

## 📝 更新日志

### v1.0 (2026-03-25)
- ✅ 初始版本发布
- ✅ 5个核心脚本完成
- ✅ 完整文档编写
- ✅ 使用指南提供

---

**文档版本**: 1.0
**最后更新**: 2026-03-25
**维护者**: OpenClaw Automation
