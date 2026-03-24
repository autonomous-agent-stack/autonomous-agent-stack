# 🔍 知识索引系统设计

> **创建时间**: 2026-03-24
> **目标**: 建立完整知识索引，支持快速检索

---

## 📊 索引体系架构

```
知识索引系统
├── 字幕索引（803 个 VTT）
│   ├── 主题索引
│   ├── 关键词索引
│   └── 时间索引
├── 笔记索引（322 个 MD）
│   ├── 标签索引
│   ├── 内容索引
│   └── 关联索引
├── 书签索引（58 个）
│   ├── 主题索引
│   ├── 价值索引
│   └── 来源索引
└── 仓库索引（50 个 Fork）
    ├── Stars 索引
    ├── 更新索引
    └── 分类索引
```

---

## 1. 字幕索引（803 个）

### 1.1 主题索引

**生成脚本**: `/tmp/generate-subtitle-index.py`

```python
import os
import json
from pathlib import Path

def generate_subtitle_index():
    """
    生成字幕主题索引
    
    Returns:
        {
            "01-artificial-intelligence": {
                "count": 27,
                "channels": {
                    "bestpartners": 10,
                    "diaryofaceo": 12,
                    "wowinsight": 5
                },
                "keywords": ["AI", "机器学习", "深度学习"]
            }
        }
    """
    index = {}
    base_path = Path("/tmp/youtube-subtitles-classified-v2")
    
    for category_dir in base_path.iterdir():
        if category_dir.is_dir() and category_dir.name.startswith("0"):
            category_name = category_dir.name
            index[category_name] = {
                "count": 0,
                "channels": {},
                "keywords": extract_keywords(category_name)
            }
            
            for channel_dir in category_dir.iterdir():
                if channel_dir.is_dir():
                    channel_name = channel_dir.name.replace("-subtitles", "")
                    vtt_count = len(list(channel_dir.glob("*.vtt")))
                    index[category_name]["count"] += vtt_count
                    index[category_name]["channels"][channel_name] = vtt_count
    
    return index

def extract_keywords(category_name):
    """提取分类关键词"""
    keyword_map = {
        "01-artificial-intelligence": ["AI", "机器学习", "深度学习", "模型", "训练"],
        "02-vibe-coding-ai-tips": ["Prompt", "Cursor", "ChatGPT", "Claude", "AI工具"],
        "03-health-wellness": ["健康", "营养", "运动", "心理", "睡眠"],
        "04-life": ["创业", "财富", "心理学", "职业", "人际关系"]
    }
    return keyword_map.get(category_name, [])
```

**输出示例**: `/tmp/subtitle-index.json`

```json
{
  "01-artificial-intelligence": {
    "count": 27,
    "channels": {
      "bestpartners": 10,
      "diaryofaceo": 12,
      "wowinsight": 5
    },
    "keywords": ["AI", "机器学习", "深度学习", "模型", "训练"]
  },
  "02-vibe-coding-ai-tips": {
    "count": 557,
    "channels": {
      "bestpartners": 26,
      "diaryofaceo": 524,
      "wowinsight": 7
    },
    "keywords": ["Prompt", "Cursor", "ChatGPT", "Claude", "AI工具"]
  },
  "03-health-wellness": {
    "count": 68,
    "channels": {
      "diaryofaceo": 68
    },
    "keywords": ["健康", "营养", "运动", "心理", "睡眠"]
  },
  "04-life": {
    "count": 151,
    "channels": {
      "bestpartners": 1,
      "diaryofaceo": 150
    },
    "keywords": ["创业", "财富", "心理学", "职业", "人际关系"]
  }
}
```

---

### 1.2 关键词索引

**生成脚本**: `/tmp/generate-keyword-index.py`

```python
import re
from collections import defaultdict

def generate_keyword_index(vtt_path: str):
    """
    从 VTT 文件提取关键词
    
    Args:
        vtt_path: VTT 文件路径
    
    Returns:
        {
            "AI": {"count": 50, "files": ["file1.vtt", "file2.vtt"]},
            "Prompt": {"count": 30, "files": ["file3.vtt"]}
        }
    """
    keyword_index = defaultdict(lambda: {"count": 0, "files": []})
    
    # 读取 VTT 内容
    with open(vtt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取关键词（简化版）
    keywords = [
        "AI", "机器学习", "深度学习", "Prompt", "ChatGPT", "Claude",
        "Cursor", "OpenClaw", "Agent", "Skill", "记忆系统", "MSA",
        "健康", "营养", "运动", "创业", "财富", "心理学"
    ]
    
    for keyword in keywords:
        count = len(re.findall(keyword, content, re.IGNORECASE))
        if count > 0:
            keyword_index[keyword]["count"] += count
            keyword_index[keyword]["files"].append(os.path.basename(vtt_path))
    
    return dict(keyword_index)
```

**输出示例**: `/tmp/keyword-index.json`

```json
{
  "AI": {
    "count": 1500,
    "files": ["file1.vtt", "file2.vtt", "file3.vtt"]
  },
  "Prompt": {
    "count": 800,
    "files": ["file4.vtt", "file5.vtt"]
  },
  "OpenClaw": {
    "count": 500,
    "files": ["file6.vtt", "file7.vtt"]
  }
}
```

---

## 2. 笔记索引（322 个）

### 2.1 标签索引

**生成脚本**: `/tmp/generate-note-index.py`

```python
import os
import re
from pathlib import Path

def generate_note_index():
    """
    生成笔记标签索引
    
    Returns:
        {
            "AI工具": {
                "count": 50,
                "notes": ["note1.md", "note2.md"]
            },
            "Prompt工程": {
                "count": 30,
                "notes": ["note3.md"]
            }
        }
    """
    tag_index = defaultdict(lambda: {"count": 0, "notes": []})
    notes_path = Path("/Users/iCloud_GZ/github_GZ/openclaw-memory/youtube-notes")
    
    for note_file in notes_path.glob("*.md"):
        with open(note_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取标签（从 YAML frontmatter 或正文）
        tags = extract_tags(content)
        
        for tag in tags:
            tag_index[tag]["count"] += 1
            tag_index[tag]["notes"].append(note_file.name)
    
    return dict(tag_index)

def extract_tags(content: str):
    """提取标签"""
    # 从 YAML frontmatter 提取
    frontmatter_match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
    if frontmatter_match:
        frontmatter = frontmatter_match.group(1)
        tags_match = re.search(r'tags:\s*\[(.*?)\]', frontmatter)
        if tags_match:
            return [tag.strip() for tag in tags_match.group(1).split(',')]
    
    # 从正文提取（简化版）
    keywords = ["AI", "Prompt", "Cursor", "ChatGPT", "Claude", "OpenClaw"]
    return [kw for kw in keywords if kw in content]
```

**输出示例**: `/tmp/note-index.json`

```json
{
  "AI工具": {
    "count": 50,
    "notes": ["note1.md", "note2.md"]
  },
  "Prompt工程": {
    "count": 30,
    "notes": ["note3.md"]
  },
  "OpenClaw": {
    "count": 20,
    "notes": ["note4.md"]
  }
}
```

---

## 3. 书签索引（58 个）

### 3.1 价值索引

**生成脚本**: `/tmp/generate-bookmark-index.py`

```python
def generate_bookmark_index():
    """
    生成书签价值索引
    
    Returns:
        {
            "high_priority": [
                {
                    "title": "WiFi-DensePose",
                    "likes": 2064,
                    "bookmarks": 3195,
                    "url": "xxx"
                }
            ],
            "medium_priority": [...],
            "low_priority": [...]
        }
    """
    # 读取书签数据
    bookmarks = load_bookmarks()
    
    # 按价值分类
    index = {
        "high_priority": [],
        "medium_priority": [],
        "low_priority": []
    }
    
    for bookmark in bookmarks:
        score = bookmark["likes"] + bookmark["bookmarks"]
        
        if score > 2000:
            index["high_priority"].append(bookmark)
        elif score > 500:
            index["medium_priority"].append(bookmark)
        else:
            index["low_priority"].append(bookmark)
    
    return index
```

**输出示例**: `/tmp/bookmark-index.json`

```json
{
  "high_priority": [
    {
      "title": "WiFi-DensePose",
      "likes": 2064,
      "bookmarks": 3195,
      "url": "xxx"
    },
    {
      "title": "Notebook LM 深度使用",
      "likes": 1690,
      "bookmarks": 2767,
      "url": "xxx"
    }
  ],
  "medium_priority": [...],
  "low_priority": [...]
}
```

---

## 4. 仓库索引（50 个 Fork）

### 4.1 Stars 索引

**生成脚本**: `/tmp/generate-repo-index.py`

```python
import requests

def generate_repo_index():
    """
    生成仓库 Stars 索引
    
    Returns:
        {
            "top_stars": [
                {
                    "name": "awesome-chatgpt-prompts",
                    "stars": 123000,
                    "url": "xxx"
                }
            ],
            "recently_updated": [...],
            "by_category": {...}
        }
    """
    repos = load_fork_repos()
    
    index = {
        "top_stars": sorted(repos, key=lambda x: x["stars"], reverse=True)[:10],
        "recently_updated": sorted(repos, key=lambda x: x["updated_at"], reverse=True)[:10],
        "by_category": categorize_repos(repos)
    }
    
    return index
```

**输出示例**: `/tmp/repo-index.json`

```json
{
  "top_stars": [
    {
      "name": "awesome-chatgpt-prompts",
      "stars": 123000,
      "url": "xxx"
    }
  ],
  "recently_updated": [...],
  "by_category": {
    "AI工具": [...],
    "开源项目": [...],
    "学习资源": [...]
  }
}
```

---

## 5. 统一搜索接口

### 5.1 搜索 API

```python
from fastapi import FastAPI, Query
from typing import List, Dict

app = FastAPI()

@app.get("/search")
async def search(
    query: str = Query(..., description="搜索关键词"),
    scope: List[str] = Query(["subtitles", "notes", "bookmarks"], description="搜索范围"),
    limit: int = Query(10, description="返回结果数量")
):
    """
    统一搜索接口
    
    Args:
        query: 搜索关键词
        scope: 搜索范围（subtitles/notes/bookmarks/repos）
        limit: 返回结果数量
    
    Returns:
        {
            "results": [
                {
                    "type": "subtitle",
                    "title": "AI 记忆系统详解",
                    "url": "xxx",
                    "relevance": 0.95
                }
            ],
            "total": 100
        }
    """
    results = []
    
    if "subtitles" in scope:
        results.extend(search_subtitles(query, limit))
    
    if "notes" in scope:
        results.extend(search_notes(query, limit))
    
    if "bookmarks" in scope:
        results.extend(search_bookmarks(query, limit))
    
    if "repos" in scope:
        results.extend(search_repos(query, limit))
    
    # 按相关性排序
    results.sort(key=lambda x: x["relevance"], reverse=True)
    
    return {
        "results": results[:limit],
        "total": len(results)
    }

def search_subtitles(query: str, limit: int):
    """搜索字幕"""
    # 使用关键词索引
    keyword_index = load_json("/tmp/keyword-index.json")
    
    results = []
    if query in keyword_index:
        for file in keyword_index[query]["files"][:limit]:
            results.append({
                "type": "subtitle",
                "title": file,
                "url": f"https://github.com/srxly888-creator/youtube-vibe-coding/blob/main/{file}",
                "relevance": keyword_index[query]["count"] / 1000
            })
    
    return results
```

---

## 6. 使用示例

### 示例 1: 搜索 AI 工具相关内容

```bash
curl "http://localhost:8000/search?query=AI工具&scope=subtitles,notes,bookmarks&limit=10"
```

**返回**:
```json
{
  "results": [
    {
      "type": "subtitle",
      "title": "CEO 日记 - AI 工具推荐.vtt",
      "url": "xxx",
      "relevance": 0.95
    },
    {
      "type": "note",
      "title": "AI 工具使用笔记.md",
      "url": "xxx",
      "relevance": 0.90
    },
    {
      "type": "bookmark",
      "title": "20 个 AI 图像生成技巧",
      "url": "xxx",
      "relevance": 0.85
    }
  ],
  "total": 50
}
```

### 示例 2: 按主题浏览

```bash
curl "http://localhost:8000/browse?category=vibe-coding"
```

**返回**:
```json
{
  "category": "vibe-coding",
  "subtitles": 557,
  "notes": 50,
  "bookmarks": 20,
  "repos": 5
}
```

---

## 7. 部署方案

### 7.1 本地部署

```bash
# 生成索引
python /tmp/generate-subtitle-index.py
python /tmp/generate-keyword-index.py
python /tmp/generate-note-index.py
python /tmp/generate-bookmark-index.py
python /tmp/generate-repo-index.py

# 启动服务
uvicorn search_api:app --reload --port 8000
```

### 7.2 Docker 部署

```dockerfile
FROM python:3.11

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "search_api:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 8. 性能优化

### 8.1 缓存策略

```python
from functools import lru_cache
import redis

redis_client = redis.Redis(host='localhost', port=6379, db=0)

@lru_cache(maxsize=1000)
def search_subtitles_cached(query: str):
    """带缓存的字幕搜索"""
    cache_key = f"search:subtitles:{query}"
    cached = redis_client.get(cache_key)
    
    if cached:
        return json.loads(cached)
    
    results = search_subtitles(query, limit=100)
    redis_client.setex(cache_key, 3600, json.dumps(results))
    
    return results
```

### 8.2 索引更新

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('cron', hour=2)
async def update_indexes():
    """每天凌晨 2 点更新索引"""
    generate_subtitle_index()
    generate_keyword_index()
    generate_note_index()
    generate_bookmark_index()
    generate_repo_index()
    print("索引更新完成")
```

---

## 9. 监控与告警

### 9.1 监控指标

```python
from prometheus_client import Counter, Histogram

search_counter = Counter('search_requests_total', 'Total search requests')
search_latency = Histogram('search_latency_seconds', 'Search latency')

@app.get("/search")
@search_latency.time()
async def search(query: str, scope: List[str], limit: int):
    search_counter.inc()
    # ... 搜索逻辑
```

### 9.2 告警规则

```yaml
groups:
  - name: search_alerts
    rules:
      - alert: HighSearchLatency
        expr: histogram_quantile(0.95, rate(search_latency_seconds_bucket[5m])) > 1
        for: 5m
        annotations:
          summary: "搜索延迟过高"
```

---

## 📊 索引统计

| 索引类型 | 数据量 | 更新频率 | 查询延迟 |
|----------|--------|----------|----------|
| 字幕索引 | 803 个 | 每周 | < 100ms |
| 笔记索引 | 322 个 | 每天 | < 50ms |
| 书签索引 | 58 个 | 每小时 | < 10ms |
| 仓库索引 | 50 个 | 每天 | < 50ms |

---

**创建者**: OpenClaw Agent
**创建时间**: 2026-03-24 09:10
**状态**: 🔄 设计完成，待实现
