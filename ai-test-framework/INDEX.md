# 📚 CI/CD 框架文档索引

完整的 GitHub Actions CI/CD 最佳实践框架文档导航。

## 🚀 快速导航

### 新手入门
1. **[QUICKSTART.md](./QUICKSTART.md)** ⭐ 推荐从这里开始
   - 5 分钟快速启动指南
   - 最小化配置
   - 快速验证

### 完整文档
2. **[README.md](./README.md)** - 项目概览
   - 工作流文件说明
   - 关键特性介绍
   - 最佳实践
   - 故障排查

3. **[CICD_SUMMARY.md](./CICD_SUMMARY.md)** - 实施总结
   - 交付内容清单
   - 架构概览
   - 核心功能说明

4. **[IMPLEMENTATION_GUIDE.md](./IMPLEMENTATION_GUIDE.md)** - 实施指南
   - 4 阶段实施路线图
   - 详细步骤说明
   - 验证检查清单

## 📁 文件结构

```
ai-test-framework/
├── 📄 README.md                    # 项目主文档
├── 📄 QUICKSTART.md                # 快速开始指南
├── 📄 CICD_SUMMARY.md              # 实施总结
├── 📄 IMPLEMENTATION_GUIDE.md      # 实施指南
├── 📄 INDEX.md                     # 本文件
│
├── 📁 .github/
│   ├── 📁 workflows/               # GitHub Actions 工作流
│   │   ├── ci.yml                  # 持续集成
│   │   ├── cd.yml                  # 持续部署
│   │   ├── monitoring.yml          # 监控
│   │   ├── security.yml            # 安全扫描
│   │   └── release.yml             # 发布管理
│   │
│   ├── 📁 ISSUE_TEMPLATE/          # Issue 模板
│   │   └── security-issue.md       # 安全问题报告模板
│   │
│   ├── 📄 PULL_REQUEST_TEMPLATE.md # PR 模板
│   └── 📄 lighthouse-budgets.json  # 性能预算配置
│
├── 📁 tests/                       # 测试文件
│   └── 📁 performance/
│       └── api-load-test.js        # k6 负载测试
│
├── 📄 package.json                 # 项目配置
├── 📄 .eslintrc.js                 # ESLint 配置
├── 📄 tsconfig.json                # TypeScript 配置
├── 📄 jest.config.js               # Jest 配置
├── 📄 Dockerfile                   # Docker 配置
├── 📄 .dockerignore                # Docker 忽略文件
├── 📄 .gitignore                   # Git 忽略文件
└── 📄 .prettierrc                  # Prettier 配置
```

## 🎯 按角色查找

### 👨‍💻 开发者
- [QUICKSTART.md](./QUICKSTART.md) - 快速开始
- [README.md](./README.md) - 工作流说明
- [.github/workflows/ci.yml](./.github/workflows/ci.yml) - CI 工作流

### 🔧 DevOps 工程师
- [IMPLEMENTATION_GUIDE.md](./IMPLEMENTATION_GUIDE.md) - 实施指南
- [.github/workflows/cd.yml](./.github/workflows/cd.yml) - CD 工作流
- [.github/workflows/monitoring.yml](./.github/workflows/monitoring.yml) - 监控工作流

### 🔒 安全工程师
- [.github/workflows/security.yml](./.github/workflows/security.yml) - 安全工作流
- [README.md](./README.md) - 安全最佳实践
- [.github/ISSUE_TEMPLATE/security-issue.md](./.github/ISSUE_TEMPLATE/security-issue.md) - 安全报告模板

### 🏗️ 架构师
- [CICD_SUMMARY.md](./CICD_SUMMARY.md) - 架构概览
- [README.md](./README.md) - 最佳实践
- [IMPLEMENTATION_GUIDE.md](./IMPLEMENTATION_GUIDE.md) - 实施路线图

### 🎓 项目经理
- [CICD_SUMMARY.md](./CICD_SUMMARY.md) - 交付内容
- [README.md](./README.md) - 核心特性
- [QUICKSTART.md](./QUICKSTART.md) - 快速验证

## 📖 按主题查找

### 工作流配置
- [CI 工作流](./.github/workflows/ci.yml) - 代码质量、测试、构建
- [CD 工作流](./.github/workflows/cd.yml) - 多环境部署
- [监控工作流](./.github/workflows/monitoring.yml) - 应用监控
- [安全工作流](./.github/workflows/security.yml) - 安全扫描
- [发布工作流](./.github/workflows/release.yml) - 版本发布

### 测试配置
- [单元测试](./README.md#测试配置)
- [集成测试](./README.md#测试配置)
- [性能测试](./tests/performance/api-load-test.js)
- [负载测试](./tests/performance/api-load-test.js)

### 安全配置
- [SAST](./.github/workflows/security.yml#静态应用安全测试-sast)
- [SCA](./.github/workflows/security.yml#依赖项安全扫描-sca)
- [容器安全](./.github/workflows/security.yml#容器安全扫描)
- [DAST](./.github/workflows/security.yml#动态应用安全测试-dast)

### 部署配置
- [Staging 部署](./.github/workflows/cd.yml#部署到-staging)
- [Production 部署](./.github/workflows/cd.yml#部署到-production)
- [回滚机制](./.github/workflows/cd.yml#回滚)
- [健康检查](./.github/workflows/cd.yml#健康检查)

### 监控配置
- [健康检查](./.github/workflows/monitoring.yml#应用健康检查)
- [性能监控](./.github/workflows/monitoring.yml#性能监控)
- [错误追踪](./.github/workflows/monitoring.yml#错误追踪--告警)
- [日志分析](./.github/workflows/monitoring.yml#日志分析)

## 🔧 配置文件

### 代码质量
- [package.json](./package.json) - 项目脚本和依赖
- [.eslintrc.js](./.eslintrc.js) - ESLint 规则
- [.prettierrc](./.prettierrc) - 代码格式化

### 构建配置
- [tsconfig.json](./tsconfig.json) - TypeScript 编译
- [jest.config.js](./jest.config.js) - 测试框架
- [Dockerfile](./Dockerfile) - 容器构建

### 性能配置
- [.github/lighthouse-budgets.json](./.github/lighthouse-budgets.json) - 性能预算
- [tests/performance/api-load-test.js](./tests/performance/api-load-test.js) - 负载测试

## 📋 检查清单

### 开始使用
- [ ] 阅读 [QUICKSTART.md](./QUICKSTART.md)
- [ ] 复制工作流文件到项目
- [ ] 配置 GitHub Secrets
- [ ] 推送代码触发工作流
- [ ] 验证工作流运行成功

### 生产就绪
- [ ] 配置环境保护规则
- [ ] 设置审批流程
- [ ] 配置告警通知
- [ ] 验证回滚机制
- [ ] 完成所有验证检查（见 [IMPLEMENTATION_GUIDE.md](./IMPLEMENTATION_GUIDE.md)）

## 🎓 学习路径

### 第 1 天: 基础 CI
1. 阅读 [QUICKSTART.md](./QUICKSTART.md)
2. 设置基础 CI 工作流
3. 配置 linting 和测试
4. 验证代码覆盖率

### 第 2 天: 安全扫描
1. 阅读 [README.md](./README.md) 安全章节
2. 配置 SAST 和 SCA
3. 查看安全报告
4. 修复发现的问题

### 第 3 天: 部署自动化
1. 阅读 [IMPLEMENTATION_GUIDE.md](./IMPLEMENTATION_GUIDE.md) 阶段 3
2. Docker 化应用
3. 配置 CD 工作流
4. 部署到 Staging

### 第 4 天: 监控告警
1. 配置监控工作流
2. 设置性能预算
3. 配置 Slack 通知
4. 验证告警系统

### 第 5 天: 生产部署
1. 配置环境保护规则
2. 部署到 Production
3. 验证回滚机制
4. 完成所有检查清单

## 💡 提示和技巧

### 提高效率
- ✅ 使用缓存加速构建
- ✅ 并行化任务
- ✅ 矩阵策略节省时间
- ✅ 复用 Actions

### 避免陷阱
- ❌ 不要在 CI 中运行长时间任务
- ❌ 不要在 PR 中部署生产
- ❌ 不要忽略安全警告
- ❌ 不要忘记配置回滚

### 最佳实践
- ✅ 定期更新 Actions 版本
- ✅ 保护敏感信息
- ✅ 监控工作流性能
- ✅ 保持文档更新

## 🔗 外部资源

### 官方文档
- [GitHub Actions 文档](https://docs.github.com/en/actions)
- [Docker 文档](https://docs.docker.com/)
- [Kubernetes 文档](https://kubernetes.io/docs/)

### 工具文档
- [Trivy](https://aquasecurity.github.io/trivy/)
- [CodeQL](https://codeql.github.com/)
- [Lighthouse CI](https://github.com/GoogleChrome/lighthouse-ci)
- [k6](https://k6.io/docs/)

### 社区资源
- [Awesome Actions](https://github.com/sdras/awesome-actions)
- [GitHub Actions 市场](https://github.com/marketplace?type=actions)

## 🆘 获取帮助

### 常见问题
- 查看 [README.md](./README.md) 故障排查章节
- 查看 [IMPLEMENTATION_GUIDE.md](./IMPLEMENTATION_GUIDE.md) 常见问题

### 问题排查
1. 查看工作流日志
2. 检查配置文件语法
3. 验证 Secrets 配置
4. 查看文档中的故障排查章节

### 贡献
欢迎提交 Issue 和 Pull Request！

## 📊 快速参考

### 工作流触发条件

| 工作流 | 触发条件 |
|--------|----------|
| CI | Push to main/develop, PR |
| CD | Push to main |
| 监控 | 定时（每小时）、手动 |
| 安全 | Push、PR、定时（每天） |
| 发布 | Git tag (v*) |

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| NODE_VERSION | 20 | Node.js 版本 |
| REGISTRY | ghcr.io | 容器注册表 |
| IMAGE_NAME | ${{ github.repository }} | 镜像名称 |

### 端口

| 服务 | 端口 |
|------|------|
| 应用 | 3000 |
| 健康检查 | /health |

---

**文档版本**: 1.0.0
**最后更新**: 2026-03-25
**维护状态**: ✅ 活跃维护
