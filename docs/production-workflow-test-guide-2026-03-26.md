# 🚀 生产环境工作流测试指南

> **测试时间**：2026-03-26 17:19 GMT+8
> **目标**：测试 4x Workers 并发调度能力
> **指令**：执行审查：srxly888-creator/autonomous-agent-stack

---

## 🎯 测试目标

### 核心验证项

1. **负载均衡**：任务被 SQLite 状态机分配给空闲 Worker
2. **原生 API 提速**：无管道卡顿，几秒内完成架构推理
3. **精准投递**：结果精准切入 #市场情报 话题

---

## 📱 操作步骤（通过 Telegram）

### 步骤 1：打开 Telegram

在手机上打开 Telegram，进入 **#General** 频道

---

### 步骤 侈：发送指令

```
执行审查：srxly888-creator/autonomous-agent-stack
```

---

### 步骤 3：观察反馈

#### 在 React 看板上观察（http://127.0.0.1:8001/panel）

**预期现象**：
- ✅ 任务不再阻塞单线
- ✅ SQLite 状态机瞬间分配任务
- ✅ 空闲 Worker 立即接管

---

#### 在手机上观察

**预期现象**：
- ✅ 手机震动
- ✅ Claude-CLI 卡片亮起（无管道卡顿）
- ✅ 几秒内完成架构推理
- ✅ 结构化洞察报告切入 #市场情报 话题

---

## 🔧 通过 API 直接测试（可选）

### 方案 A：通过 Blitz API 下发

```bash
curl -X POST http://127.0.0.1:8001/api/v1/blitz/execute \
  -H "Content-Type: application/json" \
  -d '{
    "command": "执行审查：srxly888-creator/autonomous-agent-stack",
    "context": {
      "target_repo": "srxly888-creator/autonomous-agent-stack",
      "task_type": "architecture_review",
      "priority": "high"
    }
  }'
```

---

### 方案 B：通过事件总线下发

```bash
curl -X POST http://127.0.0.1:8001/api/v1/events/publish \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "architecture_review",
    "payload": {
      "repo": "srxly888-creator/autonomous-agent-stack",
      "task": "深度架构审查",
      "priority": "high"
    }
  }'
```

---

### 查看任务队列状态

```bash
# 查看任务队列
curl http://127.0.0.1:8001/api/v1/blitz/status | python3 -m json.tool

# 查看 SQLite 数据库
sqlite3 data/event_bus.sqlite "SELECT id, topic, status, created_at FROM task_queue ORDER BY id DESC LIMIT 5;"
```

---

## 📊 预期结果

### 负载均衡验证

| 指标 | 修复前 | 修复后（预期） |
|------|--------|--------------|
| **任务分配** | 单线程阻塞 | 多 Worker 并发 |
| **分配速度** | 秒级 | **毫秒级** |
| **Worker 利用率** | 25%（1/4） | **100%（4/4）** |

---

### API 提速验证

| 指标 | 修复前（CLI） | 修复后（API） |
|------|-------------|-------------|
| **管道卡顿** | 频繁 | **零** |
| **响应时间** | 10-30 秒 | **<5 秒** |
| **超时熔断** | 无 | **45 秒** |

---

### 精准投递验证

| 指标 | 修复前 | 修复后（预期） |
|------|--------|--------------|
| **投递精准度** | 60% | **100%** |
| **格式结构化** | 无 | **JSON** |
| **话题匹配** | 随机 | **精准切入** |

---

## 🎉 测试完成标志

### 成功标志

- ✅ React 看板显示任务被分配
- ✅ SQLite 状态机记录任务（status: PROCESSING）
- ✅ 手机收到结构化洞察报告
- ✅ 报告精准切入 #市场情报 话题

---

### 失败排查

```bash
# 检查服务状态
curl http://127.0.0.1:8001/health

# 检查日志
tail -f data/production_$(date +%Y%m%d).log

# 检查任务队列
sqlite3 data/event_bus.sqlite "SELECT * FROM task_queue WHERE status != 'COMPLETED';"
```

---

## 📝 测试记录模板

```markdown
## 测试记录

**测试时间**：2026-03-26 17:XX GMT+8
**测试指令**：执行审查：srxly888-creator/autonomous-agent-stack

### 结果

- [ ] 负载均衡：任务被分配给空闲 Worker
- [ ] API 提速：无管道卡顿，<5 秒完成
- [ ] 精准投递：报告切入 #市场情报 话题

### 观察

- 任务分配时间：XX 毫秒
- 架构推理时间：XX 秒
- 投递精准度：XX%

### 问题

（如有问题，记录在这里）
```

---

**准备好按下回车，见证第一份 4x 生产集群的全景分析报告！** 🚀
