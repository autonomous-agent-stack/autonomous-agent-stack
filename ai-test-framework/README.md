# GitHub Actions CI/CD 最佳实践指南

这是一个完整的 GitHub Actions CI/CD 工作流示例，展示了企业级自动化部署的最佳实践。

## 📋 目录

- [概览](#概览)
- [工作流文件](#工作流文件)
- [关键特性](#关键特性)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [最佳实践](#最佳实践)
- [故障排查](#故障排查)

## 🎯 概览

本项目包含 5 个完整的 GitHub Actions 工作流：

1. **CI (持续集成)** - 代码质量、测试、构建
2. **CD (持续部署)** - 多环境部署自动化
3. **监控** - 应用健康监控、性能追踪
4. **安全** - 安全扫描、合规检查
5. **发布** - 版本发布、回滚

## 📁 工作流文件

### 1. CI 工作流 (`.github/workflows/ci.yml`)

**触发条件**: Push to main/develop, Pull Requests

**包含的 Job**:
- **Lint**: 代码质量检查（ESLint、Prettier、TypeScript）
- **Security Scan**: 静态安全扫描（Trivy、npm audit）
- **Test**: 矩阵测试（多 Node.js 版本、多测试套件）
- **Build**: 矩阵构建（多操作系统）
- **Performance**: Lighthouse CI 性能测试
- **Docker**: Docker 镜像构建和安全扫描

**矩阵策略**:
```yaml
strategy:
  matrix:
    node: [18, 20, 21]
    os: [ubuntu-latest, macos-latest, windows-latest]
```

### 2. CD 工作流 (`.github/workflows/cd.yml`)

**触发条件**: Push to main, Manual dispatch

**环境**:
- **Staging**: 自动部署
- **Production**: 需要手动批准

**部署步骤**:
1. 运行测试
2. 构建 Docker 镜像
3. 推送到容器注册表
4. 部署到 ECS
5. 烟雾测试
6. 通知团队

### 3. 监控工作流 (`.github/workflows/monitoring.yml`)

**触发条件**: 定时任务（每小时）、手动触发

**监控项目**:
- 应用健康检查
- 性能监控（Lighthouse）
- 错误追踪
- 依赖项监控
- API 性能测试（k6）
- 日志分析
- 正常运行时间监控

### 4. 安全工作流 (`.github/workflows/security.yml`)

**触发条件**: Push、PR、定时（每天）、手动

**安全检查**:
- **SAST**: CodeQL、Semgrep、njsscan
- **SCA**: npm audit、Snyk、OWASP Dependency Check
- **容器安全**: Trivy、Grype
- **IaC 安全**: tfsec、Checkov、Kubesec
- **DAST**: OWASP ZAP、Nuclei
- **密钥检测**: TruffleHog、Gitleaks

### 5. 发布工作流 (`.github/workflows/release.yml`)

**触发条件**: Git tags (v*)

**发布流程**:
1. 语义化版本控制
2. 构建多平台二进制文件
3. 构建多架构 Docker 镜像
4. 创建 GitHub Release
5. 部署到生产环境
6. 发布后监控
7. 自动回滚（失败时）

## ✨ 关键特性

### 1. 矩阵构建与测试

```yaml
strategy:
  fail-fast: false
  matrix:
    node: [18, 20, 21]
    os: [ubuntu-latest, macos-latest, windows-latest]
    test-suite: [unit, integration]
```

**优势**:
- 并行执行，节省时间
- 覆盖多个 Node.js 版本
- 跨平台兼容性测试
- 测试隔离

### 2. 多环境部署

```yaml
deploy-staging:
  environment:
    name: staging
    url: https://staging.example.com

deploy-production:
  environment:
    name: production
    url: https://example.com
```

**环境保护规则**:
- 生产环境需要手动审批
- 自动化烟雾测试
- 健康检查验证
- 自动回滚机制

### 3. 安全扫描集成

**多层安全防护**:
- SAST（静态应用安全测试）
- SCA（软件成分分析）
- 容器安全扫描
- DAST（动态应用安全测试）
- 密钥泄露检测
- IaC 安全检查

**结果上传到 GitHub Security**:
```yaml
- uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: 'trivy-results.sarif'
```

### 4. 性能监控

**Lighthouse CI**:
- 自动化性能测试
- 性能预算检查
- PR 评论显示结果
- 性能趋势追踪

**k6 负载测试**:
- 模拟真实用户流量
- SLA 合规性检查
- 自动扩缩容触发

### 5. Docker 多架构构建

```yaml
platforms: linux/amd64,linux/arm64,linux/arm/v7
```

**支持架构**:
- AMD64 (x86_64)
- ARM64 (Apple Silicon, ARM 服务器)
- ARM v7 (Raspberry Pi)

## 🚀 快速开始

### 前置要求

1. GitHub 仓库
2. AWS 账户（ECS、ECR、CloudWatch）
3. 容器注册表访问（GitHub Container Registry 或 Docker Hub）
4. 必要的 Secrets 配置

### 必需的 Secrets

在 GitHub 仓库设置中添加以下 Secrets:

```bash
# AWS
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key

# Slack
SLACK_WEBHOOK=your_slack_webhook_url

# Codecov
CODECOV_TOKEN=your_codecov_token

# Snyk
SNYK_TOKEN=your_snyk_token

# Sentry
SENTRY_AUTH_TOKEN=your_sentry_token

# Feature Flags
FEATURE_FLAG_TOKEN=your_feature_flag_token

# Incident Management
INCIDENT_TOKEN=your_incident_token
```

### 安装步骤

1. **复制工作流文件到你的仓库**:
```bash
mkdir -p .github/workflows
cp ci.yml .github/workflows/
cp cd.yml .github/workflows/
cp monitoring.yml .github/workflows/
cp security.yml .github/workflows/
cp release.yml .github/workflows/
```

2. **配置 package.json**:
```json
{
  "scripts": {
    "lint": "eslint src/",
    "format:check": "prettier --check src/",
    "type-check": "tsc --noEmit",
    "test": "jest",
    "test:unit": "jest --testPathPattern=unit",
    "test:integration": "jest --testPathPattern=integration",
    "test:coverage": "jest --coverage",
    "test:smoke": "jest --testPathPattern=smoke",
    "test:synthetic": "jest --testPathPattern=synthetic",
    "build": "tsc && webpack --mode production"
  }
}
```

3. **配置环境保护规则**:
   - 进入 GitHub 仓库 Settings > Environments
   - 创建 `staging` 和 `production` 环境
   - 为 production 环境添加保护规则（需要审批）

4. **推送代码**:
```bash
git add .github/workflows/
git commit -m "Add CI/CD workflows"
git push origin main
```

## ⚙️ 配置说明

### 自定义环境变量

在工作流文件中修改 `env` 部分:

```yaml
env:
  NODE_VERSION: '20'
  PYTHON_VERSION: '3.11'
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}
```

### 自定义矩阵

根据项目需求调整测试矩阵:

```yaml
strategy:
  matrix:
    node: [18, 20, 21]
    os: [ubuntu-latest]
    database: [postgresql, mysql, mongodb]
```

### 自定义性能预算

编辑 `.github/lighthouse-budgets.json`:

```json
{
  "budgets": [
    {
      "path": "/*",
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

### 自定义负载测试

编辑 `tests/performance/api-load-test.js`:

```javascript
export const options = {
  stages: [
    { duration: '1m', target: 10 },
    { duration: '3m', target: 50 },
    { duration: '5m', target: 100 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],
    http_req_failed: ['rate<0.01'],
  },
};
```

## 🎯 最佳实践

### 1. 缓存依赖

```yaml
- uses: actions/setup-node@v4
  with:
    node-version: '20'
    cache: 'npm'
```

**优势**:
- 减少 CI 时间
- 降低网络带宽
- 提高构建稳定性

### 2. 使用 Artifact 缓存

```yaml
- name: Build Docker image
  uses: docker/build-push-action@v5
  with:
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

### 3. 并行化任务

```yaml
jobs:
  test:
    strategy:
      matrix:
        node: [18, 20, 21]
  lint:
    # ...
  security:
    # ...
```

**并行执行可以显著减少总运行时间**

### 4. 条件执行

```yaml
- name: Deploy to production
  if: github.ref == 'refs/heads/main'
  run: |
    # ...
```

### 5. 失败时不停止

```yaml
- name: Run npm audit
  run: npm audit --audit-level=moderate
  continue-on-error: true
```

### 6. 使用 composite actions

创建可重用的工作流步骤:

```yaml
# .github/actions/setup/action.yml
name: 'Setup Build Environment'
runs:
  using: 'composite'
  steps:
    - uses: actions/setup-node@v4
      with:
        node-version: '20'
        cache: 'npm'
```

使用:
```yaml
- uses: ./.github/actions/setup
```

### 7. 监控工作流性能

使用 `actions/run-waypoint` 查看工作流性能趋势

### 8. 安全最佳实践

- ✅ 使用 GitHub Secrets 存储敏感信息
- ✅ 使用 OIDC 进行 AWS 认证（而非长期密钥）
- ✅ 定期更新 Actions 版本
- ✅ 限制 Actions 权限
- ✅ 审计第三方 Actions

```yaml
permissions:
  contents: read
  issues: read
  pull-requests: read
```

## 🔧 故障排查

### 常见问题

#### 1. Docker 构建失败

**问题**: Docker 构建超时或内存不足

**解决方案**:
```yaml
- name: Build Docker image
  uses: docker/build-push-action@v5
  with:
    build-args: |
      BUILDKIT_INLINE_CACHE=1
```

#### 2. 测试矩阵失败

**问题**: 特定 Node.js 版本测试失败

**解决方案**:
```yaml
strategy:
  fail-fast: false  # 不在第一个失败时停止
  matrix:
    node: [18, 20, 21]
```

#### 3. 安全扫描误报

**问题**: Trivy 或 Snyk 报告误报

**解决方案**:
- 添加例外规则
- 使用 `--severity-threshold` 过滤
- 更新依赖到最新版本

#### 4. 部署回滚

**问题**: 生产部署失败需要回滚

**解决方案**:
```yaml
- name: Rollback ECS service
  if: failure()
  run: |
    aws ecs update-service --cluster myapp-production \
      --service myapp-service \
      --task-definition $PREV_TASK_DEF
```

### 调试技巧

#### 启用调试日志

```yaml
- name: Run tests
  run: npm test
  env:
    ACTIONS_STEP_DEBUG: true
    ACTIONS_RUNNER_DEBUG: true
```

#### 使用 tmate 进行交互式调试

```yaml
- name: Setup tmate session
  if: failure()
  uses: mxschmitt/action-tmate@v3
  timeout-minutes: 30
```

#### 查看工作流日志

1. 进入 GitHub Actions
2. 点击失败的工作流运行
3. 展开失败的步骤查看详细日志
4. 下载日志文件进行离线分析

## 📚 参考资源

- [GitHub Actions 官方文档](https://docs.github.com/en/actions)
- [GitHub Actions 安全最佳实践](https://docs.github.com/en/actions/security-guides)
- [Docker Build Push Action](https://github.com/docker/build-push-action)
- [Lighthouse CI](https://github.com/GoogleChrome/lighthouse-ci)
- [k6 负载测试](https://k6.io/docs/)
- [OWASP ZAP](https://www.zaproxy.org/docs/docker/)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

---

**注意**: 本示例仅供参考，实际使用时请根据项目需求进行调整。
