# AI Agent 完整迁移指南

> **版本**: v1.0
> **更新时间**: 2026-03-27 14:10
> **迁移场景**: 20+

---

## 🔄 迁移场景

### 场景 1: 从 v1.0 迁移到 v2.0

**兼容性检查**:
```python
# 1. 检查 API 兼容性
def check_api_compatibility():
    """检查 API 兼容性"""
    v1_endpoints = get_v1_endpoints()
    v2_endpoints = get_v2_endpoints()
    
    missing = set(v1_endpoints) - set(v2_endpoints)
    
    if missing:
        print(f"⚠️ 缺失的端点: {missing}")
    
    return len(missing) == 0

# 2. 检查数据兼容性
def check_data_compatibility():
    """检查数据兼容性"""
    v1_schema = get_v1_schema()
    v2_schema = get_v2_schema()
    
    # 检查字段
    for table, fields in v1_schema.items():
        v2_fields = v2_schema.get(table, {})
        
        for field, type_ in fields.items():
            if field not in v2_fields:
                print(f"⚠️ 缺失字段: {table}.{field}")
            elif v2_fields[field] != type_:
                print(f"⚠️ 类型不匹配: {table}.{field}")
    
    return True
```

**迁移步骤**:
```bash
# 1. 备份数据
pg_dump agent > backup_v1.sql

# 2. 更新代码
git pull origin main
pip install -r requirements.txt

# 3. 运行迁移脚本
python scripts/migrate_v1_to_v2.py

# 4. 验证
python scripts/validate_migration.py

# 5. 回滚（如果失败）
python scripts/rollback_v1.py
```

---

### 场景 2: 从 OpenAI 迁移到 Claude

**代码迁移**:
```python
# v1: OpenAI
from openai import OpenAI

client = OpenAI()

def generate(prompt):
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# v2: Claude
from anthropic import Anthropic

client = Anthropic()

def generate(prompt):
    response = client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text
```

**适配器模式**:
```python
class LLMAdapter:
    """LLM 适配器"""
    
    def __init__(self, provider: str):
        self.provider = provider
        
        if provider == "openai":
            self.client = OpenAI()
        elif provider == "claude":
            self.client = Anthropic()
    
    def generate(self, prompt: str) -> str:
        """统一接口"""
        if self.provider == "openai":
            return self._openai_generate(prompt)
        elif self.provider == "claude":
            return self._claude_generate(prompt)
    
    def _openai_generate(self, prompt):
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    
    def _claude_generate(self, prompt):
        response = self.client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
```

---

### 场景 3: 从 SQLite 迁移到 PostgreSQL

**数据迁移**:
```python
import sqlite3
import psycopg2

def migrate_sqlite_to_postgres():
    """从 SQLite 迁移到 PostgreSQL"""
    
    # 1. 连接
    sqlite_conn = sqlite3.connect("agent.db")
    postgres_conn = psycopg2.connect("postgresql://...")
    
    # 2. 获取所有表
    tables = sqlite_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    
    # 3. 迁移每个表
    for (table,) in tables:
        # 获取数据
        rows = sqlite_conn.execute(f"SELECT * FROM {table}").fetchall()
        
        # 插入到 PostgreSQL
        for row in rows:
            postgres_conn.execute(
                f"INSERT INTO {table} VALUES ({','.join(['%s']*len(row))})",
                row
            )
    
    # 4. 提交
    postgres_conn.commit()
    
    print(f"✅ 迁移完成: {len(tables)} 个表")
```

---

### 场景 4: 从单机迁移到 Kubernetes

**Docker 化**:
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "main.py"]
```

**Kubernetes 配置**:
```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: agent
  template:
    metadata:
      labels:
        app: agent
    spec:
      containers:
      - name: agent
        image: agent:v1.0
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: agent-secrets
              key: database-url
```

---

### 场景 5: 从 ChromaDB 迁移到 Pinecone

**数据导出**:
```python
import chromadb

def export_from_chroma():
    """从 ChromaDB 导出"""
    client = chromadb.Client()
    collection = client.get_collection("documents")
    
    # 获取所有数据
    results = collection.get(include=["embeddings", "documents", "metadatas"])
    
    return {
        "ids": results["ids"],
        "embeddings": results["embeddings"],
        "documents": results["documents"],
        "metadatas": results["metadatas"]
    }
```

**数据导入**:
```python
import pinecone

def import_to_pinecone(data):
    """导入到 Pinecone"""
    pinecone.init(api_key="...", environment="us-west1-gcp")
    
    index = pinecone.Index("documents")
    
    # 批量上传
    vectors = [
        (id_, embedding, metadata)
        for id_, embedding, metadata in zip(
            data["ids"],
            data["embeddings"],
            data["metadatas"]
        )
    ]
    
    index.upsert(vectors)
    
    print(f"✅ 导入完成: {len(vectors)} 个向量")
```

---

## 📊 迁移清单

### 迁移前

- [ ] 数据备份
- [ ] 代码备份
- [ ] 配置备份
- [ ] 兼容性检查
- [ ] 依赖检查
- [ ] 测试环境准备

### 迁移中

- [ ] 执行迁移脚本
- [ ] 监控进度
- [ ] 记录错误
- [ ] 性能监控
- [ ] 日志记录

### 迁移后

- [ ] 数据验证
- [ ] 功能测试
- [ ] 性能测试
- [ ] 安全测试
- [ ] 用户验收

---

## 🔧 迁移工具

### 1. 数据迁移工具

```python
class DataMigrator:
    """数据迁移工具"""
    
    def __init__(self, source, target):
        self.source = source
        self.target = target
    
    def migrate(self, table: str):
        """迁移表"""
        # 1. 获取源数据
        data = self.source.get(table)
        
        # 2. 转换格式
        converted = self._convert(data)
        
        # 3. 插入目标
        self.target.insert(table, converted)
        
        return len(converted)
    
    def _convert(self, data):
        """格式转换"""
        # 实现转换逻辑
        return data
```

---

**生成时间**: 2026-03-27 14:15 GMT+8
