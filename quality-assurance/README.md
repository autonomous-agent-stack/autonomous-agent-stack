# 质量保证

> 代码质量、测试策略和最佳实践

---

## 📋 目录

- [质量标准](#质量标准)
- [测试策略](#测试策略)
- [代码审查](#代码审查)
- [持续集成](#持续集成)

---

## 🎯 质量标准

### 1. 代码质量指标

| 指标 | 目标 | 度量方式 |
|------|------|---------|
| **代码覆盖率** | > 80% | Jest/Vitest |
| **代码复杂度** | < 15 | ESLint/SonarQube |
| **代码重复率** | < 5% | PMD/CPD |
| **技术债务** | < 5 小时 | SonarQube |
| **文档覆盖率** | > 90% | JSDoc/TSDoc |

### 2. 性能指标

| 指标 | 目标 | 度量方式 |
|------|------|---------|
| **响应时间** | < 500ms | Lighthouse |
| **吞吐量** | > 1000 req/s | Apache Bench |
| **错误率** | < 0.1% | Prometheus |
| **可用性** | > 99.9% | Uptime Monitor |

---

## 🧪 测试策略

### 1. 测试金字塔

```
        ┌───────┐
        │  E2E  │  10%
        ├───────┤
        │集成测试│  20%
        ├───────┤
        │单元测试│  70%
        └───────┘
```

### 2. 单元测试

**最佳实践**:
```typescript
// ✅ 好的测试
describe('Calculator', () => {
  it('should add two numbers correctly', () => {
    const calc = new Calculator();
    expect(calc.add(2, 3)).toBe(5);
  });
  
  it('should handle negative numbers', () => {
    const calc = new Calculator();
    expect(calc.add(-1, -2)).toBe(-3);
  });
  
  it('should throw error for invalid input', () => {
    const calc = new Calculator();
    expect(() => calc.add(NaN, 1)).toThrow();
  });
});
```

**覆盖率配置**:
```json
// jest.config.json
{
  "coverageThreshold": {
    "global": {
      "branches": 80,
      "functions": 80,
      "lines": 80,
      "statements": 80
    }
  }
}
```

### 3. 集成测试

**API 测试**:
```typescript
import request from 'supertest';
import app from '../app';

describe('API Integration Tests', () => {
  it('POST /api/users should create user', async () => {
    const response = await request(app)
      .post('/api/users')
      .send({ name: 'Alice', email: 'alice@example.com' })
      .expect(201);
    
    expect(response.body).toHaveProperty('id');
    expect(response.body.name).toBe('Alice');
  });
});
```

### 4. E2E 测试

**Playwright 示例**:
```typescript
import { test, expect } from '@playwright/test';

test('user can login', async ({ page }) => {
  await page.goto('https://example.com/login');
  
  await page.fill('#email', 'user@example.com');
  await page.fill('#password', 'password123');
  await page.click('#login-button');
  
  await expect(page).toHaveURL('https://example.com/dashboard');
  await expect(page.locator('h1')).toContainText('Welcome');
});
```

---

## 👀 代码审查

### 1. 审查清单

**功能**:
- [ ] 代码是否实现需求？
- [ ] 边界条件是否处理？
- [ ] 错误处理是否完整？

**性能**:
- [ ] 是否有性能问题？
- [ ] 数据库查询是否优化？
- [ ] 是否有内存泄漏？

**安全**:
- [ ] 输入是否验证？
- [ ] SQL 注入防护？
- [ ] XSS 防护？

**可维护性**:
- [ ] 代码是否易读？
- [ ] 命名是否清晰？
- [ ] 是否有注释？

### 2. 自动化审查工具

```yaml
# .github/workflows/code-review.yml
name: Code Review

on: [pull_request]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      # ESLint
      - name: Run ESLint
        run: npm run lint
      
      # Prettier
      - name: Check Formatting
        run: npm run format:check
      
      # SonarQube
      - name: SonarQube Scan
        uses: sonarsource/sonarqube-scan-action@master
```

---

## 🔄 持续集成

### 1. CI 配置

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install Dependencies
        run: npm ci
      
      - name: Run Tests
        run: npm test -- --coverage
      
      - name: Upload Coverage
        uses: codecov/codecov-action@v3
```

### 2. 质量门禁

```yaml
# sonar-project.properties
sonar.projectKey=my-project
sonar.sources=src
sonar.tests=tests
sonar.test.inclusions=**/*.test.ts

# 质量门禁
sonar.qualitygate.wait=true
sonar.qualitygate.timeout=300
```

---

## 📊 质量报告

### 1. 代码质量报告

```bash
# 生成报告
npm run quality:report

# 输出示例
代码质量报告
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
覆盖率：    85.3%  ✅
复杂度：    12.5   ✅
重复率：    3.2%   ✅
技术债务：  4.5h   ✅
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
总体评分：  A
```

### 2. 性能报告

```bash
# Lighthouse 报告
npm run lighthouse

# 输出示例
性能报告
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
性能：      92/100  ✅
可访问性：  98/100  ✅
最佳实践：  95/100  ✅
SEO：       100/100 ✅
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
总体评分：  96/100
```

---

## 🛠️ 工具推荐

### 静态分析

| 工具 | 语言 | 特点 |
|------|------|------|
| **ESLint** | JavaScript/TypeScript | 插件丰富 |
| **Pylint** | Python | 功能全面 |
| **SonarQube** | 多语言 | 企业级 |
| **CodeClimate** | 多语言 | 云服务 |

### 测试框架

| 工具 | 语言 | 特点 |
|------|------|------|
| **Jest** | JavaScript/TypeScript | 功能全面 |
| **Vitest** | JavaScript/TypeScript | 快速 |
| **Pytest** | Python | 简洁易用 |
| **Playwright** | E2E | 跨浏览器 |

---

## 📚 学习资源

### 官方文档

- [Jest Documentation](https://jestjs.io/)
- [Playwright Documentation](https://playwright.dev/)
- [SonarQube Documentation](https://docs.sonarqube.org/)

### 最佳实践

- [Google Testing Blog](https://testing.googleblog.com/)
- [Martin Fowler on Testing](https://martinfowler.com/testing/)
- [Test Driven Development](https://www.agilealliance.org/glossary/tdd/)

---

<div align="center">
  <p>🧪 质量第一，测试驱动！</p>
</div>
