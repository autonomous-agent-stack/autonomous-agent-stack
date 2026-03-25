# 下一步行动清单 - 2026-03-25 19:57

> **制定时间**: 2026-03-25 19:57 GMT+8
> **优先级**: 🔴 P0（最高）
> **执行时间**: 下一轮

---

## 🔴 P0 任务（最高优先级）

### 任务 1: 持久化评估状态（1-2 天）

**目标**: 从 demo → 可持续使用

#### 实现步骤

**1. SQLite 存储实现**
```python
# autoresearch/shared/storage/database.py
from sqlalchemy import create_engine, Column, String, Float, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class Evaluation(Base):
    """评估记录表"""
    __tablename__ = "evaluations"
    
    id = Column(String, primary_key=True)
    task_id = Column(String, unique=True, index=True)
    type = Column(String)  # "prompt" | "report" | "params"
    status = Column(String)  # "queued" | "running" | "completed" | "failed"
    
    # 输入
    target = Column(JSON)
    criteria = Column(JSON)
    
    # 输出
    scores = Column(JSON)
    result_status = Column(String)  # "pass" | "fail"
    run_id = Column(String)
    duration_seconds = Column(Float)
    metrics = Column(JSON)
    
    # 元数据
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    completed_at = Column(DateTime, nullable=True)

class Database:
    """数据库管理"""
    
    def __init__(self, db_path: str = "autoresearch.db"):
        self.engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
    
    def get_session(self):
        return self.Session()

# 使用示例
db = Database("data/evaluations.db")
```

**2. 仓储层实现**
```python
# autoresearch/shared/storage/repositories/evaluations.py
from typing import Optional, List
from sqlalchemy.orm import Session
from .database import Evaluation

class EvaluationRepository:
    """评估仓储"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, eval_data: dict) -> Evaluation:
        """创建评估记录"""
        evaluation = Evaluation(**eval_data)
        self.session.add(evaluation)
        self.session.commit()
        return evaluation
    
    def get_by_task_id(self, task_id: str) -> Optional[Evaluation]:
        """根据 task_id 查询"""
        return self.session.query(Evaluation).filter(
            Evaluation.task_id == task_id
        ).first()
    
    def update(self, task_id: str, updates: dict) -> Optional[Evaluation]:
        """更新评估记录"""
        evaluation = self.get_by_task_id(task_id)
        if evaluation:
            for key, value in updates.items():
                setattr(evaluation, key, value)
            self.session.commit()
        return evaluation
    
    def list_recent(self, limit: int = 100) -> List[Evaluation]:
        """查询最近记录"""
        return self.session.query(Evaluation).order_by(
            Evaluation.created_at.desc()
        ).limit(limit).all()
```

**3. 服务层集成**
```python
# autoresearch/core/services/evaluations.py
from autoresearch.shared.storage.database import Database
from autoresearch.shared.storage.repositories.evaluations import EvaluationRepository

class EvaluationService:
    """评估服务（持久化版本）"""
    
    def __init__(self):
        self.db = Database("data/evaluations.db")
        self.repo = EvaluationRepository(self.db.get_session())
    
    async def create_evaluation(self, request: dict) -> str:
        """创建评估任务"""
        task_id = generate_task_id()
        
        # 保存到数据库
        self.repo.create({
            "id": task_id,
            "task_id": task_id,
            "type": request["type"],
            "status": "queued",
            "target": request["target"],
            "criteria": request["criteria"]
        })
        
        return task_id
    
    async def get_evaluation(self, task_id: str) -> dict:
        """查询评估结果"""
        evaluation = self.repo.get_by_task_id(task_id)
        
        if not evaluation:
            raise NotFoundError(f"Evaluation {task_id} not found")
        
        return {
            "task_id": evaluation.task_id,
            "status": evaluation.status,
            "scores": evaluation.scores,
            "result_status": evaluation.result_status,
            "run_id": evaluation.run_id,
            "duration_seconds": evaluation.duration_seconds,
            "metrics": evaluation.metrics,
            "created_at": evaluation.created_at.isoformat(),
            "completed_at": evaluation.completed_at.isoformat() if evaluation.completed_at else None
        }
```

**4. API 路由更新**
```python
# autoresearch/api/routers/evaluations.py
from fastapi import APIRouter, BackgroundTasks
from autoresearch.core.services.evaluations import EvaluationService

router = APIRouter()
evaluation_service = EvaluationService()

@router.post("/evaluations")
async def create_evaluation(
    request: EvaluationRequest,
    background_tasks: BackgroundTasks
):
    """创建评估任务（持久化版本）"""
    task_id = await evaluation_service.create_evaluation(request.dict())
    
    # 后台执行
    background_tasks.add_task(
        evaluation_service.execute_evaluation,
        task_id
    )
    
    return {"task_id": task_id, "status": "queued"}

@router.get("/evaluations/{task_id}")
async def get_evaluation(task_id: str):
    """查询评估结果（持久化版本）"""
    result = await evaluation_service.get_evaluation(task_id)
    return result
```

#### 验证标准
- ✅ 服务重启后状态保留
- ✅ 支持历史查询（最近 100 条）
- ✅ 支持数据导出（JSON/CSV）
- ✅ 查询性能 < 100ms

---

### 任务 2: evaluator_command 接入（1-2 天）

**目标**: 灵活配置评估器

#### 实现步骤

**1. 请求模型更新**
```python
# autoresearch/shared/models.py
from pydantic import BaseModel, validator
from typing import Optional, List

class EvaluationRequest(BaseModel):
    """评估请求"""
    type: str  # "prompt" | "report" | "params"
    target: dict
    
    # 新增：支持自定义评估器
    config_path: Optional[str] = None
    evaluator_command: Optional[str] = None
    
    criteria: Optional[List[str]] = ["accuracy", "completeness", "readability"]
    weights: Optional[dict] = None
    
    @validator("config_path", "evaluator_command")
    def check_evaluator(cls, v, values):
        """至少提供一种评估器配置"""
        if not values.get("config_path") and not values.get("evaluator_command"):
            raise ValueError("需要提供 config_path 或 evaluator_command")
        return v
```

**2. 服务层实现**
```python
# autoresearch/core/services/evaluations.py
import subprocess
import tempfile
import os

class EvaluationService:
    """评估服务（支持自定义命令）"""
    
    async def execute_evaluation(self, task_id: str):
        """执行评估（后台任务）"""
        # 更新状态
        self.repo.update(task_id, {"status": "running"})
        
        try:
            # 获取任务信息
            evaluation = self.repo.get_by_task_id(task_id)
            
            # 判断使用哪种评估器
            if evaluation.evaluator_command:
                # 使用自定义命令
                result = await self.run_custom_evaluator(
                    evaluation.evaluator_command,
                    evaluation.target
                )
            else:
                # 使用默认评估器（task.json）
                result = await self.run_default_evaluator(
                    evaluation.config_path,
                    evaluation.target
                )
            
            # 更新结果
            self.repo.update(task_id, {
                "status": "completed",
                "scores": result["scores"],
                "result_status": result["status"],
                "run_id": result["run_id"],
                "duration_seconds": result["duration"],
                "metrics": result["metrics"],
                "completed_at": datetime.now()
            })
        
        except Exception as e:
            # 更新失败状态
            self.repo.update(task_id, {
                "status": "failed",
                "scores": {"error": str(e)},
                "completed_at": datetime.now()
            })
    
    async def run_custom_evaluator(
        self,
        command: str,
        target: dict
    ) -> dict:
        """
        执行自定义评估器命令
        
        Args:
            command: 命令字符串（支持变量替换）
                例如: "python my_evaluator.py --input {{input}} --output {{output}}"
            target: 评估目标（prompt/report/params）
        
        Returns:
            {
                "scores": {"total": 85.5, "breakdown": {...}},
                "status": "pass",
                "run_id": "run_123",
                "duration": 10.5,
                "metrics": {...}
            }
        """
        import time
        start_time = time.time()
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as input_file:
            json.dump(target, input_file)
            input_path = input_file.name
        
        output_path = input_path.replace('.json', '_output.json')
        
        try:
            # 变量替换
            command = command.replace("{{input}}", input_path)
            command = command.replace("{{output}}", output_path)
            
            # 执行命令
            process = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300  # 5 分钟超时
            )
            
            if process.returncode != 0:
                raise Exception(f"Command failed: {process.stderr}")
            
            # 读取输出
            with open(output_path) as f:
                result = json.load(f)
            
            # 计算耗时
            duration = time.time() - start_time
            
            return {
                "scores": result["scores"],
                "status": result.get("status", "pass"),
                "run_id": result.get("run_id", f"run_{int(time.time())}"),
                "duration": duration,
                "metrics": result.get("metrics", {})
            }
        
        finally:
            # 清理临时文件
            if os.path.exists(input_path):
                os.unlink(input_path)
            if os.path.exists(output_path):
                os.unlink(output_path)
```

**3. API 调用示例**
```bash
# 使用自定义评估器
curl -X POST http://localhost:8001/api/v1/evaluations \
  -H "Content-Type: application/json" \
  -d '{
    "type": "report",
    "target": {
      "content": "研究报告内容..."
    },
    "evaluator_command": "python /path/to/my_evaluator.py --input {{input}} --output {{output}}",
    "criteria": ["accuracy", "completeness"]
  }'

# 使用默认评估器（task.json）
curl -X POST http://localhost:8001/api/v1/evaluations \
  -H "Content-Type: application/json" \
  -d '{
    "type": "report",
    "target": {
      "content": "研究报告内容..."
    },
    "config_path": "configs/task.json",
    "criteria": ["accuracy", "completeness"]
  }'
```

#### 验证标准
- ✅ 支持自定义评估器
- ✅ 支持变量替换（{{input}}, {{output}}）
- ✅ 支持错误处理和超时
- ✅ API 文档更新

---

## ⚠️ 实际风险：AppleDouble 文件污染

### 问题描述

**现象**：
- 外置盘反复生成 `._*` 文件
- 污染 `compileall` 结果
- 污染导入结果

**影响**：
- 编译错误
- 导入失败
- Git 状态混乱

### 解决方案

#### 方案 1: 清理脚本

```bash
# ~/.openclaw/scripts/cleanup-appledouble.sh
#!/bin/bash

# AppleDouble 文件清理脚本
# 用于清理 macOS 生成的 ._ 开头的文件

set -e

GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}🧹 开始清理 AppleDouble 文件...${NC}"

# 检查目标目录
TARGET_DIR="${1:-/Volumes/PS1008/Github}"

if [ ! -d "$TARGET_DIR" ]; then
    echo "错误: 目录不存在: $TARGET_DIR"
    exit 1
fi

# 统计数量
COUNT=$(find "$TARGET_DIR" -name "._*" -type f | wc -l | tr -d ' ')

if [ "$COUNT" -eq 0 ]; then
    echo "✅ 未发现 AppleDouble 文件"
    exit 0
fi

echo "发现 $COUNT 个 AppleDouble 文件"

# 删除文件
find "$TARGET_DIR" -name "._*" -type f -delete

echo -e "${GREEN}✅ 已清理 $COUNT 个 AppleDouble 文件${NC}"

# 验证
REMAINING=$(find "$TARGET_DIR" -name "._*" -type f | wc -l | tr -d ' ')
if [ "$REMAINING" -gt 0 ]; then
    echo "⚠️ 仍有 $REMAINING 个文件未清理"
    exit 1
fi
```

#### 方案 2: 启动前检查

```bash
# autoresearch/scripts/pre-start-check.sh
#!/bin/bash

# 启动前检查脚本

set -e

echo "=== 启动前检查 ==="

# 1. 检查 AppleDouble 文件
APPLEDOUBLE_COUNT=$(find /Volumes/PS1008/Github -name "._*" -type f 2>/dev/null | wc -l | tr -d ' ')

if [ "$APPLEDOUBLE_COUNT" -gt 0 ]; then
    echo "⚠️ 发现 $APPLEDOUBLE_COUNT 个 AppleDouble 文件，正在清理..."
    find /Volumes/PS1008/Github -name "._*" -type f -delete
    echo "✅ 已清理"
fi

# 2. 检查 Git 状态
cd /Volumes/PS1008/Github/autoresearch
if git status --porcelain | grep -q "^??"; then
    echo "⚠️ 发现未跟踪文件"
    echo "建议运行: git clean -fd"
fi

# 3. 检查依赖
if ! command -v uv &> /dev/null; then
    echo "❌ uv 未安装"
    exit 1
fi

echo "✅ 启动前检查通过"
```

#### 方案 3: 自动化集成

```python
# autoresearch/scripts/cleanup.py
import os
import subprocess
from pathlib import Path

def cleanup_appledouble(directory: str = "/Volumes/PS1008/Github"):
    """
    清理 AppleDouble 文件
    
    Args:
        directory: 目标目录
    """
    directory = Path(directory)
    
    if not directory.exists():
        print(f"❌ 目录不存在: {directory}")
        return
    
    # 查找所有 ._ 开头的文件
    appledouble_files = list(directory.rglob("._*"))
    
    if not appledouble_files:
        print("✅ 未发现 AppleDouble 文件")
        return
    
    print(f"🧹 发现 {len(appledouble_files)} 个 AppleDouble 文件")
    
    # 删除文件
    for file in appledouble_files:
        try:
            file.unlink()
            print(f"  ✓ {file}")
        except Exception as e:
            print(f"  ✗ {file}: {e}")
    
    print(f"✅ 已清理 {len(appledouble_files)} 个 AppleDouble 文件")

# 在 FastAPI 启动时调用
@app.on_event("startup")
async def startup_event():
    """启动时自动清理"""
    cleanup_appledouble("/Volumes/PS1008/Github")
```

### 验证标准
- ✅ 清理脚本可执行
- ✅ 启动前检查通过
- ✅ 自动化集成到 FastAPI
- ✅ 编译和导入正常

---

## 📋 完整任务清单

### 立即行动（下一轮）
- [ ] **持久化评估状态**（1-2 天）
  - [ ] SQLite 存储实现
  - [ ] 仓储层实现
  - [ ] 服务层集成
  - [ ] API 路由更新
  - [ ] 验证测试

- [ ] **evaluator_command 接入**（1-2 天）
  - [ ] 请求模型更新
  - [ ] 服务层实现
  - [ ] API 调用示例
  - [ ] 验证测试

- [ ] **AppleDouble 清理**（1 小时）
  - [ ] 清理脚本
  - [ ] 启动前检查
  - [ ] 自动化集成
  - [ ] 验证测试

### 后续行动（本周）
- [ ] **Report API 适配 GPT Researcher**（2-3 天）
- [ ] **补充子目录 README**（1 天）
- [ ] **deer-flow 环境部署**（1 天）

---

## 📊 成功指标

### 技术指标
- **重启恢复**: ✅ 服务重启后状态保留
- **查询性能**: < 100ms
- **自定义评估器**: ✅ 支持任意命令
- **AppleDouble 清理**: ✅ 0 个残留文件

### 业务指标
- **评估准确率**: > 85%
- **系统稳定性**: > 99%
- **用户满意度**: > 4.5/5

---

**行动清单生成时间**: 2026-03-25 19:57 GMT+8
**状态**: ✅ 完成
**优先级**: 🔴 P0
**执行时间**: 下一轮
