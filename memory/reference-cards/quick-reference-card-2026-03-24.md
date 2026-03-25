# 🎯 OpenClaw Agent 快速参考卡

> **版本**: 1.0
> **更新时间**: 2026-03-24
> **适用场景**: 快速查阅核心概念

---

## 📋 核心概念速查

### 1. Function Calling 流程（5 步）

```
用户提问
   ↓
大模型思考 → 决定调用工具
   ↓
本地执行 → 获取结果
   ↓
结果返回 → 生成回复
```

**关键代码**:
```python
response = completion(
    model="deepseek/deepseek-chat",
    messages=messages,
    tools=[tool_schema],
    tool_choice="auto"
)
```

---

### 2. 成本对比表

| 方案 | 成本/次 | 月成本（1000次） | 节省 |
|------|---------|------------------|------|
| Claude CLI | $0.05-0.25 | $50-250 | - |
| GLM-5 | $0.01 | $10 | 80-96% |
| DeepSeek | $0.001 | $1 | 98-99.6% |
| 本地 Skill | $0.0001 | $0.1 | 99.8-99.9% |

---

### 3. Agent 模板选择

| Agent 类型 | 适用场景 | 核心技能 |
|-----------|---------|----------|
| **代码审查** | 代码质量检查 | check_quality, scan_security |
| **内容创作** | 文案生成 | generate_blog, optimize_seo |
| **数据分析** | 数据处理 | clean_data, statistical_analysis |
| **智能客服** | 用户服务 | answer_faq, create_ticket |
| **学习助手** | 知识问答 | explain_concept, generate_quiz |

---

### 4. 常用 API 调用

**GLM-5**:
```python
from zhipuai import ZhipuAI
client = ZhipuAI(api_key="your-key")
response = client.chat.completions.create(
    model="glm-5",
    messages=[{"role": "user", "content": "你好"}]
)
```

**DeepSeek (via LiteLLM)**:
```python
from litellm import completion
response = completion(
    model="deepseek/deepseek-chat",
    messages=[{"role": "user", "content": "你好"}]
)
```

---

### 5. 工具注册格式

```python
tool_schema = {
    "type": "function",
    "function": {
        "name": "skill_name",
        "description": "技能描述",
        "parameters": {
            "type": "object",
            "properties": {
                "param1": {
                    "type": "string",
                    "description": "参数描述"
                }
            },
            "required": ["param1"]
        }
    }
}
```

---

### 6. 多 Agent 协作模式

```
Orchestrator (调度器)
   ├─ Agent A (收集员)
   ├─ Agent B (分析师)
   └─ Agent C (报告员)
```

**核心原则**: 轻 Prompt + 重 Skill

---

### 7. 记忆系统层级

| 层级 | 用途 | 生命周期 |
|------|------|----------|
| **短期记忆** | 当前会话 | 会话结束 |
| **长期记忆** | 持久化存储 | 永久 |
| **情景记忆** | 事件序列 | 可配置 |

---

### 8. 错误处理模板

```python
try:
    result = skill(**params)
    return {"success": True, "data": result}
except Exception as e:
    return {"success": False, "error": str(e)}
```

---

### 9. 性能优化技巧

1. **缓存结果** - 避免重复调用
2. **批量处理** - 减少API次数
3. **异步执行** - 提高响应速度
4. **工具链组合** - 减少交互次数

---

### 10. 部署检查清单

- [ ] 安装 LiteLLM (`pip install litellm`)
- [ ] 配置 API Key
- [ ] 测试连接
- [ ] 添加真实 Skill
- [ ] 配置错误处理
- [ ] 设置日志记录
- [ ] 性能测试
- [ ] 部署到生产环境

---

## 🚀 快速开始命令

### 创建新 Agent
```bash
cd ~/openclaw-agents
mkdir my-agent
cd my-agent
# 创建 SOUL.md
# 添加 skills/
# 运行 deploy.sh
```

### 测试 Function Calling
```python
python /tmp/litellm-multi-agent-demo/complete_loop_demo.py
```

### 查看案例
```python
python /tmp/real-world-cases/real_world_cases.py
```

---

## 📚 文档索引

| 文档 | 路径 | 内容 |
|------|------|------|
| **开发指南** | memory/multi-agent-development-guide-2026-03-24.md | 架构设计 |
| **GLM-5 集成** | memory/glm5-integration-plan-2026-03-24.md | 三大路径 |
| **实战案例** | /tmp/real-world-cases/real_world_cases.py | 20个案例 |
| **最佳实践** | /tmp/agent-best-practices/best_practices_agents.py | 10个模板 |
| **高级功能** | /tmp/advanced-features/advanced_agent.py | 完整实现 |

---

## 💡 常见问题速查

**Q: 如何降低成本？**
A: 使用 DeepSeek + 本地 Skill，成本降低 99.9%

**Q: 如何提高准确率？**
A: 完善 tool_schema 描述 + 本地 Skill 测试

**Q: 如何扩展功能？**
A: 添加新 Skill → 注册到 tool_schema → 测试

**Q: 如何处理错误？**
A: 统一错误格式 + 完善异常处理 + 日志记录

**Q: 如何优化性能？**
A: 缓存 + 批量 + 异步 + 工具链

---

## 🎯 最佳实践清单

✅ 单一职责 - 每个 Agent 专注一个领域
✅ 模块化 - Skill 独立可测试
✅ 统一接口 - 标准化输入输出
✅ 错误处理 - 完善的异常捕获
✅ 日志记录 - 便于调试和优化
✅ 文档完整 - 清晰的使用说明
✅ 测试覆盖 - 单元测试 + 集成测试
✅ 性能监控 - 响应时间 + 成本追踪

---

**大佬，快速参考卡完成！一页纸掌握核心知识！** 🚀
