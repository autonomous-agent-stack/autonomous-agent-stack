# AI 代码审查工具快速参考

> 一页纸速查手册

---

## 🎯 工具选择决策树

```
开始
  │
  ├─ 团队规模 > 100 人？
  │   ├─ 是 → SonarQube ⭐⭐⭐⭐⭐
  │   └─ 否 ↓
  │
  ├─ 需要安全审计？
  │   ├─ 是 → Semgrep ⭐⭐⭐⭐⭐
  │   └─ 否 ↓
  │
  ├─ 技术债管理优先？
  │   ├─ 是 → CodeClimate ⭐⭐⭐⭐
  │   └─ 否 ↓
  │
  ├─ 需要快速反馈？
  │   ├─ 是 → DeepSource ⭐⭐⭐⭐⭐
  │   └─ 否 ↓
  │
  └─ Codacy ⭐⭐⭐⭐ (均衡选择)
```

---

## 📊 快速对比表

| 工具 | 免费版 | 扫描速度 | 自定义规则 | CI/CD | 最佳场景 |
|------|--------|---------|-----------|-------|---------|
| **SonarQube** | ✅ 自托管 | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 企业级 |
| **CodeClimate** | ✅ 4 个仓库 | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | 技术债 |
| **Codacy** | ✅ 30 个仓库 | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | 快速上手 |
| **DeepSource** | ✅ 4 个仓库 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | AI 辅助 |
| **Semgrep** | ✅ 完整功能 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 安全审计 |

---

## 🔥 常用命令速查

### SonarQube

```bash
# 本地扫描
mvn sonar:sonar \
  -Dsonar.host.url=http://localhost:9000 \
  -Dsonar.login=your-token

# Docker 扫描
docker run --rm \
  -e SONAR_HOST_URL=http://sonarqube:9000 \
  -e SONAR_LOGIN=your-token \
  -v "$PWD:/usr/src" \
  sonarsource/sonar-scanner-cli

# 质量门禁检查
mvn sonar:sonar -Dsonar.qualitygate.wait=true
```

### Semgrep

```bash
# 扫描当前目录
semgrep scan --config auto

# 扫描特定文件
semgrep scan --config auto src/

# 仅扫描修改的文件
git diff --name-only origin/main | semgrep scan --

# 自定义规则
semgrep scan --config rules/custom.yaml
```

### DeepSource

```bash
# 安装 CLI
curl -dSL https://deepsource.io/cli | sh

# 运行扫描
deepsource scan --cli-output

# 仅扫描修改的文件
deepsource scan --git-diff-origin=main
```

### CodeClimate

```bash
# 安装 CLI
curl -L https://codeclimate.com/downloads/test-reporter/test-reporter-latest-linux-amd64 > ./cc-test-reporter
chmod +x ./cc-test-reporter

# 运行分析
./cc-test-reporter analyze

# 上传覆盖率
./cc-test-reporter format-coverage -t simplecov -o coverage/codeclimate.json
./cc-test-reporter upload-coverage
```

### Codacy

```bash
# 安装 CLI
curl -L https://github.com/codacy/codacy-coverage-reporter/releases/latest/download/codacy-coverage-reporter-linux -o codacy-coverage-reporter
chmod +x codacy-coverage-reporter

# 上传覆盖率
./codacy-coverage-reporter report -l Python -r coverage.xml
```

---

## ⚙️ GitHub Actions 模板

### 组合使用所有工具

```yaml
name: Code Quality Pipeline

on:
  pull_request:
    branches: [main, develop]

jobs:
  quality-check:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0
      
      # 1. 快速安全扫描（1-2 分钟）
      - name: Semgrep Scan
        uses: returntocorp/semgrep-action@v1
        with:
          config: auto
      
      # 2. 增量质量分析（2-3 分钟）
      - name: DeepSource Scan
        uses: deepsource/deepsource-action@v1
        env:
          DEEPSOURCE_DOCKER_IMAGE: "deepsource/cli:latest"
        with:
          deepsource-api-token: ${{ secrets.DEEPSOURCE_API_TOKEN }}
      
      # 3. 完整质量分析（5-10 分钟）
      - name: SonarQube Scan
        uses: sonarsource/sonarqube-scan-action@master
        env:
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
          SONAR_HOST_URL: ${{ secrets.SONAR_HOST_URL }}
```

---

## 🎯 按语言选择工具

| 语言 | 推荐工具 #1 | 推荐工具 #2 | 备注 |
|------|------------|------------|------|
| **Java** | SonarQube | Semgrep | Java 生态最成熟 |
| **Python** | Semgrep | DeepSource | Python 规则丰富 |
| **JavaScript/TS** | DeepSource | Codacy | 现代 JS 支持好 |
| **Go** | Semgrep | DeepSource | 性能优化工具多 |
| **Ruby** | CodeClimate | DeepSource | Ruby 生态整合好 |
| **PHP** | SonarQube | Codacy | PHP 规则完整 |
| **C#** | SonarQube | Semgrep | .NET 支持完善 |
| **C/C++** | SonarQube | Semgrep | 静态分析专业 |

---

## 💰 成本对比（月费用）

| 团队规模 | SonarQube | CodeClimate | Codacy | DeepSource | Semgrep |
|---------|----------|-------------|--------|-----------|---------|
| **1-10 人** | €0 (自托管) | $0 | $0 | $0 | $0 |
| **10-50 人** | €1,200 | $290-1,450 | $120-600 | $120-600 | $200-1,000 |
| **50-100 人** | €6,000 | $1,450-2,900 | $600-1,200 | $600-1,200 | $1,000-2,000 |
| **100+ 人** | 定价咨询 | 定价咨询 | 定价咨询 | 定价咨询 | 定价咨询 |

---

## 🚀 分阶段实施路线图

### 阶段 1：基础部署（第 1-2 周）

- [ ] 选择 1-2 个工具试用
- [ ] 注册账号并获取 Token
- [ ] 配置基础规则
- [ ] 运行首次扫描

### 阶段 2：CI/CD 集成（第 3-4 周）

- [ ] 创建 GitHub Actions 工作流
- [ ] 配置质量门禁
- [ ] 设置失败通知
- [ ] 团队培训

### 阶段 3：优化和标准化（第 2-3 月）

- [ ] 调整规则减少误报
- [ ] 建立团队质量标准
- [ ] 创建自定义规则
- [ ] 定期审查会议

### 阶段 4：文化和持续改进（第 4-6 月）

- [ ] 质量指标可视化
- [ ] 技术债偿还计划
- [ ] 代码质量竞赛
- [ ] 最佳实践分享

---

## 🎓 学习资源

### 官方文档

- **SonarQube**: https://docs.sonarqube.org/
- **CodeClimate**: https://docs.codeclimate.com/
- **Codacy**: https://docs.codacy.com/
- **DeepSource**: https://deepsource.io/docs/
- **Semgrep**: https://semgrep.dev/docs/

### 社区和教程

- **SonarQube Community**: https://community.sonarsource.com/
- **Semgrep Rules**: https://semgrep.dev/r/
- **OWASP Top 10**: https://owasp.org/www-project-top-ten/
- **CWE Top 25**: https://cwe.mitre.org/top25/

### 视频教程

- "SonarQube Tutorial for Beginners" - YouTube
- "Semgrep for Security" - Conference Talks
- "Code Quality Best Practices" - Conference Talks

---

## 💡 最佳实践清单

### ✅ 推荐做法

- **增量分析** > 全量扫描
- **质量门禁** > 手动检查
- **定期审查** > 一次性设置
- **团队协作** > 个人使用
- **持续优化** > 配置后不管

### ❌ 避免陷阱

- ❌ 启用所有规则（误报爆炸）
- ❌ 忽略工具建议（买工具不用）
- ❌ 质量门禁太宽松（形同虚设）
- ❌ 仅关注分数（忽略实际问题）
- ❌ 不更新规则（错失新漏洞）

---

## 🆘 快速故障排查

| 问题 | 可能原因 | 解决方案 |
|------|---------|---------|
| **扫描超时** | 项目太大 | 增量扫描、并行处理 |
| **误报率高** | 规则太严格 | 调整规则、添加例外 |
| **内存溢出** | 资源不足 | 增加内存限制 |
| **质量门禁失败** | 新代码有问题 | 修复问题或调整阈值 |
| **Token 过期** | 凭据失效 | 重新生成 Token |

---

## 📱 常用链接

### 仪表盘

- SonarQube: http://localhost:9000
- CodeClimate: https://codeclimate.com
- Codacy: https://app.codacy.com
- DeepSource: https://deepsource.io
- Semgrep Cloud: https://semgrep.dev

### CLI 下载

- SonarQube Scanner: https://docs.sonarqube.org/latest/analysis/scan/sonarscanner/
- Semgrep CLI: https://semgrep.dev/docs/getting-started/
- DeepSource CLI: https://deepsource.io/docs/integrations/github-actions/
- CodeClimate CLI: https://docs.codeclimate.com/docs/configuring-test-coverage

---

## 🎯 一句话总结

> **SonarQube** = 企业级代码质量平台  
> **CodeClimate** = 技术债管理专家  
> **Codacy** = 快速上手的一站式方案  
> **DeepSource** = 现代化的增量分析工具  
> **Semgrep** = 自定义规则 + 安全审计之王

---

*最后更新：2026-03-25*
