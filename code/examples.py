"""
AI 数据分析工具包使用示例
演示各种数据分析场景的实际应用
"""

import sys
sys.path.append('..')

import pandas as pd
import numpy as np
from ai_data_analysis_toolkit import *

# 设置随机种子
np.random.seed(42)

print("=" * 80)
print("AI 数据分析工具包 - 使用示例")
print("=" * 80)

# ==================== 示例 1: 客户数据分析 ====================

print("\n【示例 1】客户数据分析")
print("-" * 80)

# 创建客户数据
customer_data = pd.DataFrame({
    'customer_id': range(1, 101),
    'age': np.random.randint(18, 70, 100),
    'income': np.random.normal(50000, 15000, 100),
    'spending_score': np.random.randint(1, 100, 100),
    'membership_years': np.random.randint(0, 20, 100),
    'segment': np.random.choice(['VIP', 'Regular', 'New'], 100, p=[0.15, 0.60, 0.25])
})

print("1.1 原始数据:")
print(customer_data.head(10))

# 数据清洗
print("\n1.2 数据清洗:")
cleaner = DataCleaner()

# 检查异常值
age_outliers = cleaner.detect_outliers(customer_data, 'age', method='iqr')
print(f"年龄异常值: {len(age_outliers)} 个")

income_outliers = cleaner.detect_outliers(customer_data, 'income', method='iqr')
print(f"收入异常值: {len(income_outliers)} 个")

# 数据探索
print("\n1.3 数据探索:")
explorer = DataExplorer()

stats = explorer.descriptive_stats(customer_data)
print("\n描述性统计:")
print(stats[['age', 'income', 'spending_score']])

# 分组统计
segment_stats = explorer.group_aggregate(
    customer_data,
    'segment',
    {'age': 'mean', 'income': 'mean', 'spending_score': 'mean'}
)
print("\n按客户分组的平均统计:")
print(segment_stats)

# 相关性分析
print("\n1.4 相关性分析:")
corr_matrix = explorer.correlation_matrix(customer_data)
print("相关性矩阵:")
print(corr_matrix)

# 机器学习 - 客户细分
print("\n1.5 客户细分 (K-Means 聚类):")
ml = MachineLearningTool()

# 选择数值特征
X = customer_data[['age', 'income', 'spending_score', 'membership_years']]
kmeans, labels = ml.train_kmeans(X, n_clusters=3)

customer_data['cluster'] = labels
print("\n聚类结果:")
print(customer_data.groupby('cluster').agg({
    'age': 'mean',
    'income': 'mean',
    'spending_score': 'mean',
    'customer_id': 'count'
}).rename(columns={'customer_id': 'count'}))

# ==================== 示例 2: 销售预测 ====================

print("\n\n【示例 2】销售预测")
print("-" * 80)

# 创建销售数据
dates = pd.date_range('2023-01-01', periods=365, freq='D')
sales_data = pd.DataFrame({
    'date': dates,
    'sales': np.random.poisson(100, 365) + np.sin(np.arange(365) * 2 * np.pi / 365) * 20,
    'advertising': np.random.uniform(50, 150, 365),
    'price': np.random.uniform(10, 30, 365),
    'holiday': np.random.choice([0, 1], 365, p=[0.9, 0.1])
})

# 添加时间特征
sales_data['day_of_week'] = sales_data['date'].dt.dayofweek
sales_data['month'] = sales_data['date'].dt.month
sales_data['is_weekend'] = sales_data['day_of_week'] >= 5

print("2.1 销售数据:")
print(sales_data.head(10))

# 特征工程
print("\n2.2 特征工程:")
features = ['advertising', 'price', 'holiday', 'day_of_week', 'month', 'is_weekend']
X = sales_data[features]
y = sales_data['sales']

# 分割数据
X_train, X_test, y_train, y_test = ml.split_data(X, y, test_size=0.2)
print(f"训练集: {X_train.shape}, 测试集: {X_test.shape}")

# 训练模型
print("\n2.3 训练预测模型:")
rf_model = ml.train_random_forest(X_train, y_train, n_estimators=100)
rf_results = ml.evaluate_model(rf_model, X_test, y_test, 'random_forest')

# 转换为分类问题评估
y_test_class = (y_test > y_test.median()).astype(int)
y_pred_class = (rf_model.predict(X_test) > y_test.median()).astype(int)

from sklearn.metrics import accuracy_score
accuracy = accuracy_score(y_test_class, y_pred_class)
print(f"随机森林 R²: {rf_model.score(X_test, y_test):.3f}")
print(f"分类准确率: {accuracy:.3f}")

# ==================== 示例 3: 质量控制分析 ====================

print("\n\n【示例 3】质量控制分析")
print("-" * 80)

# 创建产品质量数据
quality_data = pd.DataFrame({
    'product_id': [f'P{i:03d}' for i in range(1, 201)],
    'weight': np.random.normal(100, 5, 200),
    'length': np.random.normal(50, 2, 200),
    'width': np.random.normal(30, 1, 200),
    'defect': np.random.choice([0, 1], 200, p=[0.85, 0.15])
})

# 添加一些缺陷产品的异常值
defect_indices = np.random.choice(quality_data.index, 30, replace=False)
quality_data.loc[defect_indices, 'weight'] += np.random.uniform(-15, 15, 30)
quality_data.loc[defect_indices, 'length'] += np.random.uniform(-8, 8, 30)

print("3.1 质量数据:")
print(quality_data.head(10))

# 质量统计
print("\n3.2 质量统计:")
good_quality = quality_data[quality_data['defect'] == 0]
bad_quality = quality_data[quality_data['defect'] == 1]

print("合格品统计:")
print(good_quality[['weight', 'length', 'width']].describe())

print("\n不合格品统计:")
print(bad_quality[['weight', 'length', 'width']].describe())

# 统计检验
print("\n3.3 统计检验 (合格品 vs 不合格品):")
stat_analyzer = StatisticalAnalyzer()

t_test_weight = stat_analyzer.t_test(good_quality['weight'], bad_quality['weight'])
print(f"重量 t 检验: t={t_test_weight['statistic']:.3f}, p={t_test_weight['p_value']:.4f}")
print(f"  差异显著: {'是' if t_test_weight['significant'] else '否'}")

t_test_length = stat_analyzer.t_test(good_quality['length'], bad_quality['length'])
print(f"长度 t 检验: t={t_test_length['statistic']:.3f}, p={t_test_length['p_value']:.4f}")
print(f"  差异显著: {'是' if t_test_length['significant'] else '否'}")

# 分类模型
print("\n3.4 缺陷预测模型:")
X = quality_data[['weight', 'length', 'width']]
y = quality_data['defect']

X_train, X_test, y_train, y_test = ml.split_data(X, y, test_size=0.3)

# 训练决策树
dt_model = ml.train_decision_tree(X_train, y_train, max_depth=5)
dt_results = ml.evaluate_model(dt_model, X_test, y_test, 'decision_tree')

print(f"决策树准确率: {dt_results['accuracy']:.3f}")
print("\n分类报告:")
print(dt_results['report'])

# ==================== 示例 4: A/B 测试分析 ====================

print("\n\n【示例 4】A/B 测试分析")
print("-" * 80)

# 创建 A/B 测试数据
ab_test_data = pd.DataFrame({
    'user_id': range(1, 1001),
    'group': np.random.choice(['A', 'B'], 1000),
    'conversion': np.random.choice([0, 1], 1000, p=[0.8, 0.2])
})

# B 组有稍高的转化率
ab_test_data.loc[ab_test_data['group'] == 'B', 'conversion'] = np.random.choice(
    [0, 1], 
    500, 
    p=[0.75, 0.25]
)

print("4.1 A/B 测试数据:")
print(ab_test_data.head(10))

# 转化率统计
print("\n4.2 转化率分析:")
conversion_rates = ab_test_data.groupby('group')['conversion'].agg(['mean', 'count'])
conversion_rates.columns = ['conversion_rate', 'sample_size']
print(conversion_rates)

# 统计检验
print("\n4.3 显著性检验:")
group_a = ab_test_data[ab_test_data['group'] == 'A']['conversion']
group_b = ab_test_data[ab_test_data['group'] == 'B']['conversion']

from scipy.stats import chi2_contingency
contingency_table = pd.crosstab(ab_test_data['group'], ab_test_data['conversion'])
chi2, p_value, dof, expected = chi2_contingency(contingency_table)

print(f"卡方检验: χ²={chi2:.3f}, p={p_value:.4f}")
print(f"差异显著: {'是' if p_value < 0.05 else '否'}")

# 计算提升
rate_a = conversion_rates.loc['A', 'conversion_rate']
rate_b = conversion_rates.loc['B', 'conversion_rate']
lift = (rate_b - rate_a) / rate_a * 100

print(f"\n转化率提升: {lift:.2f}%")
print(f"A 组转化率: {rate_a:.2%}")
print(f"B 组转化率: {rate_b:.2%}")

# ==================== 示例 5: 时间序列分析 ====================

print("\n\n【示例 5】时间序列分析")
print("-" * 80)

# 创建时间序列数据
dates = pd.date_range('2023-01-01', periods=365, freq='D')
ts_data = pd.DataFrame({
    'date': dates,
    'value': np.cumsum(np.random.randn(365)) + 100
})

# 添加趋势和季节性
ts_data['value'] += np.arange(365) * 0.1  # 趋势
ts_data['value'] += np.sin(np.arange(365) * 2 * np.pi / 30) * 5  # 月度季节性

print("5.1 时间序列数据:")
print(ts_data.head(10))

# 滚动统计
print("\n5.2 滚动统计:")
ts_data['MA7'] = ts_data['value'].rolling(window=7).mean()
ts_data['MA30'] = ts_data['value'].rolling(window=30).mean()
ts_data['STD30'] = ts_data['value'].rolling(window=30).std()

print("\n最近30天统计:")
print(ts_data[['date', 'value', 'MA7', 'MA30', 'STD30']].tail(10))

# 趋势分析
print("\n5.3 趋势分析:")
from scipy.stats import linregress
x = np.arange(len(ts_data))
slope, intercept, r_value, p_value, std_err = linregress(x, ts_data['value'])

print(f"线性趋势斜率: {slope:.4f}")
print(f"R²: {r_value**2:.4f}")
print(f"趋势: {'上升' if slope > 0 else '下降'}")

# ==================== 生成综合报告 ====================

print("\n\n【生成综合报告】")
print("-" * 80)

report_gen = ReportGenerator()

# 客户分析报告
customer_report = report_gen.generate_summary_report(
    customer_data,
    "客户数据分析报告"
)
report_gen.save_report(customer_report, 'customer_analysis_report.md')
print("✓ 客户分析报告已生成")

# 销售分析报告
sales_report = report_gen.generate_summary_report(
    sales_data,
    "销售数据分析报告"
)
report_gen.save_report(sales_report, 'sales_analysis_report.md')
print("✓ 销售分析报告已生成")

# 质量分析报告
quality_report = report_gen.generate_summary_report(
    quality_data,
    "质量分析报告"
)
report_gen.save_report(quality_report, 'quality_analysis_report.md')
print("✓ 质量分析报告已生成")

print("\n" + "=" * 80)
print("所有示例执行完成！")
print("=" * 80)

# 输出数据摘要
print("\n【数据摘要】")
print(f"客户数据: {len(customer_data)} 条记录, {len(customer_data.columns)} 个字段")
print(f"销售数据: {len(sales_data)} 条记录, {len(sales_data.columns)} 个字段")
print(f"质量数据: {len(quality_data)} 条记录, {len(quality_data.columns)} 个字段")
print(f"A/B 测试数据: {len(ab_test_data)} 条记录, {len(ab_test_data.columns)} 个字段")
print(f"时间序列数据: {len(ts_data)} 条记录, {len(ts_data.columns)} 个字段")

print("\n【生成的文件】")
print("- customer_analysis_report.md")
print("- sales_analysis_report.md")
print("- quality_analysis_report.md")
