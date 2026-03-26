# Market Pain Point Extractor - MCP Tool

通用市场痛点探测器，从多平台社交媒体提取和分析用户痛点。

## 功能

1. **多平台抓取**：支持 Twitter、Reddit、微博等平台
2. **噪音过滤**：智能识别和过滤营销水军、垃圾内容
3. **情感分析**：自动分析文本情感极性（正面/负面/中立）
4. **报告生成**：生成结构化 JSON 报告
5. **数据存储**：存储到 SQLite 数据库以便后续分析

## 快速开始

### 基本使用

```python
from src.skills.market_pain_point_extractor import MarketPainPointExtractor

# 创建提取器实例
extractor = MarketPainPointExtractor()

# 执行提取
result = await extractor.execute({
    "platforms": ["twitter", "reddit", "weibo"],
    "keywords": ["卡顿", "报错", "崩溃"],
    "limit": 100
})

# 查看结果
print(f"生成了 {result['stats']['reports_generated']} 份报告")
for report in result["reports"]:
    print(f"[{report['platform']}] {report['keyword']}: {report['text'][:50]}...")
```

### 查询历史报告

```python
# 查询特定平台的负面报告
reports = extractor.get_reports(
    platform="twitter",
    sentiment="negative",
    limit=50
)

for report in reports:
    print(f"{report['timestamp']}: {report['text']}")
```

## 配置

### 关键词配置 (`src/skills/config/keywords.json`)

```json
{
  "pain_points": [
    "卡顿",
    "报错",
    "体验差",
    "崩溃",
    "慢"
  ],
  "platforms": ["twitter", "reddit", "weibo"],
  "noise_filter": {
    "min_length": 10,
    "exclude_keywords": ["广告", "推广", "优惠"],
    "spam_patterns": ["http://", "https://", "代"]
  }
}
```

## 报告格式

```json
{
  "timestamp": "2026-03-26T08:37:00Z",
  "platform": "twitter",
  "keyword": "卡顿",
  "sentiment": "negative",
  "score": 0.85,
  "text": "产品卡顿严重，体验很差",
  "metadata": {
    "user_id": "12345",
    "post_id": "67890",
    "quality_score": 0.8
  }
}
```

## 运行测试

```bash
# 运行所有测试
pytest tests/skills/ -v

# 运行特定测试文件
pytest tests/skills/test_noise_filter.py -v

# 运行集成测试
pytest tests/skills/test_integration.py -v

# 查看测试覆盖率
pytest tests/skills/ --cov=src/skills --cov-report=html
```

## 测试用例

项目包含 **30+ 测试用例**，覆盖：

### 单元测试 (`test_noise_filter.py` - 12 tests)
- ✅ 噪音过滤（短文本、关键词、URL、重复、emoji）
- ✅ 质量评分计算
- ✅ 批量过滤
- ✅ 合法投诉检测
- ✅ 自定义配置

### 单元测试 (`test_market_pain_point_extractor.py` - 13 tests)
- ✅ 初始化和配置加载
- ✅ 数据库初始化
- ✅ Mock 数据生成（Twitter/Reddit/微博）
- ✅ 关键词匹配
- ✅ 情感分析（正面/负面/中立）
- ✅ 报告生成和存储
- ✅ 数据库查询和过滤

### 集成测试 (`test_integration.py` - 10 tests)
- ✅ 完整端到端工作流
- ✅ 多平台处理
- ✅ 噪音过滤验证
- ✅ 情感分布分析
- ✅ 数据库查询
- ✅ 自定义参数覆盖
- ✅ 错误处理
- ✅ 报告质量验证

## 日志

工具使用结构化日志：

```
[Agent-Stack-Bridge] Market skill initialized
[Agent-Stack-Bridge] Fetching data from twitter
[Agent-Stack-Bridge] Filtered 5 noise items
[Agent-Stack-Bridge] Generated report: report_123
```

## MCP 集成

作为 MCP 工具使用：

```python
from src.skills.market_pain_point_extractor import MCPMarketPainPointExtractor

mcp_tool = MCPMarketPainPointExtractor()
result = await mcp_tool(context)
```

## 数据库

报告存储在 SQLite 数据库中：

```sql
-- 查询最近的负面报告
SELECT * FROM pain_point_reports
WHERE sentiment = 'negative'
ORDER BY timestamp DESC
LIMIT 100;

-- 按关键词统计
SELECT keyword, COUNT(*) as count
FROM pain_point_reports
GROUP BY keyword
ORDER BY count DESC;
```

## 扩展

### 添加新平台

1. 在 `_fetch_from_platform` 添加平台逻辑
2. 创建对应的 `_mock_<platform>_data` 方法
3. 在配置文件中添加平台名称

### 添加真实 API 集成

替换 mock 数据生成方法为实际 API 调用：

```python
async def _fetch_from_platform(self, platform, keywords, limit, since_date):
    if platform == "twitter":
        return await self._fetch_from_twitter_api(keywords, limit)
    # ...
```

## 许可

MIT License
