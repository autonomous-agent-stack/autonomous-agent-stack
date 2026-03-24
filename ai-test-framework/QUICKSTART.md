# 🚀 快速开始指南

5 分钟内启动你的 CI/CD 工作流！

## 前置条件

✅ GitHub 仓库
✅ 基本的 Node.js 项目
✅ Docker（可选，用于容器化部署）

## 步骤 1: 复制文件（1 分钟）

```bash
# 复制工作流文件到你的项目
cd your-project
cp -r ../ai-test-framework/.github .
cp ../ai-test-framework/package.json .
cp ../ai-test-framework/.eslintrc.js .
cp ../ai-test-framework/tsconfig.json .
cp ../ai-test-framework/jest.config.js .
cp ../ai-test-framework/Dockerfile .
cp ../ai-test-framework/.dockerignore .
cp ../ai-test-framework/.gitignore .
```

## 步骤 2: 安装依赖（1 分钟）

```bash
npm install
```

## 步骤 3: 配置 GitHub Secrets（2 分钟）

1. 进入你的 GitHub 仓库
2. 点击 **Settings** > **Secrets and variables** > **Actions**
3. 点击 **New repository secret** 添加以下 Secrets:

### 必需的 Secrets

```bash
# Slack 通知（可选但推荐）
SLACK_WEBHOOK=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Codecov（可选）
CODECOV_TOKEN=your_codecov_token

# AWS（用于部署）
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key

# Snyk（可选，用于高级安全扫描）
SNYK_TOKEN=your_snyk_token
```

### 如何获取 Slack Webhook

1. 进入 Slack App: https://api.slack.com/apps
2. 创建新的 Incoming Webhooks
3. 复制 Webhook URL
4. 粘贴到 GitHub Secrets

## 步骤 4: 推送代码（1 分钟）

```bash
git add .
git commit -m "Add CI/CD workflows"
git push origin main
```

## 步骤 5: 查看运行结果

1. 进入你的 GitHub 仓库
2. 点击 **Actions** 标签页
3. 查看工作流运行状态

🎉 **恭喜！你的 CI/CD 工作流已经运行！**

## 验证工作流

### 1. CI 工作流

创建一个 Pull Request 或推送到 main 分支，CI 工作流将自动运行：

```bash
git checkout -b feature/test
git push origin feature/test
```

### 2. 安全扫描

安全扫描会在每次 Push 和 Pull Request 时自动运行。

### 3. CD 工作流

推送到 main 分支将触发部署：

```bash
git checkout main
git merge feature/test
git push origin main
```

## 常用命令

### 本地测试

```bash
# 运行 linting
npm run lint

# 运行类型检查
npm run type-check

# 运行测试
npm test

# 运行测试并生成覆盖率报告
npm run test:coverage

# 构建项目
npm run build

# 格式化代码
npm run format
```

### Docker 测试

```bash
# 构建 Docker 镜像
docker build -t myapp:latest .

# 运行容器
docker run -p 3000:3000 myapp:latest

# 健康检查
curl http://localhost:3000/health
```

## 自定义配置

### 修改 Node.js 版本

编辑 `.github/workflows/ci.yml`:

```yaml
strategy:
  matrix:
    node: [18, 20, 21]  # 修改为你需要的版本
```

### 添加环境变量

在工作流文件中添加:

```yaml
env:
  MY_VAR: "value"
```

### 自定义性能预算

编辑 `.github/lighthouse-budgets.json`:

```json
{
  "budgets": [
    {
      "timings": [
        {
          "metric": "first-contentful-paint",
          "budget": 2000
        }
      ]
    }
  ]
}
```

## 故障排查

### 问题 1: 工作流失败

**检查步骤**:
1. 查看 Actions 标签页中的详细日志
2. 检查是否所有依赖都已安装
3. 确认所有配置文件都已复制

### 问题 2: 测试失败

**解决方案**:
```bash
# 本地运行测试
npm test

# 查看详细错误
npm test -- --verbose
```

### 问题 3: Docker 构建失败

**解决方案**:
```bash
# 检查 Dockerfile 语法
docker build -t test .

# 查看构建日志
docker build --progress=plain -t test .
```

### 问题 4: 权限错误

**解决方案**:
1. 检查 GitHub Actions 权限设置
2. 进入 Settings > Actions > General
3. 确保 "Workflow permissions" 设置正确

## 下一步

现在你的基础 CI/CD 已经运行，你可以：

1. ✅ 配置环境保护规则（Settings > Environments）
2. ✅ 自定义工作流以满足项目需求
3. ✅ 添加更多测试和安全扫描
4. ✅ 配置生产部署
5. ✅ 设置监控和告警

## 需要帮助？

- 📖 查看 [README.md](./README.md) 了解详细文档
- 📝 查看 [IMPLEMENTATION_GUIDE.md](./IMPLEMENTATION_GUIDE.md) 了解实施细节
- 🔍 查看 [CICD_SUMMARY.md](./CICD_SUMMARY.md) 了解架构概览

## 成功标志

当你看到以下内容时，说明 CI/CD 已成功运行：

✅ GitHub Actions 显示绿色的 ✓
✅ 所有检查通过
✅ Docker 镜像已构建
✅ 测试覆盖率报告已生成
✅ 安全扫描已完成
✅ 代码已部署到 Staging

---

**预计时间**: 5 分钟
**难度**: ⭐⭐☆☆☆
**状态**: ✅ 准备就绪

祝你的 CI/CD 之旅顺利！ 🎉
