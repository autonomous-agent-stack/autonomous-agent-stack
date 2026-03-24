# AI Job Hunter - 多平台求职工具 🎯

一个强大的 AI 求职工具，支持在多个主流求职平台搜索和管理职位。

## 🌟 支持的平台

- **LinkedIn AI** - 全球最大的职业社交平台
- **Indeed** - 全球最大的求职搜索引擎
- **Glassdoor** - 包含公司评价和薪资信息
- **Hired** - 专注于技术职位的平台
- **AngelList (Wellfound)** - 初创公司和科技职位

## ✨ 核心功能

### 🔍 多平台搜索
- 一次搜索，覆盖多个平台
- 支持关键词、地点、工作类型筛选
- 实时聚合搜索结果

### 💾 职位管理
- 保存感兴趣的职位
- 查看已保存职位列表
- 移除不感兴趣的职位

### 📊 灵活筛选
- 按薪资范围筛选
- 按标签筛选（如：远程、AI、全职）
- 自定义筛选条件

### 📤 多格式导出
- JSON 格式（程序化处理）
- CSV 格式（Excel 打开）
- Markdown 格式（文档分享）

## 🚀 快速开始

### 1. 安装依赖

```bash
cd ai-job-hunter
pip install -r requirements.txt
```

### 2. 配置 API 密钥

编辑 `config.json`，填入各平台的 API 密钥：

```json
{
  "linkedin": {
    "api_key": "your_linkedin_api_key"
  },
  "indeed": {
    "api_key": "your_indeed_api_key",
    "publisher_id": "your_publisher_id"
  }
  // ... 其他平台配置
}
```

**API 密钥获取指南：**

- **LinkedIn**: 访问 [LinkedIn Developer Portal](https://developer.linkedin.com/) 申请 API 访问权限
- **Indeed**: 注册 [Indeed Publisher Program](https://www.indeed.com/publisher)
- **Glassdoor**: 申请 [Glassdoor API Partner](https://www.glassdoor.com/developer/apiOverview.htm)
- **Hired**: 联系 [Hired API Support](https://hired.com/api)
- **AngelList**: 访问 [AngelList API](https://angel.co/api)

### 3. 基本使用

#### 搜索职位

```bash
# 基础搜索
python main.py search "AI Engineer"

# 指定地点
python main.py search "Python Developer" --location "San Francisco"

# 指定平台
python main.py search "Data Scientist" --platforms linkedin indeed

# 远程工作
python main.py search "Machine Learning" --type remote
```

#### 导出搜索结果

```bash
# 导出为 JSON
python main.py search "AI Engineer" --export json

# 导出为 CSV（可在 Excel 中打开）
python main.py search "Python Developer" --export csv --output my_jobs.csv

# 导出为 Markdown（可分享给他人）
python main.py search "Data Scientist" --export markdown --output jobs_report.md
```

#### 管理已保存的职位

```bash
# 查看已保存的职位
python main.py saved --list

# 移除第 3 个已保存的职位
python main.py saved --remove 3
```

## 📖 高级用法

### Python API 使用

```python
from main import JobHunter

# 创建实例
hunter = JobHunter(config_path="config.json")

# 搜索职位
jobs = hunter.search_jobs(
    keywords="AI Engineer",
    location="Remote",
    platforms=["linkedin", "indeed"],
    job_type="remote"
)

# 筛选职位
filtered_jobs = hunter.filter_jobs(
    jobs,
    min_salary=100000,
    required_tags=["AI", "Remote"]
)

# 保存职位
for job in filtered_jobs:
    hunter.save_job(job)

# 导出职位
hunter.export_jobs(filtered_jobs, format="csv", filename="my_jobs.csv")
```

### 自定义筛选条件

```python
# 薪资筛选
jobs = hunter.filter_jobs(jobs, min_salary=100000, max_salary=150000)

# 标签筛选
jobs = hunter.filter_jobs(jobs, required_tags=["AI", "Full-time"])

# 组合筛选
jobs = hunter.filter_jobs(
    jobs,
    min_salary=120000,
    required_tags=["Remote", "AI"]
)
```

## 🎯 使用场景

### 场景 1：批量搜索技术职位

```bash
# 搜索多个技术关键词
for keyword in "AI Engineer" "Python Developer" "Data Scientist"; do
    python main.py search "$keyword" --type remote --export json
done
```

### 场景 2：定期职位监控

创建一个脚本 `monitor_jobs.sh`：

```bash
#!/bin/bash

# 每天搜索新职位
python main.py search "AI Engineer" --location "Remote" --export json --output "jobs_$(date +%Y%m%d).json"

# 筛选并保存高薪职位
# 可以结合其他工具进行自动化处理
```

### 场景 3：生成求职报告

```bash
# 搜索并导出为 Markdown
python main.py search "Machine Learning" --export markdown --output "ml_jobs_report.md"
```

然后可以分享这个报告给猎头或朋友。

## 📝 配置说明

### config.json 完整配置

```json
{
  "linkedin": {
    "api_key": "your_api_key",
    "api_url": "https://api.linkedin.com/v2/jobs"
  },
  "search_preferences": {
    "keywords": "AI Engineer",
    "location": "Remote",
    "job_type": "full-time"
  },
  "filters": {
    "min_salary": 100000,
    "max_salary": null,
    "required_tags": ["AI", "Remote"]
  }
}
```

## 🔧 故障排除

### 问题：搜索返回空结果

**可能原因：**
1. API 密钥未配置或无效
2. 搜索关键词过于具体
3. 地点设置不正确

**解决方案：**
1. 检查 `config.json` 中的 API 密钥
2. 尝试更通用的关键词
3. 使用 "Remote" 或不指定地点

### 问题：无法导出文件

**可能原因：**
1. 文件路径不存在
2. 没有写入权限

**解决方案：**
1. 确保目录存在且可写
2. 使用绝对路径或相对路径

## 📚 扩展功能

### 添加新平台

在 `main.py` 中的 `_search_platform` 方法添加新平台的实现：

```python
def _search_platform(self, platform: str, keywords: str, location: str, job_type: str) -> List[Job]:
    if platform == "new_platform":
        # 实现新平台的搜索逻辑
        jobs = self._call_new_platform_api(keywords, location, job_type)
        return jobs
```

### AI 辅助筛选

可以集成 AI 模型来：
- 分析职位描述的匹配度
- 自动提取关键技能要求
- 生成个性化职位推荐

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 📮 联系方式

如有问题或建议，请提交 Issue。

---

**祝你找到理想的工作！** 🎉
