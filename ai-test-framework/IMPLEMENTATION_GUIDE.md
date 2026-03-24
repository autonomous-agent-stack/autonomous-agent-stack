# GitHub Actions CI/CD 实施指南

本指南提供了完整的 CI/CD 实施步骤，从零开始到生产就绪。

## 📋 实施路线图

### 阶段 1: 基础设置 (1-2 天)
- [ ] 仓库初始化
- [ ] 基础 CI 工作流
- [ ] Linting 和格式化
- [ ] 单元测试

### 阶段 2: 高级 CI (2-3 天)
- [ ] 矩阵测试
- [ ] 安全扫描
- [ ] 代码覆盖率
- [ ] 性能基准测试

### 阶段 3: 持续部署 (3-5 天)
- [ ] 环境配置
- [ ] Docker 化
- [ ] 部署自动化
- [ ] 回滚机制

### 阶段 4: 监控与优化 (持续)
- [ ] 监控仪表板
- [ ] 告警配置
- [ ] 性能优化
- [ ] 持续改进

## 🚀 阶段 1: 基础设置

### 步骤 1.1: 项目初始化

```bash
# 创建项目目录结构
mkdir -p .github/workflows
mkdir -p tests/unit
mkdir -p tests/integration
mkdir -p tests/performance
mkdir -p src

# 初始化 Git 仓库（如果还没有）
git init

# 创建 .gitignore
cat > .gitignore << 'EOF'
node_modules/
dist/
coverage/
.env
.DS_Store
*.log
EOF
```

### 步骤 1.2: 配置 package.json

```bash
npm init -y

# 安装开发依赖
npm install --save-dev \
  eslint \
  prettier \
  typescript \
  @typescript-eslint/parser \
  @typescript-eslint/eslint-plugin \
  jest \
  @types/jest \
  ts-jest \
  nodemon \
  concurrently
```

更新 `package.json`:

```json
{
  "name": "myapp",
  "version": "1.0.0",
  "scripts": {
    "dev": "nodemon src/index.ts",
    "build": "tsc",
    "start": "node dist/index.js",
    "lint": "eslint src/ --ext .ts",
    "lint:fix": "eslint src/ --ext .ts --fix",
    "format": "prettier --write \"src/**/*.ts\"",
    "format:check": "prettier --check \"src/**/*.ts\"",
    "type-check": "tsc --noEmit",
    "test": "jest",
    "test:watch": "jest --watch",
    "test:coverage": "jest --coverage",
    "test:unit": "jest --testPathPattern=tests/unit",
    "test:integration": "jest --testPathPattern=tests/integration"
  }
}
```

### 步骤 1.3: 配置 ESLint

创建 `.eslintrc.js`:

```javascript
module.exports = {
  parser: '@typescript-eslint/parser',
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
  ],
  plugins: ['@typescript-eslint'],
  env: {
    node: true,
    es6: true,
  },
  rules: {
    '@typescript-eslint/explicit-function-return-type': 'warn',
    '@typescript-eslint/no-explicit-any': 'warn',
    '@typescript-eslint/no-unused-vars': 'error',
    'no-console': 'warn',
  },
};
```

### 步骤 1.4: 配置 Prettier

创建 `.prettierrc`:

```json
{
  "semi": true,
  "trailingComma": "es5",
  "singleQuote": true,
  "printWidth": 100,
  "tabWidth": 2,
  "useTabs": false
}
```

### 步骤 1.5: 配置 Jest

创建 `jest.config.js`:

```javascript
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  roots: ['<rootDir>/tests'],
  testMatch: ['**/*.test.ts'],
  collectCoverageFrom: [
    'src/**/*.ts',
    '!src/**/*.d.ts',
    '!src/index.ts',
  ],
  coverageThreshold: {
    global: {
      branches: 70,
      functions: 70,
      lines: 70,
      statements: 70,
    },
  },
};
```

### 步骤 1.6: 配置 TypeScript

创建 `tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "commonjs",
    "lib": ["ES2020"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist", "tests"]
}
```

### 步骤 1.7: 创建基础 CI 工作流

创建 `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  lint:
    name: Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - run: npm ci
      - run: npm run lint
      - run: npm run type-check

  test:
    name: Test
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - run: npm ci
      - run: npm test
      - run: npm run test:coverage

      - uses: codecov/codecov-action@v4
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
```

## 🎯 阶段 2: 高级 CI

### 步骤 2.1: 添加矩阵测试

更新 CI 工作流:

```yaml
test:
  name: Test (Node ${{ matrix.node }})
  runs-on: ubuntu-latest
  needs: lint
  strategy:
    fail-fast: false
    matrix:
      node: [18, 20, 21]
  steps:
    - uses: actions/checkout@v4

    - uses: actions/setup-node@v4
      with:
        node-version: ${{ matrix.node }}
        cache: 'npm'

    - run: npm ci
    - run: npm test
```

### 步骤 2.2: 添加安全扫描

创建 `.github/workflows/security.yml`:

```yaml
name: Security Scan

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  security:
    name: Security Scan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run npm audit
        run: npm audit --audit-level=moderate
        continue-on-error: true

      - name: Run Trivy
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'

      - uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: 'trivy-results.sarif'
```

### 步骤 2.3: 配置 CodeQL

添加到安全工作流:

```yaml
- name: Initialize CodeQL
  uses: github/codeql-action/init@v3
  with:
    languages: javascript, typescript

- name: Perform CodeQL Analysis
  uses: github/codeql-action/analyze@v3
```

### 步骤 2.4: 添加性能测试

创建性能测试文件:

```javascript
// tests/performance/app-performance.test.ts
describe('Performance Tests', () => {
  it('should respond within 100ms', async () => {
    const start = Date.now();
    // Your operation here
    const duration = Date.now() - start;
    expect(duration).toBeLessThan(100);
  });
});
```

## 🚢 阶段 3: 持续部署

### 步骤 3.1: Docker 化应用

创建 `Dockerfile`:

```dockerfile
# Multi-stage build
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm ci

# Copy source and build
COPY . .
RUN npm run build

# Production image
FROM node:20-alpine

WORKDIR /app

# Copy built files
COPY --from=builder /app/dist ./dist
COPY package*.json ./

# Install production dependencies only
RUN npm ci --only=production

# Create non-root user
RUN addgroup -g 1001 -S nodejs
RUN adduser -S nodejs -u 1001
USER nodejs

EXPOSE 3000

CMD ["node", "dist/index.js"]
```

创建 `.dockerignore`:

```
node_modules
dist
coverage
.git
.env
*.md
```

### 步骤 3.2: 创建 Kubernetes 配置

创建 `k8s/deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  labels:
    app: myapp
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: myapp
        image: ghcr.io/your-org/myapp:latest
        ports:
        - containerPort: 3000
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: myapp-service
spec:
  selector:
    app: myapp
  ports:
  - port: 80
    targetPort: 3000
  type: LoadBalancer
```

### 步骤 3.3: 创建 CD 工作流

创建 `.github/workflows/cd.yml`:

```yaml
name: CD

on:
  push:
    branches: [main]

jobs:
  deploy-staging:
    name: Deploy to Staging
    runs-on: ubuntu-latest
    environment:
      name: staging
      url: https://staging.example.com
    steps:
      - uses: actions/checkout@v4

      - name: Login to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ghcr.io/${{ github.repository }}:staging
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Deploy to Kubernetes
        run: |
          kubectl set image deployment/myapp myapp=ghcr.io/${{ github.repository }}:staging
          kubectl rollout status deployment/myapp
```

### 步骤 3.4: 配置环境保护规则

1. 进入 GitHub 仓库 Settings > Environments
2. 创建环境:
   - `staging` (无保护规则)
   - `production` (需要审批)
3. 添加保护规则:
   - Required reviewers: 指定审批人
   - Wait timer: 设置等待时间
   - Deployment branches: 限制部署分支

### 步骤 3.5: 实现健康检查

在应用中添加健康检查端点:

```typescript
// src/health.ts
import express from 'express';

export function createHealthRouter() {
  const router = express.Router();

  router.get('/health', (req, res) => {
    res.json({
      status: 'healthy',
      timestamp: new Date().toISOString(),
      uptime: process.uptime(),
    });
  });

  return router;
}
```

### 步骤 3.6: 实现回滚机制

在 CD 工作流中添加回滚步骤:

```yaml
- name: Deploy
  id: deploy
  run: |
    kubectl set image deployment/myapp myapp=$IMAGE
    kubectl rollout status deployment/myapp

- name: Rollback on failure
  if: failure()
  run: |
    kubectl rollout undo deployment/myapp
```

## 📊 阶段 4: 监控与优化

### 步骤 4.1: 配置监控

创建 `.github/workflows/monitoring.yml`:

```yaml
name: Monitoring

on:
  schedule:
    - cron: '0 * * * *'
  workflow_dispatch:

jobs:
  health-check:
    name: Health Check
    runs-on: ubuntu-latest
    steps:
      - name: Check production
        run: |
          response=$(curl -s -o /dev/null -w "%{http_code}" https://example.com/health)
          if [ $response -ne 200 ]; then
            echo "❌ Health check failed"
            exit 1
          fi
```

### 步骤 4.2: 配置告警

添加 Slack 通知:

```yaml
- name: Notify on failure
  if: failure()
  uses: 8398a7/action-slack@v3
  with:
    status: 'failure'
    text: '❌ Health check failed'
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

### 步骤 4.3: 配置性能监控

添加 Lighthouse CI:

```yaml
- name: Run Lighthouse CI
  uses: treosh/lighthouse-ci-action@v10
  with:
    urls: https://example.com
    uploadArtifacts: true
```

### 步骤 4.4: 优化 CI/CD 性能

**使用缓存**:
```yaml
- uses: actions/setup-node@v4
  with:
    node-version: '20'
    cache: 'npm'
```

**并行化任务**:
```yaml
jobs:
  lint:
    # ...
  test:
    # ...
  security:
    # ...
# 所有 job 并行运行
```

**使用 Docker 层缓存**:
```yaml
- uses: docker/build-push-action@v5
  with:
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

## ✅ 验证检查清单

### 基础 CI
- [ ] Linting 通过
- [ ] 类型检查通过
- [ ] 单元测试通过
- [ ] 代码覆盖率 > 70%

### 安全
- [ ] npm audit 无高危漏洞
- [ ] Trivy 扫描无严重问题
- [ ] CodeQL 无警告
- [ ] 密钥未泄露

### 部署
- [ ] Docker 镜像成功构建
- [ ] 容器安全扫描通过
- [ ] 部署到 staging 成功
- [ ] 健康检查通过
- [ ] 回滚机制正常

### 监控
- [ ] 应用健康检查正常
- [ ] 性能指标在 SLA 内
- [ ] 告警配置正确
- [ ] 日志收集正常

## 🔧 故障排查

### 常见问题

**Q: CI 运行太慢**
A: 启用缓存、并行化任务、减少不必要的步骤

**Q: Docker 构建失败**
A: 检查 Dockerfile、检查网络连接、使用 BuildKit

**Q: 测试偶尔失败**
A: 检查测试依赖、增加超时时间、隔离测试

**Q: 部署后应用崩溃**
A: 检查健康检查、查看日志、启用回滚

## 📚 延伸阅读

- [GitHub Actions 官方文档](https://docs.github.com/en/actions)
- [Docker 最佳实践](https://docs.docker.com/develop/dev-best-practices/)
- [Kubernetes 文档](https://kubernetes.io/docs/)
- [持续集成模式](https://www.martinfowler.com/articles/continuousIntegration.html)

---

**下一步**: 根据 [README.md](./README.md) 配置你的项目。
