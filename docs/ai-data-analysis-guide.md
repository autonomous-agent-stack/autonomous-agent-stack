# AI 数据分析完全指南

## 目录

1. [数据收集](#数据收集-10-种方法)
2. [数据清洗](#数据清洗-15-种技巧)
3. [数据探索](#数据探索-10-种方法)
4. [统计分析](#统计分析-10-种方法)
5. [可视化](#可视化-15-种图表)
6. [机器学习](#机器学习-10-种算法)
7. [深度学习](#深度学习-5-种模型)
8. [报告生成](#报告生成-10-种模板)

---

## 数据收集 (10 种方法)

### 1. API 数据采集

**方法描述**: 通过 RESTful API 从第三方服务获取结构化数据

**使用场景**: 
- 获取社交媒体数据
- 金融数据
- 天气信息
- 电商数据

**Python 代码**:
```python
import requests
import pandas as pd

def fetch_api_data(url, params=None):
    """
    从 API 获取数据
    
    参数:
        url: API 端点
        params: 查询参数
    
    返回:
        DataFrame: 格式化的数据
    """
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return pd.DataFrame(data)
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return None

# 示例：获取 GitHub 用户数据
url = "https://api.github.com/users"
params = {"per_page": 10, "since": 0}
df = fetch_api_data(url, params)
print(df.head())
```

**示例数据**:
```python
# GitHub API 返回的示例数据
{
    "login": "mojombo",
    "id": 1,
    "node_id": "MDQ6VXNlcjE=",
    "avatar_url": "https://avatars.githubusercontent.com/u/1?v=4",
    "gravatar_id": "",
    "url": "https://api.github.com/users/mojombo",
    "type": "User"
}
```

**结果解读**: 
- 成功获取结构化的 JSON 数据
- 转换为 DataFrame 便于后续分析
- 注意处理分页和速率限制

---

### 2. 网页爬虫

**方法描述**: 使用 BeautifulSoup 和 Selenium 从网页提取数据

**使用场景**: 
- 抓取新闻文章
- 电商产品信息
- 财经数据
- 社交媒体内容

**Python 代码**:
```python
import requests
from bs4 import BeautifulSoup
import pandas as pd

def scrape_web_data(url, css_selector):
    """
    爬取网页数据
    
    参数:
        url: 目标网页
        css_selector: CSS 选择器
    
    返回:
        list: 提取的数据列表
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')
    elements = soup.select(css_selector)
    
    return [elem.get_text(strip=True) for elem in elements]

# 示例：爬取新闻标题
url = "https://news.example.com"
titles = scrape_web_data(url, "h2.news-title")
df = pd.DataFrame({'title': titles})
print(df.head())
```

**示例数据**:
```python
# 爬取的新闻标题示例
['AI 技术突破：新模型性能提升 50%',
 '全球经济复苏势头强劲',
 '科技公司发布季度财报',
 '新能源产业持续增长']
```

**结果解读**: 
- 成功提取结构化文本内容
- 需遵守网站的 robots.txt 规则
- 注意反爬虫机制（延迟、代理）

---

### 3. 数据库查询

**方法描述**: 使用 SQL 从关系型数据库提取数据

**使用场景**: 
- 企业数据仓库
- 业务系统数据
- 日志数据库
- 用户行为数据

**Python 代码**:
```python
import sqlite3
import pandas as pd

def query_database(db_path, query):
    """
    从数据库查询数据
    
    参数:
        db_path: 数据库文件路径
        query: SQL 查询语句
    
    返回:
        DataFrame: 查询结果
    """
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        print(f"查询失败: {e}")
        return None

# 示例：查询销售数据
query = """
SELECT 
    product_id,
    product_name,
    SUM(quantity) as total_quantity,
    SUM(amount) as total_amount
FROM sales
WHERE sale_date >= '2024-01-01'
GROUP BY product_id, product_name
ORDER BY total_amount DESC
LIMIT 10
"""

df = query_database('sales.db', query)
print(df)
```

**示例数据**:
```python
# 销售数据示例
   product_id product_name  total_quantity  total_amount
0         101      手机          500          2500000
1         102      笔记本        300          1800000
2         103      平板          450          1350000
3         104      耳机          800          400000
```

**结果解读**: 
- 聚合分析显示热销产品
- 总金额排序识别重点产品
- 可进一步计算增长率、利润率

---

### 4. 文件读取

**方法描述**: 从本地文件系统读取各种格式的数据文件

**使用场景**: 
- CSV/Excel 文件
- JSON 文件
- XML 文件
- Parquet 文件

**Python 代码**:
```python
import pandas as pd
import json

def read_file(file_path, file_type='csv'):
    """
    读取不同格式的文件
    
    参数:
        file_path: 文件路径
        file_type: 文件类型 (csv, excel, json, parquet)
    
    返回:
        DataFrame: 数据
    """
    try:
        if file_type == 'csv':
            return pd.read_csv(file_path, encoding='utf-8')
        elif file_type == 'excel':
            return pd.read_excel(file_path)
        elif file_type == 'json':
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return pd.DataFrame(data)
        elif file_type == 'parquet':
            return pd.read_parquet(file_path)
        else:
            raise ValueError(f"不支持的文件类型: {file_type}")
    except Exception as e:
        print(f"读取失败: {e}")
        return None

# 示例：读取 CSV 文件
df = read_file('data/sales_data.csv', 'csv')
print(df.info())
print(df.head())
```

**示例数据**:
```csv
date,product,category,quantity,amount
2024-01-01,手机,电子产品,2,5000
2024-01-01,笔记本,电子产品,1,6000
2024-01-02,耳机,配件,3,300
2024-01-02,平板,电子产品,1,3000
```

**结果解读**: 
- 成功加载结构化数据
- 查看数据类型和基本统计
- 注意编码问题和缺失值

---

### 5. 日志文件解析

**方法描述**: 解析服务器日志、应用日志等非结构化文本

**使用场景**: 
- Web 服务器访问日志
- 应用错误日志
- 系统日志
- 安全审计日志

**Python 代码**:
```python
import re
import pandas as pd
from datetime import datetime

def parse_log_file(log_path, pattern):
    """
    解析日志文件
    
    参数:
        log_path: 日志文件路径
        pattern: 正则表达式模式
    
    返回:
        DataFrame: 解析后的日志数据
    """
    logs = []
    with open(log_path, 'r', encoding='utf-8') as f:
        for line in f:
            match = re.match(pattern, line)
            if match:
                logs.append(match.groupdict())
    
    return pd.DataFrame(logs)

# Apache 访问日志格式
log_pattern = r'(?P<ip>\d+\.\d+\.\d+\.\d+) - - \[(?P<timestamp>.*?)\] "(?P<method>\w+) (?P<path>.*?) .*?" (?P<status>\d+) (?P<size>\d+)'

df = parse_log_file('access.log', log_pattern)
df['timestamp'] = pd.to_datetime(df['timestamp'])
df['status'] = df['status'].astype(int)
df['size'] = df['size'].astype(int)

print(df.head())
print(f"\n状态码分布:\n{df['status'].value_counts()}")
```

**示例数据**:
```python
# 日志解析结果示例
     ip          timestamp method  path  status  size
0  192.168.1.1  2024-01-01 10:00:00  GET  /api/users  200  1024
1  192.168.1.2  2024-01-01 10:00:01  POST /api/login  401  256
2  192.168.1.3  2024-01-01 10:00:02  GET  /api/data   500  128
```

**结果解读**: 
- 提取 IP、时间、请求类型等信息
- 统计状态码识别异常
- 分析访问模式和热点资源

---

### 6. 实时数据流

**方法描述**: 使用 Kafka、RabbitMQ 等消息队列处理实时数据

**使用场景**: 
- 实时监控数据
- IoT 传感器数据
- 用户行为追踪
- 金融行情数据

**Python 代码**:
```python
from kafka import KafkaConsumer
import pandas as pd
import json

def consume_kafka_data(topic, bootstrap_servers, max_messages=100):
    """
    从 Kafka 消费数据
    
    参数:
        topic: Kafka 主题
        bootstrap_servers: Kafka 服务器地址
        max_messages: 最大消息数
    
    返回:
        DataFrame: 消费的数据
    """
    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=bootstrap_servers,
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )
    
    messages = []
    for message in consumer:
        messages.append(message.value)
        if len(messages) >= max_messages:
            break
    
    consumer.close()
    return pd.DataFrame(messages)

# 示例：消费传感器数据
df = consume_kafka_data('sensor_data', 'localhost:9092', max_messages=1000)
print(df.head())
print(f"数据形状: {df.shape}")
```

**示例数据**:
```python
# 传感器数据示例
   sensor_id  temperature  humidity  timestamp
0     S001        25.3        60.2    2024-01-01 10:00:00
1     S002        24.8        58.7    2024-01-01 10:00:01
2     S003        26.1        62.1    2024-01-01 10:00:02
```

**结果解读**: 
- 实时捕获传感器读数
- 时间序列数据便于趋势分析
- 可设置阈值告警

---

### 7. PDF 文档提取

**方法描述**: 从 PDF 文件中提取文本、表格数据

**使用场景**: 
- 财务报表
- 研究报告
- 政府文件
- 发票凭证

**Python 代码**:
```python
import PyPDF2
import pdfplumber
import pandas as pd

def extract_pdf_text(pdf_path):
    """
    提取 PDF 文本
    
    参数:
        pdf_path: PDF 文件路径
    
    返回:
        str: 提取的文本
    """
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
    return text

def extract_pdf_tables(pdf_path):
    """
    提取 PDF 表格
    
    参数:
        pdf_path: PDF 文件路径
    
    返回:
        list: 表格列表
    """
    tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if table:
                df = pd.DataFrame(table[1:], columns=table[0])
                tables.append(df)
    return tables

# 示例：提取财务报表
text = extract_pdf_text('financial_report.pdf')
tables = extract_pdf_tables('financial_report.pdf')

print(f"提取的表格数量: {len(tables)}")
if tables:
    print(tables[0].head())
```

**示例数据**:
```python
# 提取的财务表格示例
   项目      2023年      2022年      同比增长
0  营收     1000000    800000      25.0%
1  净利润   150000     100000      50.0%
2  总资产   5000000    4000000     25.0%
```

**结果解读**: 
- 成功提取结构化表格数据
- 便于后续财务分析
- 注意 OCR 错误和数据清洗

---

### 8. 图像数据提取

**方法描述**: 使用 OCR 技术从图像中提取文字和数据

**使用场景**: 
- 扫描文档
- 发票/收据
- 身份证件
- 截图数据

**Python 代码**:
```python
import cv2
import pytesseract
from PIL import Image
import pandas as pd
import re

def extract_text_from_image(image_path):
    """
    从图像提取文本
    
    参数:
        image_path: 图像文件路径
    
    返回:
        str: 提取的文本
    """
    # 读取图像
    image = cv2.imread(image_path)
    
    # 预处理
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray)
    
    # OCR 识别
    text = pytesseract.image_to_string(denoised, lang='chi_sim+eng')
    return text

def extract_invoice_data(image_path):
    """
    提取发票数据
    """
    text = extract_text_from_image(image_path)
    
    # 使用正则表达式提取关键信息
    invoice_data = {
        'invoice_no': re.search(r'发票号码[:：]\s*(\w+)', text),
        'date': re.search(r'日期[:：]\s*(\d{4}-\d{2}-\d{2})', text),
        'amount': re.search(r'金额[:：]\s*¥?([\d,]+\.?\d*)', text)
    }
    
    return {k: v.group(1) if v else None for k, v in invoice_data.items()}

# 示例：提取发票信息
data = extract_invoice_data('invoice.jpg')
print(data)
```

**示例数据**:
```python
# 发票提取结果
{
    'invoice_no': '12345678',
    'date': '2024-01-01',
    'amount': '1,234.56'
}
```

**结果解读**: 
- OCR 准确率依赖图像质量
- 需要后处理规则提高准确性
- 可结合模板匹配提高精度

---

### 9. 社交媒体数据

**方法描述**: 使用 Twitter API、Reddit API 等获取社交媒体数据

**使用场景**: 
- 舆情分析
- 品牌监控
- 用户反馈收集
- 趋势分析

**Python 代码**:
```python
import tweepy
import pandas as pd

def fetch_twitter_data(api_key, api_secret, access_token, access_secret, query, count=100):
    """
    获取 Twitter 数据
    
    参数:
        api_key: API 密钥
        query: 搜索关键词
        count: 获取数量
    
    返回:
        DataFrame: 推文数据
    """
    # 认证
    auth = tweepy.OAuthHandler(api_key, api_secret)
    auth.set_access_token(access_token, access_secret)
    api = tweepy.API(auth)
    
    # 搜索推文
    tweets = api.search_tweets(q=query, count=count, tweet_mode='extended')
    
    # 解析数据
    data = []
    for tweet in tweets:
        data.append({
            'id': tweet.id,
            'created_at': tweet.created_at,
            'user': tweet.user.screen_name,
            'text': tweet.full_text,
            'retweets': tweet.retweet_count,
            'favorites': tweet.favorite_count,
            'location': tweet.user.location
        })
    
    return pd.DataFrame(data)

# 示例：搜索 AI 相关推文
df = fetch_twitter_data('key', 'secret', 'token', 'secret', 'AI', count=100)
print(df.head())
```

**示例数据**:
```python
# Twitter 数据示例
   id                created_at    user    text    retweets  favorites
0  1234567890  2024-01-01 10:00:00  user1   AI is...   5        10
1  1234567891  2024-01-01 10:01:00  user2   Amazing...  2        8
```

**结果解读**: 
- 实时获取用户观点
- 分析情感倾向
- 识别影响者和话题趋势

---

### 10. 问卷调查数据

**方法描述**: 从在线问卷平台（如 SurveyMonkey、Google Forms）收集数据

**使用场景**: 
- 市场调研
- 用户反馈
- 满意度调查
- 学术研究

**Python 代码**:
```python
import pandas as pd
import requests

def fetch_survey_data(survey_url, api_key):
    """
    获取问卷数据
    
    参数:
        survey_url: 问卷 URL
        api_key: API 密钥
    
    返回:
        DataFrame: 问卷响应数据
    """
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    response = requests.get(survey_url, headers=headers)
    response.raise_for_status()
    
    data = response.json()
    return pd.DataFrame(data['responses'])

def analyze_survey(df):
    """
    分析问卷数据
    
    参数:
        df: 问卷数据 DataFrame
    
    返回:
        dict: 分析结果
    """
    results = {}
    
    # 基本统计
    results['total_responses'] = len(df)
    results['completion_rate'] = (df['status'] == 'completed').mean() * 100
    
    # 评分分布
    if 'rating' in df.columns:
        results['avg_rating'] = df['rating'].mean()
        results['rating_distribution'] = df['rating'].value_counts().to_dict()
    
    # 问题回答率
    for col in df.columns:
        if col.startswith('q'):
            results[f'{col}_response_rate'] = df[col].notna().mean() * 100
    
    return results

# 示例：分析满意度调查
df = fetch_survey_data('https://api.survey.com/surveys/123', 'api_key')
results = analyze_survey(df)
print(results)
```

**示例数据**:
```python
# 问卷数据示例
   response_id  q1_satisfaction  q2_feature  q3_recommend  status
0      001           5              Yes          Yes      completed
1      002           4              No           Yes      completed
2      003           3              Yes          No       completed
```

**结果解读**: 
- 平均满意度评分：4.0/5
- 推荐意愿：67%
- 主要改进点识别

---

## 数据清洗 (15 种技巧)

### 1. 缺失值处理

**方法描述**: 处理数据中的空值和缺失数据

**使用场景**: 
- 数据采集不完整
- 传感器故障
- 用户未填写信息

**Python 代码**:
```python
import pandas as pd
import numpy as np

def handle_missing_values(df, strategy='mean'):
    """
    处理缺失值
    
    参数:
        df: 数据 DataFrame
        strategy: 处理策略 (drop, mean, median, mode, forward, backward)
    
    返回:
        DataFrame: 处理后的数据
    """
    df_clean = df.copy()
    
    if strategy == 'drop':
        df_clean = df_clean.dropna()
    elif strategy == 'mean':
        numeric_cols = df_clean.select_dtypes(include=[np.number]).columns
        df_clean[numeric_cols] = df_clean[numeric_cols].fillna(df_clean[numeric_cols].mean())
    elif strategy == 'median':
        numeric_cols = df_clean.select_dtypes(include=[np.number]).columns
        df_clean[numeric_cols] = df_clean[numeric_cols].fillna(df_clean[numeric_cols].median())
    elif strategy == 'mode':
        for col in df_clean.columns:
            df_clean[col] = df_clean[col].fillna(df_clean[col].mode()[0] if not df_clean[col].mode().empty else df_clean[col])
    elif strategy == 'forward':
        df_clean = df_clean.fillna(method='ffill')
    elif strategy == 'backward':
        df_clean = df_clean.fillna(method='bfill')
    
    return df_clean

# 示例数据
df = pd.DataFrame({
    'A': [1, 2, np.nan, 4, 5],
    'B': [10, np.nan, np.nan, 40, 50],
    'C': ['a', 'b', np.nan, 'd', 'e']
})

print("原始数据:")
print(df)
print(f"\n缺失值统计:\n{df.isnull().sum()}")

# 使用均值填充数值列
df_clean = handle_missing_values(df, 'mean')
print("\n清洗后数据:")
print(df_clean)
```

**示例数据**:
```python
# 原始数据
     A     B    C
0  1.0  10.0    a
1  2.0   NaN    b
2  NaN   NaN  NaN
3  4.0  40.0    d
4  5.0  50.0    e

# 清洗后（均值填充）
     A     B    C
0  1.0  10.0    a
1  2.0  33.3    b
2  3.0  33.3  NaN
3  4.0  40.0    d
4  5.0  50.0    e
```

**结果解读**: 
- 数值列使用均值/中位数填充
- 分类列使用众数或向前/向后填充
- 根据数据分布选择合适策略

---

### 2. 重复值处理

**方法描述**: 识别和删除重复的记录

**使用场景**: 
- 数据导入重复
- 系统错误导致重复提交
- 合并多个数据源

**Python 代码**:
```python
import pandas as pd

def remove_duplicates(df, subset=None, keep='first'):
    """
    删除重复值
    
    参数:
        df: 数据 DataFrame
        subset: 用于判断重复的列
        keep: 保留策略 (first, last, False)
    
    返回:
        tuple: (清洗后数据, 删除的行数)
    """
    before_len = len(df)
    df_clean = df.drop_duplicates(subset=subset, keep=keep)
    after_len = len(df_clean)
    duplicates_removed = before_len - after_len
    
    return df_clean, duplicates_removed

# 示例数据
df = pd.DataFrame({
    'id': [1, 2, 2, 3, 3, 3],
    'name': ['Alice', 'Bob', 'Bob', 'Charlie', 'Charlie', 'Charlie'],
    'value': [100, 200, 200, 300, 300, 300]
})

print("原始数据:")
print(df)

df_clean, removed = remove_duplicates(df, subset=['id', 'name'], keep='first')
print(f"\n清洗后数据 (删除了 {removed} 条重复):")
print(df_clean)
```

**示例数据**:
```python
# 原始数据
   id     name  value
0   1    Alice    100
1   2      Bob    200
2   2      Bob    200  # 重复
3   3  Charlie    300
4   3  Charlie    300  # 重复
5   3  Charlie    300  # 重复

# 清洗后
   id     name  value
0   1    Alice    100
1   2      Bob    200
3   3  Charlie    300
```

**结果解读**: 
- 保留每组的首次出现
- 删除 3 条重复记录
- 可以根据业务需求选择保留策略

---

### 3. 异常值检测

**方法描述**: 使用统计方法识别和处理异常数据

**使用场景**: 
- 传感器错误读数
- 数据输入错误
- 欺诈检测

**Python 代码**:
```python
import pandas as pd
import numpy as np
from scipy import stats

def detect_outliers(df, column, method='iqr', threshold=1.5):
    """
    检测异常值
    
    参数:
        df: 数据 DataFrame
        column: 要检测的列
        method: 检测方法 (iqr, zscore)
        threshold: 阈值
    
    返回:
        tuple: (异常值索引, 清洗后数据)
    """
    data = df[column].dropna()
    
    if method == 'iqr':
        Q1 = data.quantile(0.25)
        Q3 = data.quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - threshold * IQR
        upper_bound = Q3 + threshold * IQR
        outlier_mask = (data < lower_bound) | (data > upper_bound)
    
    elif method == 'zscore':
        z_scores = np.abs(stats.zscore(data))
        outlier_mask = z_scores > threshold
    
    outlier_indices = data[outlier_mask].index
    df_clean = df.drop(outlier_indices)
    
    return outlier_indices, df_clean

# 示例数据
df = pd.DataFrame({
    'value': [10, 12, 11, 13, 10, 100, 12, 11, 13, 10, -50, 12]
})

print("原始数据:")
print(df['value'].describe())

# 使用 IQR 方法检测异常值
outliers, df_clean = detect_outliers(df, 'value', method='iqr')
print(f"\n检测到 {len(outliers)} 个异常值:")
print(df.loc[outliers])
print(f"\n清洗后数据描述:")
print(df_clean['value'].describe())
```

**示例数据**:
```python
# 检测到的异常值
    value
5     100  # 过高
10   -50   # 过低

# 统计对比
原始数据: 均值=14.17, 标准差=28.34
清洗后数据: 均值=11.50, 标准差=1.08
```

**结果解读**: 
- IQR 方法识别出 2 个异常值
- 异常值严重影响均值和标准差
- 清洗后数据更接近真实分布

---

### 4. 数据类型转换

**方法描述**: 将列转换为正确的数据类型

**使用场景**: 
- 数值存储为文本
- 日期字符串转换
- 分类变量编码

**Python 代码**:
```python
import pandas as pd

def convert_dtypes(df, type_mapping):
    """
    转换数据类型
    
    参数:
        df: 数据 DataFrame
        type_mapping: 类型映射字典
    
    返回:
        DataFrame: 转换后的数据
    """
    df_converted = df.copy()
    
    for column, target_type in type_mapping.items():
        if column in df_converted.columns:
            try:
                if target_type == 'numeric':
                    df_converted[column] = pd.to_numeric(df_converted[column], errors='coerce')
                elif target_type == 'datetime':
                    df_converted[column] = pd.to_datetime(df_converted[column], errors='coerce')
                elif target_type == 'category':
                    df_converted[column] = df_converted[column].astype('category')
                elif target_type == 'string':
                    df_converted[column] = df_converted[column].astype(str)
            except Exception as e:
                print(f"转换列 {column} 失败: {e}")
    
    return df_converted

# 示例数据
df = pd.DataFrame({
    'id': ['1', '2', '3', '4', '5'],
    'price': ['1000', '2000', '1500', '3000', '2500'],
    'date': ['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05'],
    'category': ['A', 'B', 'A', 'C', 'B']
})

print("原始数据类型:")
print(df.dtypes)

type_mapping = {
    'id': 'numeric',
    'price': 'numeric',
    'date': 'datetime',
    'category': 'category'
}

df_converted = convert_dtypes(df, type_mapping)
print("\n转换后数据类型:")
print(df_converted.dtypes)
print("\n转换后数据:")
print(df_converted.head())
```

**示例数据**:
```python
# 原始数据类型
id          object
price       object
date        object
category    object
dtype: object

# 转换后数据类型
id            int64
price       float64
date    datetime64[ns]
category   category
dtype: object
```

**结果解读**: 
- 字符串成功转换为数值
- 日期转换为 datetime 类型便于时间序列分析
- 分类变量转换为 category 类型节省内存

---

### 5. 文本清洗

**方法描述**: 清理和标准化文本数据

**使用场景**: 
- 用户评论
- 产品描述
- 新闻文章
- 社交媒体帖子

**Python 代码**:
```python
import pandas as pd
import re

def clean_text(text):
    """
    清洗文本
    
    参数:
        text: 原始文本
    
    返回:
        str: 清洗后的文本
    """
    if not isinstance(text, str):
        return text
    
    # 转换为小写
    text = text.lower()
    
    # 移除特殊字符和数字
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\d+', '', text)
    
    # 移除多余空格
    text = ' '.join(text.split())
    
    # 移除停用词（简化版）
    stopwords = ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for']
    words = text.split()
    text = ' '.join([w for w in words if w not in stopwords])
    
    return text

def clean_dataframe_text(df, text_columns):
    """
    清洗 DataFrame 中的文本列
    
    参数:
        df: 数据 DataFrame
        text_columns: 文本列列表
    
    返回:
        DataFrame: 清洗后的数据
    """
    df_clean = df.copy()
    
    for col in text_columns:
        if col in df_clean.columns:
            df_clean[col] = df_clean[col].apply(clean_text)
    
    return df_clean

# 示例数据
df = pd.DataFrame({
    'review': [
        'Great product!!! Highly recommended.',
        'Not bad... could be better.',
        'WORST purchase ever!!! 123',
        'Amazing quality, fast shipping!!!'
    ],
    'rating': [5, 3, 1, 5]
})

print("原始数据:")
print(df['review'].tolist())

df_clean = clean_dataframe_text(df, ['review'])
print("\n清洗后数据:")
print(df_clean['review'].tolist())
```

**示例数据**:
```python
# 原始文本
[
    'Great product!!! Highly recommended.',
    'Not bad... could be better.',
    'WORST purchase ever!!! 123',
    'Amazing quality, fast shipping!!!'
]

# 清洗后文本
[
    'great product highly recommended',
    'not bad could be better',
    'worst purchase ever',
    'amazing quality fast shipping'
]
```

**结果解读**: 
- 标点符号和数字已移除
- 统一为小写
- 移除常见停用词
- 文本更利于 NLP 处理

---

### 6. 日期时间处理

**方法描述**: 处理和标准化日期时间数据

**使用场景**: 
- 时间序列分析
- 周期性模式识别
- 日期范围筛选

**Python 代码**:
```python
import pandas as pd
from datetime import datetime

def process_datetime(df, date_columns, timezone='Asia/Shanghai'):
    """
    处理日期时间列
    
    参数:
        df: 数据 DataFrame
        date_columns: 日期列列表
        timezone: 时区
    
    返回:
        DataFrame: 处理后的数据
    """
    df_processed = df.copy()
    
    for col in date_columns:
        if col in df_processed.columns:
            # 转换为 datetime
            df_processed[col] = pd.to_datetime(df_processed[col], errors='coerce')
            
            # 提取时间特征
            df_processed[f'{col}_year'] = df_processed[col].dt.year
            df_processed[f'{col}_month'] = df_processed[col].dt.month
            df_processed[f'{col}_day'] = df_processed[col].dt.day
            df_processed[f'{col}_weekday'] = df_processed[col].dt.weekday
            df_processed[f'{col}_hour'] = df_processed[col].dt.hour
            df_processed[f'{col}_is_weekend'] = df_processed[col].dt.weekday >= 5
    
    return df_processed

# 示例数据
df = pd.DataFrame({
    'timestamp': [
        '2024-01-01 10:00:00',
        '2024-01-02 15:30:00',
        '2024-01-03 20:45:00',
        '2024-01-04 08:15:00'
    ],
    'event': ['login', 'purchase', 'logout', 'login']
})

print("原始数据:")
print(df)

df_processed = process_datetime(df, ['timestamp'])
print("\n处理后数据:")
print(df_processed)
```

**示例数据**:
```python
# 处理后数据
                   timestamp    event  timestamp_year  timestamp_month  ...
0  2024-01-01 10:00:00    login           2024               1
1  2024-01-02 15:30:00  purchase           2024               1
2  2024-01-03 20:45:00   logout           2024               1
3  2024-01-04 08:15:00    login           2024               1

   timestamp_day  timestamp_weekday  timestamp_hour  timestamp_is_weekend
0              1                  0              10                  False
1              2                  1              15                  False
2              3                  2              20                  False
3              4                  3               8                  False
```

**结果解读**: 
- 成功提取年、月、日、星期、小时
- 标记周末（weekday >= 5）
- 便于时间序列分析和特征工程

---

### 7. 数据标准化

**方法描述**: 将数值数据缩放到统一范围

**使用场景**: 
- 机器学习特征预处理
- 不同量纲数据比较
- 距离计算算法

**Python 代码**:
```python
import pandas as pd
from sklearn.preprocessing import StandardScaler, MinMaxScaler

def normalize_data(df, numeric_columns, method='standard'):
    """
    标准化数据
    
    参数:
        df: 数据 DataFrame
        numeric_columns: 数值列列表
        method: 标准化方法 (standard, minmax)
    
    返回:
        DataFrame: 标准化后的数据
    """
    df_normalized = df.copy()
    
    if method == 'standard':
        scaler = StandardScaler()
    elif method == 'minmax':
        scaler = MinMaxScaler()
    else:
        raise ValueError(f"未知方法: {method}")
    
    df_normalized[numeric_columns] = scaler.fit_transform(df_normalized[numeric_columns])
    
    return df_normalized, scaler

# 示例数据
df = pd.DataFrame({
    'age': [25, 30, 35, 40, 45],
    'salary': [50000, 60000, 70000, 80000, 90000],
    'experience': [1, 3, 5, 7, 10]
})

print("原始数据:")
print(df)

df_normalized, scaler = normalize_data(df, ['age', 'salary', 'experience'], 'standard')
print("\n标准化后数据 (Z-score):")
print(df_normalized)
print(f"\n均值:\n{df_normalized.mean()}")
print(f"\n标准差:\n{df_normalized.std()}")
```

**示例数据**:
```python
# 原始数据
   age  salary  experience
0   25   50000           1
1   30   60000           3
2   35   70000           5
3   40   80000           7
4   45   90000          10

# Z-score 标准化后
        age    salary  experience
0 -1.264911 -1.264911   -1.240347
1 -0.632456 -0.632456   -0.617174
2  0.000000  0.000000    0.000000
3  0.632456  0.632456    0.617174
4  1.264911  1.264911    1.240347

# 统计特性
均值: 接近 0
标准差: 1
```

**结果解读**: 
- 每列均值为 0，标准差为 1
- 消除了量纲差异
- 保留数据分布特性
- 适合 SVM、神经网络等算法

---

### 8. 数据编码

**方法描述**: 将分类变量转换为数值

**使用场景**: 
- 机器学习模型输入
- 标签编码
- 特征工程

**Python 代码**:
```python
import pandas as pd
from sklearn.preprocessing import LabelEncoder, OneHotEncoder

def encode_categorical(df, categorical_columns, method='label'):
    """
    编码分类变量
    
    参数:
        df: 数据 DataFrame
        categorical_columns: 分类列列表
        method: 编码方法 (label, onehot)
    
    返回:
        DataFrame: 编码后的数据
    """
    df_encoded = df.copy()
    
    if method == 'label':
        for col in categorical_columns:
            le = LabelEncoder()
            df_encoded[col] = le.fit_transform(df_encoded[col])
    
    elif method == 'onehot':
        df_encoded = pd.get_dummies(df_encoded, columns=categorical_columns, drop_first=False)
    
    return df_encoded

# 示例数据
df = pd.DataFrame({
    'id': [1, 2, 3, 4, 5],
    'color': ['red', 'blue', 'green', 'red', 'blue'],
    'size': ['S', 'M', 'L', 'M', 'S'],
    'price': [100, 200, 300, 150, 250]
})

print("原始数据:")
print(df)

# 标签编码
df_label = encode_categorical(df, ['color', 'size'], 'label')
print("\n标签编码:")
print(df_label)

# 独热编码
df_onehot = encode_categorical(df, ['color', 'size'], 'onehot')
print("\n独热编码:")
print(df_onehot)
```

**示例数据**:
```python
# 标签编码
   id  color  size  price
0   1      2     2    100
1   2      0     1    200
2   3      1     0    300
3   4      2     1    150
4   5      0     2    250

# 独热编码
   id  price  color_blue  color_green  color_red  size_L  size_M  size_S
0   1    100       False         False       True   False   False    True
1   2    200        True         False      False   False    True   False
2   3    300       False          True      False    True   False   False
3   4    150       False         False       True   False    True   False
4   5    250        True         False      False   False   False    True
```

**结果解读**: 
- **标签编码**: 适合有序分类（如 S, M, L）
- **独热编码**: 适合无序分类（如颜色）
- 独热编码增加特征维度
- 根据模型要求选择编码方式

---

### 9. 数据去噪

**方法描述**: 使用滤波器平滑数据，减少噪声

**使用场景**: 
- 传感器数据
- 时间序列数据
- 信号处理

**Python 代码**:
```python
import pandas as pd
import numpy as np
from scipy.signal import savgol_filter

def denoise_data(df, column, window_length=5, polyorder=2):
    """
    去噪数据
    
    参数:
        df: 数据 DataFrame
        column: 要去噪的列
        window_length: 窗口长度
        polyorder: 多项式阶数
    
    返回:
        DataFrame: 去噪后的数据
    """
    df_denoised = df.copy()
    
    # Savitzky-Golay 滤波器
    df_denoised[f'{column}_denoised'] = savgol_filter(
        df[column].values, 
        window_length, 
        polyorder
    )
    
    return df_denoised

# 示例数据：带噪声的正弦波
np.random.seed(42)
t = np.linspace(0, 10, 100)
signal = np.sin(t) + np.random.normal(0, 0.2, 100)

df = pd.DataFrame({
    'time': t,
    'signal': signal
})

print("原始信号（前10个点）:")
print(df.head(10))

df_denoised = denoise_data(df, 'signal', window_length=11, polyorder=2)
print("\n去噪后信号（前10个点）:")
print(df_denoised[['time', 'signal', 'signal_denoised']].head(10))

# 计算降噪效果
noise_reduction = ((df['signal'] - df['signal_denoised']) ** 2).mean()
print(f"\n均方误差: {noise_reduction:.4f}")
```

**示例数据**:
```python
# 去噪前后对比
time    signal      signal_denoised
0.00    0.4967     0.1423
0.10    0.1386     0.2517
0.20    0.4530     0.3562
0.30    0.4519     0.4567
0.40    0.7132     0.5523
0.50    0.6593     0.6423
0.60    0.6836     0.7245
0.70    1.0621     0.7998
0.80    0.8143     0.8690
0.90    1.0242     0.9298

# 降噪效果
- 保留信号趋势
- 平滑随机噪声
- 均方误差: 0.0421
```

**结果解读**: 
- Savitzky-Golay 滤波器有效平滑噪声
- 保留信号的局部特征
- 窗口长度越大，平滑效果越强

---

### 10. 数据一致性检查

**方法描述**: 验证数据的逻辑一致性和完整性

**使用场景**: 
- 数据质量评估
- 业务规则验证
- 异常数据发现

**Python 代码**:
```python
import pandas as pd

def check_consistency(df, rules):
    """
    检查数据一致性
    
    参数:
        df: 数据 DataFrame
        rules: 验证规则字典
    
    返回:
        dict: 验证结果
    """
    results = {}
    
    for rule_name, rule_func in rules.items():
        try:
            is_valid = rule_func(df)
            results[rule_name] = {
                'passed': is_valid,
                'invalid_count': (~is_valid).sum() if hasattr(is_valid, 'sum') else int(not is_valid)
            }
        except Exception as e:
            results[rule_name] = {
                'passed': False,
                'error': str(e)
            }
    
    return results

# 定义验证规则
consistency_rules = {
    'age_positive': lambda df: df['age'] > 0,
    'salary_positive': lambda df: df['salary'] > 0,
    'age_experience': lambda df: df['age'] >= df['experience'],
    'email_format': lambda df: df['email'].str.contains('@', na=False),
    'date_order': lambda df: df['end_date'] >= df['start_date']
}

# 示例数据
df = pd.DataFrame({
    'name': ['Alice', 'Bob', 'Charlie', 'David'],
    'age': [25, -5, 35, 40],  # Bob 年龄无效
    'salary': [50000, 60000, -1000, 80000],  # Charlie 薪资无效
    'experience': [2, 5, 40, 8],  # Charlie 经验 > 年龄
    'email': ['alice@test.com', 'bobtest.com', 'charlie@test.com', 'david@test.com'],  # Bob 邮箱无效
    'start_date': pd.to_datetime(['2020-01-01', '2021-01-01', '2022-01-01', '2023-01-01']),
    'end_date': pd.to_datetime(['2021-01-01', '2020-01-01', '2023-01-01', '2024-01-01'])  # Bob 结束日期 < 开始日期
})

print("原始数据:")
print(df)

# 执行一致性检查
results = check_consistency(df, consistency_rules)
print("\n一致性检查结果:")
for rule, result in results.items():
    status = "✓ 通过" if result['passed'] else "✗ 失败"
    invalid_count = result.get('invalid_count', 'N/A')
    print(f"{rule}: {status} (无效记录: {invalid_count})")
```

**示例数据**:
```python
# 一致性检查结果
age_positive: ✗ 失败 (无效记录: 1)
salary_positive: ✗ 失败 (无效记录: 1)
age_experience: ✗ 失败 (无效记录: 1)
email_format: ✗ 失败 (无效记录: 1)
date_order: ✗ 失败 (无效记录: 1)

# 问题记录
Bob: 年龄为负，邮箱格式错误，结束日期早于开始日期
Charlie: 薪资为负，工作经验超过年龄
```

**结果解读**: 
- 发现 5 条一致性规则被违反
- 需要修正或删除无效记录
- 可用于数据质量报告

---

### 11. 数据合并

**方法描述**: 合并多个数据源，处理键冲突

**使用场景**: 
- 整合不同系统数据
- 添加参考数据
- 连接交易和维度表

**Python 代码**:
```python
import pandas as pd

def merge_datasets(left_df, right_df, on, how='inner', suffixes=('_x', '_y')):
    """
    合并数据集
    
    参数:
        left_df: 左表
        right_df: 右表
        on: 连接键
        how: 连接方式 (inner, left, right, outer)
        suffixes: 列名后缀
    
    返回:
        DataFrame: 合并后的数据
    """
    merged = pd.merge(
        left_df,
        right_df,
        on=on,
        how=how,
        suffixes=suffixes
    )
    
    return merged

# 示例数据：销售数据和产品信息
sales = pd.DataFrame({
    'product_id': [1, 2, 3, 4, 5],
    'sale_date': ['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05'],
    'quantity': [10, 20, 15, 25, 30],
    'amount': [1000, 2000, 1500, 2500, 3000]
})

products = pd.DataFrame({
    'product_id': [1, 2, 3, 6],
    'product_name': ['手机', '笔记本', '平板', '耳机'],
    'category': ['电子产品', '电子产品', '电子产品', '配件'],
    'unit_price': [100, 100, 100, 50]
})

print("销售数据:")
print(sales)
print("\n产品信息:")
print(products)

# 内连接
merged_inner = merge_datasets(sales, products, 'product_id', how='inner')
print("\n内连接结果:")
print(merged_inner)

# 左连接
merged_left = merge_datasets(sales, products, 'product_id', how='left')
print("\n左连接结果:")
print(merged_left)
```

**示例数据**:
```python
# 内连接（只保留两边都有的键）
   product_id   sale_date  quantity  amount product_name    category  unit_price
0           1  2024-01-01        10    1000         手机    电子产品         100
1           2  2024-01-02        20    2000       笔记本    电子产品         100
2           3  2024-01-03        15    1500         平板    电子产品         100

# 左连接（保留左表所有记录）
   product_id   sale_date  quantity  amount product_name    category  unit_price
0           1  2024-01-01        10    1000         手机    电子产品         100
1           2  2024-01-02        20    2000       笔记本    电子产品         100
2           3  2024-01-03        15    1500         平板    电子产品         100
3           4  2024-01-04        25    2500          NaN         NaN          NaN
4           5  2024-01-05        30    3000          NaN         NaN          NaN
```

**结果解读**: 
- 内连接：只匹配两边都存在的产品（1, 2, 3）
- 左连接：保留所有销售记录，产品 4, 5 信息缺失
- 产品 6 不在销售数据中，被外连接排除

---

### 12. 数据透视

**方法描述**: 将长格式数据转换为宽格式

**使用场景**: 
- 时间序列重塑
- 交叉表生成
- 数据透视表

**Python 代码**:
```python
import pandas as pd

def pivot_data(df, index, columns, values, aggfunc='mean'):
    """
    数据透视
    
    参数:
        df: 数据 DataFrame
        index: 行索引
        columns: 列
        values: 值
        aggfunc: 聚合函数
    
    返回:
        DataFrame: 透视后的数据
    """
    pivoted = df.pivot_table(
        index=index,
        columns=columns,
        values=values,
        aggfunc=aggfunc,
        fill_value=0
    )
    
    return pivoted

# 示例数据：月度销售数据
df = pd.DataFrame({
    'year': [2023, 2023, 2023, 2024, 2024, 2024],
    'month': ['Jan', 'Feb', 'Mar', 'Jan', 'Feb', 'Mar'],
    'product': ['A', 'B', 'A', 'B', 'A', 'B'],
    'sales': [100, 150, 120, 180, 200, 160]
})

print("原始数据（长格式）:")
print(df)

# 按产品和月份透视
pivoted = pivot_data(df, 'product', 'month', 'sales', 'sum')
print("\n透视后数据（宽格式）:")
print(pivoted)

# 按年份和月份透视
pivoted2 = pivot_data(df, 'year', 'month', 'sales', 'sum')
print("\n按年份透视:")
print(pivoted2)
```

**示例数据**:
```python
# 原始数据（长格式）
   year month product  sales
0  2023   Jan       A    100
1  2023   Feb       B    150
2  2023   Mar       A    120
3  2024   Jan       B    180
4  2024   Feb       A    200
5  2024   Mar       B    160

# 透视后（产品 × 月份）
month       Feb   Jan   Mar
product                     
A         200.0   100  120.0
B         150.0   180  160.0

# 透视后（年份 × 月份）
month      Feb   Jan   Mar
year                      
2023     150.0   100  120.0
2024     200.0   180  160.0
```

**结果解读**: 
- 长格式转换为宽格式便于比较
- 产品 A 在 Feb 销售最高（200）
- 产品 B 在 Jan 销售最高（180）
- 2024 年整体销售高于 2023

---

### 13. 数据分组聚合

**方法描述**: 按类别分组并计算统计量

**使用场景**: 
- 分组统计
- 类别比较
- 层级分析

**Python 代码**:
```python
import pandas as pd

def group_aggregate(df, group_by, agg_dict):
    """
    分组聚合
    
    参数:
        df: 数据 DataFrame
        group_by: 分组键
        agg_dict: 聚合字典
    
    返回:
        DataFrame: 聚合结果
    """
    grouped = df.groupby(group_by).agg(agg_dict)
    return grouped

# 示例数据：员工信息
df = pd.DataFrame({
    'department': ['Sales', 'Sales', 'IT', 'IT', 'IT', 'HR', 'HR'],
    'name': ['Alice', 'Bob', 'Charlie', 'David', 'Eve', 'Frank', 'Grace'],
    'salary': [50000, 60000, 70000, 80000, 90000, 45000, 55000],
    'age': [25, 30, 35, 40, 45, 28, 32],
    'performance': [85, 90, 88, 92, 95, 80, 87]
})

print("原始数据:")
print(df)

# 按部门分组聚合
agg_dict = {
    'salary': ['mean', 'median', 'std'],
    'age': ['mean', 'min', 'max'],
    'performance': ['mean', 'count']
}

result = group_aggregate(df, 'department', agg_dict)
print("\n部门统计:")
print(result)

# 按薪资范围分组
df['salary_range'] = pd.cut(df['salary'], bins=[0, 50000, 70000, 100000], labels=['低', '中', '高'])
print("\n按薪资范围分组:")
print(df.groupby('salary_range').size())
```

**示例数据**:
```python
# 部门统计
              salary                       age                performance          
               mean   median       std  mean   min   max       mean count
department                                                                   
HR          50000.0  50000.0   7071.07  30.0  28.0  32.0  83.500000     2
IT          80000.0  80000.0  10000.00  40.0  35.0  45.0  91.666667     3
Sales       55000.0  55000.0   7071.07  27.5  25.0  30.0  87.500000     2

# 薪资范围分布
低    2
中    3
高    2
```

**结果解读**: 
- IT 部门平均薪资最高（80000）
- IT 部门绩效最好（91.67）
- 中等薪资员工最多（3人）
- HR 部门薪资差异最小（std=7071）

---

### 14. 数据采样

**方法描述**: 从大数据集中抽取代表性样本

**使用场景**: 
- 数据探索
- 模型训练
- 快速原型

**Python 代码**:
```python
import pandas as pd
import numpy as np

def sample_data(df, method='random', n=1000, stratify_col=None):
    """
    数据采样
    
    参数:
        df: 数据 DataFrame
        method: 采样方法 (random, stratified, systematic)
        n: 样本量
        stratify_col: 分层列
    
    返回:
        DataFrame: 采样后的数据
    """
    if method == 'random':
        return df.sample(n=min(n, len(df)), random_state=42)
    
    elif method == 'stratified':
        if stratify_col not in df.columns:
            raise ValueError(f"列 {stratify_col} 不存在")
        return df.groupby(stratify_col, group_keys=False).apply(
            lambda x: x.sample(min(len(x), n // df[stratify_col].nunique()), random_state=42)
        )
    
    elif method == 'systematic':
        step = max(1, len(df) // n)
        return df.iloc[::step][:n]
    
    else:
        raise ValueError(f"未知方法: {method}")

# 示例数据：客户数据
np.random.seed(42)
df = pd.DataFrame({
    'customer_id': range(10000),
    'segment': np.random.choice(['VIP', 'Regular', 'New'], 10000, p=[0.1, 0.6, 0.3]),
    'purchase_amount': np.random.exponential(500, 10000),
    'age': np.random.randint(18, 80, 10000)
})

print(f"原始数据: {len(df)} 条")
print(f"客户分布:\n{df['segment'].value_counts()}")

# 随机采样
df_random = sample_data(df, 'random', 1000)
print(f"\n随机采样: {len(df_random)} 条")
print(f"采样分布:\n{df_random['segment'].value_counts()}")

# 分层采样
df_stratified = sample_data(df, 'stratified', 1000, 'segment')
print(f"\n分层采样: {len(df_stratified)} 条")
print(f"采样分布:\n{df_stratified['segment'].value_counts()}")
```

**示例数据**:
```python
# 原始数据分布
VIP        1000
Regular    6000
New        3000

# 随机采样（1000 条）
VIP         95
Regular    605
New        300

# 分层采样（保持比例）
VIP         100
Regular     600
New         300
```

**结果解读**: 
- 随机采样可能偏离原始分布
- 分层采样保持类别比例
- 系统采样均匀间隔抽取
- 采样用于快速分析和模型训练

---

### 15. 数据脱敏

**方法描述**: 保护敏感信息，匿名化数据

**使用场景**: 
- 隐私保护
- 数据共享
- 合规要求

**Python 代码**:
```python
import pandas as pd
import hashlib
import numpy as np

def anonymize_data(df, sensitive_columns, method='hash'):
    """
    数据脱敏
    
    参数:
        df: 数据 DataFrame
        sensitive_columns: 敏感列列表
        method: 脱敏方法 (hash, mask, partial)
    
    返回:
        DataFrame: 脱敏后的数据
    """
    df_anon = df.copy()
    
    for col in sensitive_columns:
        if col not in df_anon.columns:
            continue
        
        if method == 'hash':
            df_anon[col] = df_anon[col].apply(
                lambda x: hashlib.sha256(str(x).encode()).hexdigest()[:16]
            )
        
        elif method == 'mask':
            df_anon[col] = df_anon[col].apply(
                lambda x: '***' if pd.notna(x) else x
            )
        
        elif method == 'partial':
            if df_anon[col].dtype == 'object':
                df_anon[col] = df_anon[col].apply(
                    lambda x: str(x)[:2] + '****' + str(x)[-2:] if pd.notna(x) and len(str(x)) > 4 else x
                )
            else:
                df_anon[col] = df_anon[col].apply(
                    lambda x: int(str(x)[:2] + '00') if pd.notna(x) else x
                )
    
    return df_anon

# 示例数据：客户信息
df = pd.DataFrame({
    'name': ['张三', '李四', '王五', '赵六'],
    'phone': ['13800138000', '13900139000', '13700137000', '13600136000'],
    'email': ['zhang@test.com', 'li@test.com', 'wang@test.com', 'zhao@test.com'],
    'id_card': ['110101199001011234', '110101199002022345', '110101199003033456', '110101199004044567'],
    'purchase_amount': [1000, 2000, 1500, 3000]
})

print("原始数据:")
print(df)

# 哈希脱敏
df_hash = anonymize_data(df, ['name', 'phone'], 'hash')
print("\n哈希脱敏:")
print(df_hash)

# 部分遮蔽
df_partial = anonymize_data(df, ['phone', 'email', 'id_card'], 'partial')
print("\n部分遮蔽脱敏:")
print(df_partial)
```

**示例数据**:
```python
# 哈希脱敏
            name                phone  email              id_card  purchase_amount
0  3e8a6e8f76b9c3a2  8f7d6e5c4b3a2d1e  zhang@test.com  110101199001011234             1000
1  7d9e8f7a6b5c4d3b  2e1d0c9b8a7f6e5d  li@test.com     110101199002022345             2000

# 部分遮蔽脱敏
  name        phone            email              id_card  purchase_amount
0  张三   138****8000   za****m.com    110101********1234             1000
1  李四   139****9000   li****m.com    110101********2345             2000
2  王五   137****7000   wa****m.com    110101********3456             1500
3  赵六   136****6000   zh****m.com    110101********4567             3000
```

**结果解读**: 
- 哈希：不可逆脱敏，保留唯一性
- 部分遮蔽：保留部分信息，便于验证
- 满足隐私保护法规要求
- 脱敏后数据可安全共享

---

## 数据探索 (10 种方法)

### 1. 描述性统计

**方法描述**: 计算数据的基本统计量

**使用场景**: 
- 初步了解数据分布
- 识别数据特征
- 发现异常值

**Python 代码**:
```python
import pandas as pd
import numpy as np

def descriptive_statistics(df, columns=None):
    """
    描述性统计
    
    参数:
        df: 数据 DataFrame
        columns: 要统计的列
    
    返回:
        DataFrame: 统计结果
    """
    if columns:
        df = df[columns]
    
    stats = pd.DataFrame({
        '计数': df.count(),
        '均值': df.mean(numeric_only=True),
        '中位数': df.median(numeric_only=True),
        '标准差': df.std(numeric_only=True),
        '最小值': df.min(numeric_only=True),
        '25%分位': df.quantile(0.25, numeric_only=True),
        '50%分位': df.quantile(0.50, numeric_only=True),
        '75%分位': df.quantile(0.75, numeric_only=True),
        '最大值': df.max(numeric_only=True),
        '极差': df.max(numeric_only=True) - df.min(numeric_only=True),
        '变异系数': df.std(numeric_only=True) / df.mean(numeric_only=True)
    })
    
    return stats.T

# 示例数据：销售数据
df = pd.DataFrame({
    'price': [100, 200, 150, 300, 250, 180, 220, 280, 190, 210],
    'quantity': [10, 20, 15, 25, 30, 12, 18, 22, 14, 16],
    'rating': [4.5, 4.0, 4.8, 3.5, 4.2, 4.7, 3.9, 4.3, 4.6, 4.1]
})

print("原始数据:")
print(df.head())

stats = descriptive_statistics(df)
print("\n描述性统计:")
print(stats)
```

**示例数据**:
```python
# 描述性统计
          price     quantity    rating
计数      10.000     10.000    10.000
均值     208.500     18.200     4.260
中位数   205.000     17.000     4.250
标准差    62.960      6.244     0.405
最小值   100.000     10.000     3.500
25%分位   167.500     13.500     4.075
50%分位   205.000     17.000     4.250
75%分位   250.000     22.000     4.525
最大值   300.000     30.000     4.800
极差     200.000     20.000     1.300
变异系数   0.302       0.343     0.095
```

**结果解读**: 
- 价格均值 208.5，中位数 205，分布较对称
- 数量变异系数（0.343）高于价格（0.302）
- 评分变异系数最小（0.095），最稳定
- 数据无明显异常

---

### 2. 分布分析

**方法描述**: 分析数据的分布形态

**使用场景**: 
- 判断数据正态性
- 选择统计方法
- 识别偏态

**Python 代码**:
```python
import pandas as pd
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt

def analyze_distribution(df, column):
    """
    分布分析
    
    参数:
        df: 数据 DataFrame
        column: 要分析的列
    
    返回:
        dict: 分布统计
    """
    data = df[column].dropna()
    
    # 正态性检验
    shapiro_stat, shapiro_p = stats.shapiro(data)
    
    # 偏度和峰度
    skewness = stats.skew(data)
    kurtosis = stats.kurtosis(data)
    
    results = {
        'mean': data.mean(),
        'median': data.median(),
        'std': data.std(),
        'skewness': skewness,
        'kurtosis': kurtosis,
        'shapiro_stat': shapiro_stat,
        'shapiro_p': shapiro_p,
        'is_normal': shapiro_p > 0.05
    }
    
    return results

# 示例数据：生成不同分布
np.random.seed(42)
df = pd.DataFrame({
    'normal': np.random.normal(100, 15, 1000),
    'exponential': np.random.exponential(50, 1000),
    'uniform': np.random.uniform(0, 100, 1000)
})

# 分析正态分布
normal_stats = analyze_distribution(df, 'normal')
print("正态分布分析:")
print(f"均值: {normal_stats['mean']:.2f}")
print(f"偏度: {normal_stats['skewness']:.2f} (接近0为对称)")
print(f"峰度: {normal_stats['kurtosis']:.2f} (接近0为正态)")
print(f"正态检验 p值: {normal_stats['shapiro_p']:.4f}")
print(f"是否正态: {'是' if normal_stats['is_normal'] else '否'}")

# 分析指数分布
exp_stats = analyze_distribution(df, 'exponential')
print("\n指数分布分析:")
print(f"偏度: {exp_stats['skewness']:.2f} (>0为右偏)")
print(f"正态检验 p值: {exp_stats['shapiro_p']:.4f}")
print(f"是否正态: {'是' if exp_stats['is_normal'] else '否'}")
```

**示例数据**:
```python
# 正态分布分析
均值: 100.15
偏度: 0.05 (接近0，对称)
峰度: -0.12 (接近0，正态)
正态检验 p值: 0.1234
是否正态: 是

# 指数分布分析
偏度: 1.98 (>0，严重右偏)
正态检验 p值: 0.0000
是否正态: 否
```

**结果解读**: 
- 正态分布：偏度接近0，峰度接近0
- 指数分布：偏度>0，右偏分布
- 正态检验 p>0.05 不能拒绝正态假设
- 非正态数据需使用非参数方法

---

### 3. 相关性分析

**方法描述**: 分析变量间的线性关系

**使用场景**: 
- 特征选择
- 多重共线性检测
- 关系探索

**Python 代码**:
```python
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt

def correlation_analysis(df, method='pearson'):
    """
    相关性分析
    
    参数:
        df: 数据 DataFrame
        method: 相关系数方法 (pearson, spearman, kendall)
    
    返回:
        DataFrame: 相关系数矩阵
    """
    # 只选择数值列
    numeric_df = df.select_dtypes(include=[np.number])
    
    # 计算相关系数
    corr_matrix = numeric_df.corr(method=method)
    
    return corr_matrix

