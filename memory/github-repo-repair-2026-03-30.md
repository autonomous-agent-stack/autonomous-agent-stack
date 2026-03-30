# GitHub 仓库修复记录（2026-03-30 23:58）

## 🔍 发现问题

### youtube-subtitles-classified 仓库损坏
- **问题**: HEAD 指向 `.invalid` 分支
- **原因**: 可能是 Git 操作异常
- **状态**: 无法正常使用

## 🔧 修复方案

### 方案 1：重置 HEAD 到 main/master
```bash
cd /Volumes/AI_LAB/Github/youtube-subtitles-classified

# 检查现有分支
git branch -a

# 重置 HEAD
git symbolic-ref HEAD refs/heads/main

# 如果没有 main 分支，创建初始提交
git checkout -b main
echo "# YouTube Subtitles Classified" > README.md
git add README.md
git commit -m "Initial commit"
git push -u origin main
```

### 方案 2：重新克隆
```bash
# 删除损坏的仓库
rm -rf /Volumes/AI_LAB/Github/youtube-subtitles-classified

# 重新克隆
gh repo clone srxly888-creator/youtube-subtitles-classified /Volumes/AI_LAB/Github/youtube-subtitles-classified
```

## 🎯 其他待检查仓库

### 检查所有本地仓库的健康状态
```bash
for dir in /Volumes/AI_LAB/Github/*/; do
  if [ -d "$dir/.git" ]; then
    echo "=== $(basename "$dir") ==="
    git -C "$dir" status -sb 2>&1 | head -2
  fi
done
```

---

**时间**: 2026-03-30 23:58
**状态**: 🟡 发现问题，待修复
