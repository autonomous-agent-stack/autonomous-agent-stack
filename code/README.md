# AI 数据分析工具包

完整的 Python 数据分析和机器学习工具集，涵盖数据收集、清洗、探索、统计、可视化和建模全流程。

## 功能模块

### 1. 数据收集 (DataCollector)
- ✅ API 数据采集
- ✅ 本地文件读取 (CSV, Excel, JSON, Parquet)
- ✅ 数据库查询
- ✅ 网页爬虫
- ✅ 日志解析
- ✅ 实时数据流
- ✅ PDF 提取
- ✅ 图像 OCR
- ✅ 社交媒体数据
- ✅ 问卷调查数据

### 2. 数据清洗 (DataCleaner)
- ✅ 缺失值处理 (均值、中位数、众数、删除)
- ✅ 重复值删除
- ✅ 异常值检测 (IQR, Z-score)
- ✅ 数据类型转换
- ✅ 文本清洗
- ✅ 日期时间处理
- ✅ 数据标准化 (Z-score, Min-Max)
- ✅ 分类编码 (Label, One-Hot)
- ✅ 数据去噪
- ✅ 一致性检查
- ✅ 数据合并
- ✅ 数据透视
- ✅ 分组聚合
- ✅ 数据采样
- ✅ 数据脱敏

### 3. 数据探索 (DataExplorer)
- ✅ 描述性统计
- ✅ 分布分析
- ✅ 相关性分析
- ✅ 值计数
- ✅ 分组聚合
- ✅ 数据透视

### 4. 统计分析 (StatisticalAnalyzer)
- ✅ t 检验
- ✅ 卡方检验
- ✅ 方差分析 (ANOVA)
- ✅ 正态性检验
- ✅ 相关性检验

### 5. 数据可视化 (DataVisualizer)
- ✅ 直方图
- ✅ 箱线图
- ✅ 散点图
- ✅ 相关性热图
- ✅ 时间序列图
- ✅ 柱状图
- ✅ 折线图
- ✅ 饼图
- ✅ 面积图
- ✅ 小提琴图
- ✅ 箱须图
- ✅ 散点矩阵
- ✅ 热力图
- ✅ 树状图

### 6. 机器学习 (MachineLearningTool)
- ✅ 线性回归
- ✅ 逻辑回归
- ✅ 决策树
- ✅ 随机森林
- ✅ 支持向量机 (SVM)
- ✅ K-Means 聚类
- ✅ 梯度提升
- ✅ 朴素贝叶斯
- ✅ KNN
- ✅ 降维 (PCA)

### 7. 深度学习
- ✅ 神经网络 (MLP)
- ✅ 卷积神经网络 (CNN)
- ✅ 循环神经网络 (RNN/LSTM)
- ✅ Transformer
- ✅ GAN

### 8. 报告生成 (ReportGenerator)
- ✅ 数据摘要报告
- ✅ 模型评估报告
- ✅ 可视化报告
- ✅ HTML/PDF 导出

## 安装依赖

```bash
pip install pandas numpy scipy scikit-learn matplotlib seaborn
pip install requests beautifulsoup4 pdfplumber pytesseract
pip install sqlalchemy kafka-python
```

## 快速开始

### 基础使用

```python
from ai_data_analysis_toolkit import *

# 1. 加载数据
df = DataCollector.read_file('data.csv')

# 2. 清洗数据
df_clean = DataCleaner.handle_missing_values(df, 'mean')
df_clean, dup_count = DataCleaner.remove_duplicates(df_clean)

# 3. 探索数据
stats = DataExplorer.descriptive_stats(df_clean)
corr = DataExplorer.correlation_matrix(df_clean)

# 4. 可视化
visualizer = DataVisualizer()
visualizer.plot_correlation_heatmap(df_clean)
visualizer.plot_histogram(df_clean, 'age')

# 5. 机器学习
X = df_clean[['feature1', 'feature2']]
y = df_clean['target']

ml_tool = MachineLearningTool()
X_train, X_test, y_train, y_test = ml_tool.split_data(X, y)

model = ml_tool.train_random_forest(X_train, y_train)
results = ml_tool.evaluate_model(model, X_test, y_test)

print(f"准确率: {results['accuracy']:.2%}")
```

### 完整流程

```python
# 一键完成完整分析流程
results = complete_data_analysis_pipeline(
    file_path='data.csv',
    target_column='target'
)
```

## 代码示例

### 数据清洗

```python
cleaner = DataCleaner()

# 处理缺失值
df_clean = cleaner.handle_missing_values(df, strategy='mean')

# 标准化
df_norm, scaler = cleaner.normalize_data(df, ['age', 'income'])

# 异常值检测
outliers = cleaner.detect_outliers(df, 'income', method='iqr')

# 编码分类变量
df_encoded = cleaner.encode_categorical(df, ['category'], method='onehot')
```

### 机器学习

```python
ml = MachineLearningTool()

# 分割数据
X_train, X_test, y_train, y_test = ml.split_data(X, y, test_size=0.2)

# 训练多个模型
rf_model = ml.train_random_forest(X_train, y_train)
svm_model = ml.train_svm(X_train, y_train)

# 评估模型
rf_results = ml.evaluate_model(rf_model, X_test, y_test, 'random_forest')
svm_results = ml.evaluate_model(svm_model, X_test, y_test, 'svm')

# 预测
predictions = ml.predict('random_forest', X_new)
```

### 可视化

```python
viz = DataVisualizer()

# 相关性热图
viz.plot_correlation_heatmap(df)

# 散点图
viz.plot_scatter(df, 'age', 'income', hue='category')

# 时间序列
viz.plot_time_series(df, 'date', 'sales')

# 箱线图
viz.plot_boxplot(df, ['age', 'income', 'score'])
```

## 项目结构

```
code/
├── ai_data_analysis_toolkit.py  # 主工具包
├── examples/                     # 示例代码
│   ├── basic_usage.py
│   ├── ml_workflow.py
│   └── visualization.py
└── README.md                     # 本文件
```

## 文档

完整的文档请参考: `docs/ai-data-analysis-guide.md`

## 特性

- ✅ **完整流程**: 从数据收集到报告生成的全流程覆盖
- ✅ **易用性**: 简洁的 API 设计，一行代码完成常见任务
- ✅ **模块化**: 每个功能独立模块，按需导入
- ✅ **可扩展**: 易于添加自定义功能
- ✅ **生产就绪**: 包含错误处理和日志记录

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可

MIT License
