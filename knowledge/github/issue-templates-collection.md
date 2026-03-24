# GitHub Issue 模板库

## 目录

1. [模板使用指南](#模板使用指南)
2. [Bug 报告模板](#bug-报告模板)
3. [功能请求模板](#功能请求模板)
4. [文档改进模板](#文档改进模板)
5. [性能问题模板](#性能问题模板)
6. [安全漏洞模板](#安全漏洞模板)
7. [测试失败模板](#测试失败模板)
8. [部署问题模板](#部署问题模板)
9. [兼容性问题模板](#兼容性问题模板)
10. [代码审查请求模板](#代码审查请求模板)
11. [支持请求模板](#支持请求模板)
12. [重构建议模板](#重构建议模板)
13. [基础设施变更模板](#基础设施变更模板)
14. [社区讨论模板](#社区讨论模板)

---

## 模板使用指南

### 如何使用这些模板

#### 方法 1: 直接复制到 `.github/ISSUE_TEMPLATE/`

```bash
# 创建模板目录
mkdir -p .github/ISSUE_TEMPLATE

# 复制模板文件
cp bug_report.md .github/ISSUE_TEMPLATE/
cp feature_request.md .github/ISSUE_TEMPLATE/
# ... 其他模板
```

#### 方法 2: 使用 GitHub Issue 表单 (推荐)

GitHub 支持更强大的**YAML 表单格式**，提供验证和更好的用户体验。

### 表单模板 vs Markdown 模板

| 特性 | Markdown | YAML 表单 |
|------|----------|-----------|
| **字段验证** | ❌ | ✅ |
| **必填字段** | ❌ | ✅ |
| **下拉选项** | ❌ | ✅ |
| **条件显示** | ❌ | ✅ |
| **易用性** | 一般 | 优秀 |
| **灵活性** | 高 | 中 |

**推荐**: 新项目使用 YAML 表单，旧项目可以逐步迁移。

---

## 1. Bug 报告模板

### YAML 表单版本 (推荐)

```yaml
---
name: 🐛 Bug 报告
description: 报告问题帮助我们改进
title: "[BUG] "
labels: ["bug", "needs-triage"]
assignees: []
body:
  - type: markdown
    attributes:
      value: |
        感谢提交 Bug 报告！请填写以下信息帮助我们快速定位和解决问题。

  - type: textarea
    id: description
    attributes:
      label: Bug 描述
      description: 清晰简洁地描述 Bug
      placeholder: 例如：点击登录按钮后页面无响应
    validations:
      required: true

  - type: textarea
    id: reproduction
    attributes:
      label: 复现步骤
      description: 如何重现这个 Bug
      placeholder: |
        1. 访问页面 '...'
        2. 点击按钮 '....'
        3. 滚动到 '....'
        4. 看到错误
    validations:
      required: true

  - type: textarea
    id: expected
    attributes:
      label: 期望行为
      description: 你期望发生什么
      placeholder: 例如：应该跳转到首页

  - type: textarea
    id: actual
    attributes:
      label: 实际行为
      description: 实际发生了什么
      placeholder: 例如：页面卡死，浏览器控制台报错

  - type: textarea
    id: screenshots
    attributes:
      label: 截图或录屏
      description: 如果适用，添加截图或录屏来说明问题
      placeholder: 拖拽图片到此处，或粘贴图片链接

  - type: input
    id: os
    attributes:
      label: 操作系统
      placeholder: 例如：macOS 14.2, Windows 11, Ubuntu 22.04
    validations:
      required: true

  - type: input
    id: browser
    attributes:
      label: 浏览器版本 (如果是 Web Bug)
      placeholder: 例如：Chrome 120, Firefox 121, Safari 17

  - type: input
    id: app_version
    attributes:
      label: 应用版本
      description: 可以从应用设置中查看
      placeholder: 例如：v2.1.0
    validations:
      required: true

  - type: textarea
    id: logs
    attributes:
      label: 日志或错误信息
      description: 粘贴相关的日志或错误堆栈
      render: shell
      placeholder: |
        错误堆栈、console 输出、日志文件内容等

  - type: dropdown
    id: severity
    attributes:
      label: 严重程度
      description: 这个 Bug 影响有多严重？
      options:
        - 阻塞性 (无法使用核心功能)
        - 高级 (影响重要功能)
        - 中级 (影响次要功能)
        - 低级 (小问题，不影响使用)
      default: 2

  - type: textarea
    id: additional_context
    attributes:
      label: 额外信息
      description: 其他相关信息、参考资料等
      placeholder: 任何你觉得有用的信息

  - type: checkboxes
    id: terms
    attributes:
      label: 确认检查
      description: 提交前请确认
      options:
        - label: 我已搜索过现有 Issues，没有找到相同问题
          required: true
        - label: 我已阅读并遵循贡献指南
          required: true
        - label: 我已提供足够的复现信息
          required: true
        - label: 问题可以在最新版本复现
          required: false
```

### Markdown 版本

```markdown
---
name: Bug 报告
about: 报告一个问题
title: '[BUG] '
labels: bug
assignees: ''
---

## Bug 描述
清晰简洁地描述这个 Bug。

## 复现步骤
1. 访问页面 '...'
2. 点击 '....'
3. 滚动到 '....'
4. 看到错误

## 期望行为
应该发生什么。

## 实际行为
实际发生了什么。

## 截图
如果适用，添加截图或录屏。

## 环境信息

| 信息 | 值 |
|------|-----|
| 操作系统 | [例如 macOS 14.0] |
| 浏览器 | [例如 Chrome 120] |
| 应用版本 | [例如 v2.1.0] |

## 日志信息
<details>
<summary>点击展开日志</summary>

```
粘贴相关的日志、错误堆栈、console 输出等
```
</details>

## 额外信息
其他相关信息、参考资料等。

---

### 提交前检查清单

- [ ] 我已搜索过现有 Issues，确认这是新问题
- [ ] 我已阅读贡献指南
- [ ] 我已提供足够的复现步骤
- [ ] 我已在最新版本测试，问题仍然存在
- [ ] 我已附上相关截图或日志
```

---

## 2. 功能请求模板

### YAML 表单版本

```yaml
---
name: ✨ 功能请求
description: 建议新功能或改进
title: "[FEATURE] "
labels: ["enhancement", "needs-discussion"]
body:
  - type: markdown
    attributes:
      value: |
        感谢提出功能建议！请在提交前先搜索现有 Issues，确保没有重复的请求。

  - type: textarea
    id: problem
    attributes:
      label: 问题背景
      description: 这个功能解决什么问题？为什么需要？
      placeholder: |
        例如：当前的导出功能只支持 CSV，很多用户需要导出 Excel 格式以便进一步处理数据。
    validations:
      required: true

  - type: textarea
    id: solution
    attributes:
      label: 建议方案
      description: 你希望这个功能如何工作？
      placeholder: |
        例如：在导出菜单中添加"导出为 Excel"选项，支持自定义工作表名称和格式化选项。
    validations:
      required: true

  - type: textarea
    id: alternatives
    attributes:
      label: 替代方案
      description: 你考虑过其他实现方式吗？
      placeholder: 描述你考虑过的其他方案，以及为什么选择这个方案

  - type: textarea
    id: mockups
    attributes:
      label: 设计稿或示例
      description: 如果有设计稿、原型或参考链接，请提供
      placeholder: 拖拽图片或粘贴链接

  - type: dropdown
    id: priority
    attributes:
      label: 优先级
      description: 这个功能对你有多重要？
      options:
        - 紧急 (阻塞我的工作)
        - 高 (非常需要，强烈推荐)
        - 中 (有需要但非紧急)
        - 低 (锦上添花的功能)
      default: 2

  - type: textarea
    id: acceptance_criteria
    attributes:
      label: 验收标准
      description: 什么样的结果你会满意？
      placeholder: |
        - [ ] 可以通过导出菜单导出 Excel
        - [ ] 支持自定义工作表名称
        - [ ] 保留数据格式（日期、数字等）
        - [ ] 导出时间合理（< 5秒，1000条数据）

  - type: textarea
    id: additional_context
    attributes:
      label: 额外信息
      description: 其他相关信息
      placeholder: 参考资料、竞品分析、技术限制等

  - type: checkboxes
    id: confirmations
    attributes:
      label: 确认检查
      options:
        - label: 我已搜索过现有 Issues
          required: true
        - label: 这个功能符合项目路线图
          required: false
        - label: 我愿意参与实现或测试
          required: false
```

---

## 3. 文档改进模板

```yaml
---
name: 📚 文档改进
description: 报告文档问题或建议改进
title: "[DOCS] "
labels: ["documentation"]
body:
  - type: textarea
    id: issue
    attributes:
      label: 文档问题描述
      description: 文档有什么问题？
      placeholder: |
        例如：API 文档中缺少参数说明，示例代码已过时等
    validations:
      required: true

  - type: dropdown
    id: doc_type
    attributes:
      label: 文档类型
      options:
        - API 文档
        - 用户指南
        - 开发指南
        - 安装指南
        - README
        - 代码注释
        - 其他

  - type: input
    id: page_url
    attributes:
      label: 页面链接
      description: 如果是网站文档，提供链接
      placeholder: https://docs.example.com/page

  - type: textarea
    id: suggested_change
    attributes:
      label: 建议的改进
      description: 你认为应该如何改进？
      placeholder: 提供具体的改进建议，或直接提供改进后的文本

  - type: checkboxes
    id: contribution
    attributes:
      label: 贡献意愿
      options:
        - label: 我愿意提交 PR 修复文档问题
          required: false
```

---

## 4. 性能问题模板

```yaml
---
name: ⚡ 性能问题
description: 报告性能瓶颈或优化建议
title: "[PERFORMANCE] "
labels: ["performance"]
body:
  - type: markdown
    attributes:
      value: |
        性能问题需要详细的基准数据和分析。请提供尽可能多的信息。

  - type: textarea
    id: description
    attributes:
      label: 性能问题描述
      description: 哪个功能或操作性能不佳？
      placeholder: 例如：加载用户列表需要 10 秒
    validations:
      required: true

  - type: textarea
    id: current_metrics
    attributes:
      label: 当前性能指标
      description: 请提供具体的性能数据
      placeholder: |
        - 响应时间: 10 秒
        - 数据量: 10,000 条记录
        - CPU 使用率: 80%
        - 内存使用: 2GB
    validations:
      required: true

  - type: textarea
    id: expected_metrics
    attributes:
      label: 期望性能指标
      description: 你期望达到什么性能？
      placeholder: |
        - 响应时间: < 1 秒
        - 支持 100,000 条记录
        - CPU 使用率: < 50%

  - type: textarea
    id: profiling_data
    attributes:
      label: 性能分析数据
      description: 如果有 profiling 数据、火焰图等，请提供
      render: shell
      placeholder: 粘贴 profiling 输出或上传火焰图

  - type: textarea
    id: environment
    attributes:
      label: 环境信息
      placeholder: |
        - CPU: Intel i7-9700K
        - RAM: 16GB
        - 磁盘: SSD
        - 网络: 1Gbps
    validations:
      required: true

  - type: textarea
    id: suggested_solutions
    attributes:
      label: 建议的优化方案
      description: 如果你有优化思路，请分享

  - type: checkboxes
    id: contribution
    attributes:
      label: 贡献意愿
      options:
        - label: 我愿意提交 PR 进行优化
          required: false
        - label: 我需要进行性能分析但需要指导
          required: false
```

---

## 5. 安全漏洞模板

```yaml
---
name: 🔒 安全漏洞报告
description: 报告安全漏洞（私有）
title: "[SECURITY] "
labels: ["security", "critical"]
body:
  - type: markdown
    attributes:
      value: |
        ⚠️ **重要**: 安全漏洞报告是私密的，不会公开。
        请不要在公开 Issue 中讨论安全细节。

  - type: textarea
    id: vulnerability_description
    attributes:
      label: 漏洞描述
      description: 清晰描述安全漏洞
      placeholder: 例如：SQL 注入漏洞允许攻击者获取所有用户数据
    validations:
      required: true

  - type: dropdown
    id: severity
    attributes:
      label: 严重程度
      description: 根据通用漏洞评分系统 (CVSS) 评估
      options:
        - 严重 (9.0-10.0) - 可直接获取系统控制权
        - 高危 (7.0-8.9) - 可获取重要数据或权限
        - 中危 (4.0-6.9) - 影响有限
        - 低危 (0.1-3.9) - 最小影响
      default: 1

  - type: textarea
    id: affected_versions
    attributes:
      label: 受影响的版本
      description: 哪些版本受影响？
      placeholder: |
        - v1.0.0 - v2.1.0
        - 主分支
    validations:
      required: true

  - type: textarea
    id: reproduction_steps
    attributes:
      label: 漏洞复现步骤
      description: 如何触发这个漏洞？
      placeholder: 提供详细的复现步骤和 Proof of Concept (PoC)
    validations:
      required: true

  - type: textarea
    id: impact_assessment
    attributes:
      label: 影响评估
      description: 这个漏洞的潜在影响是什么？
      placeholder: 描述攻击者可能造成的损害

  - type: textarea
    id: suggested_fix
    attributes:
      label: 建议修复方案
      description: 如果你有修复建议，请提供

  - type: input
    id: cve_id
    attributes:
      label: CVE 编号 (如果已分配)
      placeholder: CVE-2024-12345

  - type: checkboxes
    id: acknowledgments
    attributes:
      label: 确认
      options:
        - label: 我同意负责任地披露漏洞，不会公开利用
          required: true
        - label: 我同意等待 90 天后再公开披露
          required: true
```

---

## 6. 测试失败模板

```yaml
---
name: 🧪 测试失败
description: 报告测试用例失败
title: "[TEST] "
labels: ["testing"]
body:
  - type: textarea
    id: test_info
    attributes:
      label: 测试信息
      description: 哪个测试失败了？
      placeholder: |
        测试文件: tests/test_auth.py
        测试用例: test_login_success
    validations:
      required: true

  - type: textarea
    id: failure_output
    attributes:
      label: 失败输出
      description: 粘贴完整的测试失败输出
      render: shell
      placeholder: 粘贴 pytest/jest/等测试框架的输出
    validations:
      required: true

  - type: textarea
    id: reproduction
    attributes:
      label: 复现步骤
      description: 如何运行失败的测试？
      placeholder: |
        1. git clone repo
        2. cd repo
        3. pip install -r requirements.txt
        4. pytest tests/test_auth.py::test_login_success

  - type: textarea
    id: expected_behavior
    attributes:
      label: 期望行为
      description: 测试应该通过，为什么你认为这是 Bug？

  - type: textarea
    id: environment
    attributes:
      label: 测试环境
      placeholder: |
        - OS: Ubuntu 22.04
        - Python: 3.11
        - 测试框架: pytest 7.4.0

  - type: dropdown
    id: failure_type
    attributes:
      label: 失败类型
      options:
        - 偶发性失败 (Flaky test)
        - 持续失败
        - 超时
        - 断言错误
        - 环境问题
```

---

## 7. 部署问题模板

```yaml
---
name: 🚀 部署问题
description: 报告部署或安装问题
title: "[DEPLOY] "
labels: ["deployment"]
body:
  - type: markdown
    attributes:
      value: |
        部署问题需要详细的环境信息和错误日志。

  - type: dropdown
    id: deployment_method
    attributes:
      label: 部署方式
      options:
        - Docker
        - Kubernetes
        - 手动部署
        - 云服务 (AWS/GCP/Azure)
        - 其他
      default: 0

  - type: textarea
    id: description
    attributes:
      label: 问题描述
      description: 部署的哪个阶段出现问题？
      placeholder: 例如：容器启动失败、服务无法访问等
    validations:
      required: true

  - type: textarea
    id: error_logs
    attributes:
      label: 错误日志
      description: 粘贴相关的错误日志
      render: shell
      placeholder: |
        Docker 日志: docker logs <container>
        K8s 日志: kubectl logs <pod>
        系统日志: journalctl
    validations:
      required: true

  - type: textarea
    id: config
    attributes:
      label: 配置文件
      description: 粘贴相关的配置文件（删除敏感信息）
      render: shell
      placeholder: |
        docker-compose.yml
        values.yaml
        .env 文件（删除密码等）

  - type: textarea
    id: environment_info
    attributes:
      label: 环境信息
      placeholder: |
        - OS: Ubuntu 22.04
        - Docker: 24.0.7
        - Kubernetes: 1.28
        - CPU: 4 cores
        - RAM: 8GB

  - type: textarea
    id: troubleshooting_steps
    attributes:
      label: 已尝试的排查步骤
      description: 你已经尝试了什么？
      placeholder: 描述你已尝试的解决方案

  - type: checkboxes
    id: checks
    attributes:
      label: 检查项
      options:
        - label: 我已检查系统要求 (CPU, RAM, 磁盘空间)
          required: true
        - label: 我已检查网络连接
          required: true
        - label: 我已查看官方文档
          required: true
```

---

## 8. 兼容性问题模板

```yaml
---
name: 🔄 兼容性问题
description: 报告兼容性问题
title: "[COMPAT] "
labels: ["compatibility"]
body:
  - type: textarea
    id: description
    attributes:
      label: 问题描述
      description: 什么功能在什么环境下不兼容？
      placeholder: 例如：应用在 iOS 12 上崩溃
    validations:
      required: true

  - type: dropdown
    id: compatibility_type
    attributes:
      label: 兼容性类型
      options:
        - 浏览器兼容性
        - 操作系统兼容性
        - 版本兼容性
        - 硬件兼容性
        - 第三方库兼容性

  - type: textarea
    id: working_environment
    attributes:
      label: 正常工作的环境
      placeholder: |
        - OS: macOS 14
        - Browser: Chrome 120

  - type: textarea
    id: broken_environment
    attributes:
      label: 出问题的环境
      placeholder: |
        - OS: Windows 10
        - Browser: Firefox 115

  - type: textarea
    id: error_details
    attributes:
      label: 错误详情
      description: 粘贴错误信息、控制台输出等
      render: shell

  - type: textarea
    id: workaround
    attributes:
      label: 临时解决方案
      description: 你找到的变通方法是什么？
```

---

## 9. 代码审查请求模板

```yaml
---
name: 👀 代码审查请求
description: 请求代码审查而不创建 PR
title: "[REVIEW] "
labels: ["code-review"]
body:
  - type: markdown
    attributes:
      value: |
        使用此模板请求代码审查，而不必创建正式的 PR。
        适用于：设计审查、架构讨论、重构建议等。

  - type: textarea
    id: description
    attributes:
      label: 审查描述
      description: 你想审查什么？为什么需要审查？
      placeholder: 例如：请求审查重构方案，确认是否影响性能
    validations:
      required: true

  - type: input
    id: files
    attributes:
      label: 相关文件
      description: 哪些文件需要审查？
      placeholder: src/auth.py, tests/test_auth.py

  - type: input
    id: branch
    attributes:
      label: 分支名
      placeholder: feature/refactor-auth

  - type: dropdown
    id: review_type
    attributes:
      label: 审查类型
      options:
        - 架构设计
        - 代码实现
        - 性能优化
        - 安全审查
        - 测试覆盖

  - type: textarea
    id: concerns
    attributes:
      label: 关注点
      description: 你最关心的方面是什么？
      placeholder: 例如：是否影响并发性能？是否有安全风险？

  - type: textarea
    id: context
    attributes:
      label: 背景信息
      description: 提供足够的上下文信息
      placeholder: 链接到相关 Issue、设计文档等

  - type: checkboxes
    id: checklist
    attributes:
      label: 审查前检查
      options:
        - label: 代码已通过本地测试
          required: true
        - label: 代码已通过 linter
          required: true
        - label: 已添加必要的注释
          required: false
        - label: 已更新相关文档
          required: false
```

---

## 10. 支持请求模板

```yaml
---
name: ❓ 支持请求
description: 寻求帮助或提问
title: "[SUPPORT] "
labels: ["question"]
body:
  - type: markdown
    attributes:
      value: |
        这是面向社区的支持渠道。对于企业级支持，请联系 support@example.com。

  - type: textarea
    id: question
    attributes:
      label: 你的问题
      description: 清晰描述你的问题或疑问
      placeholder: 例如：如何配置 API 密钥？
    validations:
      required: true

  - type: textarea
    id: context
    attributes:
      label: 背景信息
      description: 提供足够的上下文
      placeholder: |
        你想做什么？
        你已经尝试了什么？
        预期的结果是什么？
        实际的结果是什么？

  - type: input
    id: docs_link
    attributes:
      label: 相关文档链接
      description: 你查阅过哪些文档？
      placeholder: https://docs.example.com/config

  - type: dropdown
    id: category
    attributes:
      label: 问题分类
      options:
        - 使用帮助
        - 配置问题
        - API 使用
        - 最佳实践
        - 其他

  - type: checkboxes
    id: checks
    attributes:
      label: 检查项
      options:
        - label: 我已搜索过文档和 Issues
          required: true
        - label: 我已提供足够的上下文信息
          required: true
```

---

## 11. 重构建议模板

```yaml
---
name: 🔨 重构建议
description: 提出代码重构建议
title: "[REFACTOR] "
labels: ["refactoring", "tech-debt"]
body:
  - type: markdown
    attributes:
      value: |
        重构建议应该有明确的改进目标和理由。

  - type: textarea
    id: current_problem
    attributes:
      label: 当前问题
      description: 现有代码有什么问题？
      placeholder: |
        例如：代码难以维护、重复代码过多、性能瓶颈、缺乏测试等
    validations:
      required: true

  - type: textarea
    id: proposed_solution
    attributes:
      label: 建议方案
      description: 你建议如何重构？
      placeholder: 描述新的设计、架构或实现方式

  - type: textarea
    id: benefits
    attributes:
      label: 改进收益
      description: 这个重构带来什么好处？
      placeholder: |
        - 提高代码可读性
        - 减少技术债务
        - 提升性能
        - 增强可测试性

  - type: dropdown
    id: priority
    attributes:
      label: 优先级
      options:
        - 高 (影响开发效率)
        - 中 (建议尽快处理)
        - 低 (可以延后)

  - type: textarea
    id: breaking_changes
    attributes:
      label: 破坏性变更
      description: 是否会影响现有功能？
      placeholder: 描述可能的破坏性变更和兼容性影响

  - type: textarea
    id: implementation_plan
    attributes:
      label: 实施计划
      description: 如何逐步实施这个重构？
      placeholder: 提供分阶段实施计划，确保每个阶段都可以独立部署
```

---

## 12. 基础设施变更模板

```yaml
---
name: 🏗️ 基础设施变更
description: 提出基础设施或 DevOps 相关变更
title: "[INFRA] "
labels: ["infrastructure"]
body:
  - type: markdown
    attributes:
      value: |
        基础设施变更需要详细的计划和风险评估。

  - type: dropdown
    id: change_type
    attributes:
      label: 变更类型
      options:
        - CI/CD 管道
        - Docker/Kubernetes 配置
        - 监控和日志
        - 数据库迁移
        - 云资源配置
        - 网络配置

  - type: textarea
    id: description
    attributes:
      label: 变更描述
      description: 要改变什么？为什么？
      placeholder: 详细描述基础设施变更的内容和原因
    validations:
      required: true

  - type: textarea
    id: current_setup
    attributes:
      label: 当前配置
      description: 当前配置是什么样的？
      render: shell
      placeholder: 粘贴相关的配置文件

  - type: textarea
    id: proposed_setup
    attributes:
      label: 建议配置
      description: 建议的新配置是什么？
      render: shell

  - type: textarea
    id: impact_analysis
    attributes:
      label: 影响分析
      description: 这个变更会影响什么？
      placeholder: |
        - 影响的服务：API, Web, Worker
        - 影响的用户：所有用户
        - 潜在风险：服务中断
        - 回滚方案：恢复旧配置

  - type: textarea
    id: implementation_plan
    attributes:
      label: 实施计划
      description: 如何实施这个变更？
      placeholder: |
        1. 在 staging 环境测试
        2. 准备回滚方案
        3. 选择低峰期部署
        4. 监控关键指标
        5. 逐步灰度发布

  - type: textarea
    id: monitoring
    attributes:
      label: 监控指标
      description: 需要监控什么？
      placeholder: 列出关键监控指标和告警规则

  - type: checkboxes
    id: checklist
    attributes:
      label: 检查项
      options:
        - label: 我已在 staging 环境测试
          required: true
        - label: 我有回滚方案
          required: true
        - label: 我已设置监控和告警
          required: true
```

---

## 13. 社区讨论模板

```yaml
---
name: 💬 社区讨论
description: 发起社区讨论，收集反馈
title: "[DISCUSS] "
labels: ["discussion"]
body:
  - type: markdown
    attributes:
      value: |
        使用此模板发起非 Bug、非功能请求的开放讨论。

  - type: textarea
    id: topic
    attributes:
      label: 讨论主题
      description: 你想讨论什么？
      placeholder: 例如：项目的长期方向、API 设计理念、社区治理等
    validations:
      required: true

  - type: textarea
    id: background
    attributes:
      label: 背景信息
      description: 为什么现在讨论这个？
      placeholder: 提供足够的上下文，帮助其他人理解讨论的背景

  - type: textarea
    id: options
    attributes:
      label: 讨论选项
      description: 有哪些可能的方案或方向？
      placeholder: 列出不同的选项供社区讨论

  - type: dropdown
    id: discussion_type
    attributes:
      label: 讨论类型
      options:
        - RFC (Request for Comments)
        - 设计讨论
        - 技术选型
        - 社区治理
        - 其他

  - type: textarea
    id: expected_outcome
    attributes:
      label: 期望结果
      description: 讨论的预期结果是什么？
      placeholder: 例如：达成共识、决定技术方案、收集反馈等

  - type: input
    id: deadline
    attributes:
      label: 讨论截止日期
      description: 如果有截止日期，请提供
      placeholder: 2024-03-31

  - type: checkboxes
    id: moderation
    attributes:
      label: 讨论礼仪
      options:
        - label: 我同意保持尊重和建设性
          required: true
        - label: 我愿意听取不同意见
          required: true
```

---

## 模板最佳实践

### 1. 标签设计

推荐使用**层次化标签系统**:

```yaml
kind:
  - bug
  - feature
  - documentation
  - performance
  - security

status:
  - needs-triage
  - confirmed
  - in-progress
  - in-review
  - blocked
  - ready-to-merge

priority:
  - critical
  - high
  - medium
  - low

complexity:
  - small
  - medium
  - large
  - x-large
```

### 2. 字段验证

合理使用**必填字段**和**验证规则**:

```yaml
validations:
  required: true  # 必填

# 下拉框默认值
default: 2

# 复选框强制确认
options:
  - label: 我已确认
    required: true
```

### 3. 条件显示 (高级)

使用条件逻辑动态显示字段:

```yaml
- type: dropdown
  id: has_code
  attributes:
    label: 是否包含代码?
    options:
      - 是
      - 否

- type: textarea
  id: code_snippet
  attributes:
    label: 代码片段
  # 仅当 has_code=是 时显示
  if: has_code == 是
```

### 4. Markdown 渲染

对代码和日志使用语法高亮:

```yaml
- type: textarea
  attributes:
    render: shell  # 或 python, javascript, json
```

### 5. 提示和占位符

提供**清晰的指导**:

```yaml
attributes:
  label: 标题 (简短明确)
  description: 详细说明
  placeholder: 示例内容
```

---

## 模板维护

### 定期审查

每季度检查模板:

- [ ] 统计各模板使用频率
- [ ] 收集用户反馈
- [ ] 更新过时字段
- [ ] 优化用户体验
- [ ] 添加新模板类型

### A/B 测试

对关键模板进行 A/B 测试:

1. 创建模板变体
2. 收集提交数据
3. 分析完成率
4. 选择最优版本

### 模板版本控制

```bash
# 使用 Git 管理模板变更
git log .github/ISSUE_TEMPLATE/

# 标记重要变更
git tag template/v2.0
```

---

## 总结

高质量的 Issue 模板能够:

✅ **提高信息质量** - 获取更完整和结构化的信息
✅ **减少来回沟通** - 避免反复询问基本信息
✅ **加速处理流程** - 自动化分类和分配
✅ **改善用户体验** - 提供清晰的提交指引
✅ **建立专业性** - 展示项目的规范和专业

投入时间精心设计模板，长期来看会显著提升社区效率和贡献质量。
