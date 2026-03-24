# AI + 影刀自动化集成指南

> **目标**: 用 AI 指挥影刀 RPA，实现全自动业务流程
> **投资**: 5万软件 → 最大化价值
> **时间**: 2026-03-24

---

## 🎯 核心思路

```
AI 大脑 → 影刀 API → 机器人执行 → 结果返回 → AI 处理
```

**AI 的角色**:
1. 决策引擎 - 判断何时启动任务
2. 参数生成 - 为影刀任务生成动态参数
3. 结果处理 - 分析任务输出，触发下一步
4. 异常处理 - 任务失败时自动重试或报警

---

## 🔧 API 完整链路

### 1. 鉴权（获取 Token）

```python
import requests

def get_access_token(access_key_id, access_key_secret):
    """获取访问令牌"""
    url = "https://api.yingdao.com/oapi/token/v2/token/create"
    params = {
        "accessKeyId": access_key_id,
        "accessKeySecret": access_key_secret
    }
    response = requests.get(url, params=params)
    data = response.json()
    
    if data["success"]:
        return data["data"]["accessToken"]
    else:
        raise Exception(f"获取 token 失败: {data['msg']}")
```

### 2. 启动任务（AI 指挥）

```python
def start_yingdao_task(token, schedule_uuid, robot_params):
    """
    AI 启动影刀任务
    
    Args:
        token: 访问令牌
        schedule_uuid: 任务 UUID（在影刀控制台获取）
        robot_params: 应用运行参数（AI 生成）
    
    Returns:
        task_uuid: 任务运行 UUID
    """
    url = "https://api.yingdao.com/oapi/dispatch/v2/task/start"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # AI 生成的参数
    payload = {
        "scheduleUuid": schedule_uuid,
        "idempotentUuid": str(uuid.uuid4()),  # 幂等性
        "scheduleRelaParams": [{
            "robotUuid": robot_params["robot_uuid"],
            "params": robot_params["params"]  # AI 生成的参数
        }]
    }
    
    response = requests.post(url, headers=headers, json=payload)
    data = response.json()
    
    if data["success"]:
        return data["data"]["taskUuid"]
    else:
        raise Exception(f"启动任务失败: {data['msg']}")
```

### 3. 查询结果（AI 监控）

```python
import time

def query_task_result(token, task_uuid, max_wait=300):
    """
    AI 轮询任务结果
    
    Args:
        token: 访问令牌
        task_uuid: 任务运行 UUID
        max_wait: 最大等待时间（秒）
    
    Returns:
        任务结果
    """
    url = "https://api.yingdao.com/oapi/dispatch/v2/task/query"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    start_time = time.time()
    
    while True:
        payload = {"taskUuid": task_uuid}
        response = requests.post(url, headers=headers, json=payload)
        data = response.json()
        
        if not data["success"]:
            raise Exception(f"查询失败: {data['msg']}")
        
        task_status = data["data"]["status"]
        
        # 检查是否终态
        if task_status in ["finish", "failed", "canceled"]:
            return data["data"]
        
        # 超时检查
        if time.time() - start_time > max_wait:
            raise Exception("任务超时")
        
        # AI 等待 5 秒后继续轮询
        time.sleep(5)
```

### 4. 停止任务（AI 控制）

```python
def stop_task(token, task_uuid):
    """AI 停止任务"""
    url = "https://api.yingdao.com/oapi/dispatch/v2/task/stop"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {"taskUuid": task_uuid}
    
    response = requests.post(url, headers=headers, json=payload)
    return response.json()
```

---

## 🤖 AI + 影刀 实战场景

### 场景 1: AI 数据分析 + 影刀自动化

**流程**:
```
1. AI 分析业务数据 → 发现异常订单
2. AI 调用影刀 API → 启动"订单处理"任务
3. 影刀机器人执行 → 自动登录系统、处理订单
4. AI 查询结果 → 分析处理结果
5. AI 决策 → 触发下一步操作
```

**代码示例**:
```python
# AI 分析数据
def analyze_orders():
    """AI 分析订单数据"""
    # 这里用 AI 分析订单
    # ...
    return ["order_1", "order_2", "order_3"]

# AI 指挥影刀处理
def ai_process_orders():
    token = get_access_token(KEY_ID, KEY_SECRET)
    
    # AI 分析出异常订单
    abnormal_orders = analyze_orders()
    
    # AI 生成影刀参数
    robot_params = {
        "robot_uuid": "your_robot_uuid",
        "params": [
            {
                "name": "order_list",
                "value": ",".join(abnormal_orders),  # AI 生成的订单列表
                "type": "str"
            }
        ]
    }
    
    # AI 启动影刀任务
    task_uuid = start_yingdao_task(token, SCHEDULE_UUID, robot_params)
    
    # AI 监控任务
    result = query_task_result(token, task_uuid)
    
    # AI 处理结果
    if result["status"] == "finish":
        print("✅ 订单处理完成")
        # AI 继续下一步...
    else:
        print("❌ 订单处理失败")
        # AI 报警或重试...
```

### 场景 2: AI 监控 + 影刀自动化

**流程**:
```
1. AI 监控系统状态 → 发现服务器负载过高
2. AI 调用影刀 API → 启动"服务器运维"任务
3. 影刀机器人执行 → 自动扩容、清理日志
4. AI 查询结果 → 验证负载降低
5. AI 决策 → 继续监控或进一步操作
```

### 场景 3: AI 内容生成 + 影刀发布

**流程**:
```
1. AI 生成内容 → 文章、图片、视频
2. AI 调用影刀 API → 启动"内容发布"任务
3. 影刀机器人执行 → 自动登录平台、发布内容
4. AI 查询结果 → 确认发布成功
5. AI 决策 → 推广或优化内容
```

---

## 💡 AI 增强影刀的关键点

### 1. 动态参数生成

**传统方式**: 固定参数，手动配置
**AI 方式**: 动态生成，智能决策

```python
# AI 生成参数
def ai_generate_params(context):
    """根据上下文动态生成参数"""
    if context["type"] == "urgent":
        return {
            "name": "priority",
            "value": "high",
            "type": "str"
        }
    else:
        return {
            "name": "priority",
            "value": "normal",
            "type": "str"
        }
```

### 2. 智能调度

**传统方式**: 定时触发
**AI 方式**: 智能判断触发时机

```python
# AI 智能调度
def ai_scheduler():
    """AI 判断何时启动任务"""
    # AI 分析业务指标
    metrics = get_business_metrics()
    
    if metrics["order_volume"] > 1000:
        # AI 决定启动影刀任务
        start_yingdao_task(...)
    elif metrics["error_rate"] > 0.1:
        # AI 决定启动监控任务
        start_yingdao_task(...)
    else:
        # AI 决定不启动
        pass
```

### 3. 结果智能处理

**传统方式**: 简单判断成功/失败
**AI 方式**: 深度分析，触发链式反应

```python
# AI 智能处理结果
def ai_process_result(result):
    """AI 分析结果并决策"""
    if result["status"] == "finish":
        # AI 分析输出参数
        output = result["jobDataList"][0]["robotParams"]["outputs"]
        
        if output["quality_score"] < 0.8:
            # AI 决定重新处理
            start_yingdao_task(...)
        else:
            # AI 触发下一个任务
            start_next_task(...)
```

---

## 📊 价值最大化策略

### 1. 高频场景自动化

**识别高频重复任务**:
- 数据采集
- 报表生成
- 系统巡检
- 内容发布

**用 AI + 影刀实现 7x24 自动化**

### 2. 复杂流程编排

**多任务协同**:
```
任务 A（数据采集）
  ↓
AI 分析数据
  ↓
任务 B（数据处理）
  ↓
AI 验证结果
  ↓
任务 C（结果发布）
```

### 3. 智能异常处理

**AI 监控 + 自动修复**:
```
监控异常 → AI 分析 → 启动修复任务 → 验证结果 → 继续监控
```

---

## 🎯 实施步骤

### Step 1: 准备工作

1. **获取 API Key**:
   - 登录影刀控制台
   - 创建 `accessKeyId` 和 `accessKeySecret`

2. **创建任务**:
   - 在控制台创建任务
   - 配置应用和机器人
   - 获取 `scheduleUuid`

3. **测试 API**:
   - 使用 PostMan 测试 API
   - 验证参数和响应

### Step 2: 开发集成

1. **实现鉴权**:
   ```python
   token = get_access_token(KEY_ID, KEY_SECRET)
   ```

2. **启动任务**:
   ```python
   task_uuid = start_yingdao_task(token, SCHEDULE_UUID, params)
   ```

3. **查询结果**:
   ```python
   result = query_task_result(token, task_uuid)
   ```

### Step 3: AI 增强

1. **参数智能生成**:
   - AI 分析业务场景
   - 动态生成参数

2. **结果智能处理**:
   - AI 分析任务输出
   - 触发下一步操作

3. **异常智能处理**:
   - AI 监控任务状态
   - 自动重试或报警

---

## 🚀 高级应用

### 1. AI 编排多个任务

```python
def ai_orchestrate_workflow():
    """AI 编排多个影刀任务"""
    
    # 任务 1: 数据采集
    task1_uuid = start_yingdao_task(token, TASK1_UUID, params1)
    result1 = query_task_result(token, task1_uuid)
    
    # AI 分析结果
    data = ai_analyze(result1)
    
    # 任务 2: 数据处理（基于任务 1 结果）
    params2 = ai_generate_params(data)
    task2_uuid = start_yingdao_task(token, TASK2_UUID, params2)
    result2 = query_task_result(token, task2_uuid)
    
    # 任务 3: 结果发布
    # ...
```

### 2. AI + 影刀 + 大模型

```python
# 结合大模型实现智能自动化
def ai_intelligent_automation(user_request):
    """用户自然语言 → AI 理解 → 影刀执行"""
    
    # 1. AI 理解用户意图
    intent = llm_understand(user_request)
    
    # 2. AI 生成影刀参数
    params = llm_generate_params(intent)
    
    # 3. AI 启动影刀任务
    task_uuid = start_yingdao_task(token, SCHEDULE_UUID, params)
    
    # 4. AI 查询结果
    result = query_task_result(token, task_uuid)
    
    # 5. AI 总结结果给用户
    summary = llm_summarize(result)
    return summary
```

---

## 📈 ROI 计算

**投入**: 5万软件
**产出**:
- 节省人力: 2 人 × 10万/年 = 20万/年
- 提升效率: 3 倍
- 减少错误: 90%

**回本周期**: 3 个月

---

## 🔗 相关资源

- **API 文档**: `knowledge/yingdao/API-Documentation.md`
- **鉴权文档**: `knowledge/yingdao/API-Authentication.md`
- **CLI 工具**: `tools/yingdao_cli.py`

---

**更新时间**: 2026-03-24 19:35
**状态**: ✅ 完整方案已就绪，等待 API Key 测试
