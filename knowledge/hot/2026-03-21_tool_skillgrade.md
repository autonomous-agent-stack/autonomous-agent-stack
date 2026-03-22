# Skillgrade - Agent Skills单元测试框架

**来源**: https://x.com/shao__meng/status/2033704407129542798
**GitHub**: https://github.com/mgechev/skillgrade
**作者**: @mgechev (Skills Best Practices作者)
**发现日期**: 2026-03-21
**优先级**: ⭐⭐ 中

## 核心价值

验证Codex/Claude Code/OpenClaw等AI Agents能否正确发现并使用Skills

## 技术特点

### 1. 混合评分机制
- **70% 确定性评分**：代码检查
- **30% LLM裁判**：工作流质量
- 加权得出最终通过率

### 2. 安全隔离
- Docker默认隔离
- 防止Agent误操作
- 支持local CI

### 3. 一键生成测试
- AI init自动生成eval.yaml
- 支持三种模式：
  - 烟雾测试（5次）
  - 可靠评估（15次）
  - 回归检测（30次）

## 使用流程（3分钟）

```bash
# 1. 在SKILL.md目录下
skillgrade init

# 2. 定制eval.yaml

# 3. 运行测试
skillgrade --smoke

# 4. 查看报告
skillgrade preview  # CLI
# 或浏览器访问 http://localhost:3847
```

## 示例项目

### 1. superlint（简易）
- Agent发现superlint工具
- 检查→修复→验证3步workflow
- 修复app.js

### 2. angular-modern（进阶）
- TS grader静态分析
- 5项现代Angular API迁移
- 展示复杂Skills评分

## 关键选项

- `--ci`: 阈值退出
- `--parallel`: 并行执行
- `--provider=local`: 本地执行
- `--threshold=0.8`: 通过阈值

## 适用场景

- Skills开发测试
- CI/CD集成
- Skills质量保证
- 回归检测

## 待实践

- [ ] 安装测试
- [ ] 创建自定义eval
- [ ] CI集成实践
