"""
AI 数据分析工具包
完整的 Python 数据分析和机器学习工具集
"""

import pandas as pd
import numpy as np
from scipy import stats
from scipy.signal import savgol_filter
from sklearn.preprocessing import StandardScaler, MinMaxScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.cluster import KMeans
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

# ==================== 数据收集工具 ====================

class DataCollector:
    """数据收集工具类"""
    
    @staticmethod
    def fetch_api_data(url, params=None):
        """从 API 获取数据"""
        import requests
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return pd.DataFrame(response.json())
        except Exception as e:
            print(f"API 请求失败: {e}")
            return None
    
    @staticmethod
    def read_file(file_path, file_type='csv'):
        """读取本地文件"""
        try:
            if file_type == 'csv':
                return pd.read_csv(file_path, encoding='utf-8')
            elif file_type == 'excel':
                return pd.read_excel(file_path)
            elif file_type == 'json':
                import json
                with open(file_path, 'r', encoding='utf-8') as f:
                    return pd.DataFrame(json.load(f))
            elif file_type == 'parquet':
                return pd.read_parquet(file_path)
        except Exception as e:
            print(f"文件读取失败: {e}")
            return None
    
    @staticmethod
    def query_database(db_path, query):
        """从数据库查询"""
        import sqlite3
        try:
            conn = sqlite3.connect(db_path)
            df = pd.read_sql_query(query, conn)
            conn.close()
            return df
        except Exception as e:
            print(f"数据库查询失败: {e}")
            return None

# ==================== 数据清洗工具 ====================

class DataCleaner:
    """数据清洗工具类"""
    
    @staticmethod
    def handle_missing_values(df, strategy='mean'):
        """处理缺失值"""
        df_clean = df.copy()
        
        if strategy == 'drop':
            df_clean = df_clean.dropna()
        elif strategy == 'mean':
            numeric_cols = df_clean.select_dtypes(include=[np.number]).columns
            df_clean[numeric_cols] = df_clean[numeric_cols].fillna(
                df_clean[numeric_cols].mean()
            )
        elif strategy == 'median':
            numeric_cols = df_clean.select_dtypes(include=[np.number]).columns
            df_clean[numeric_cols] = df_clean[numeric_cols].fillna(
                df_clean[numeric_cols].median()
            )
        elif strategy == 'mode':
            for col in df_clean.columns:
                mode_val = df_clean[col].mode()
                if len(mode_val) > 0:
                    df_clean[col] = df_clean[col].fillna(mode_val[0])
        
        return df_clean
    
    @staticmethod
    def remove_duplicates(df, subset=None, keep='first'):
        """删除重复值"""
        before_len = len(df)
        df_clean = df.drop_duplicates(subset=subset, keep=keep)
        removed = before_len - len(df_clean)
        return df_clean, removed
    
    @staticmethod
    def detect_outliers(df, column, method='iqr', threshold=1.5):
        """检测异常值"""
        data = df[column].dropna()
        
        if method == 'iqr':
            Q1 = data.quantile(0.25)
            Q3 = data.quantile(0.75)
            IQR = Q3 - Q1
            lower = Q1 - threshold * IQR
            upper = Q3 + threshold * IQR
            outlier_mask = (data < lower) | (data > upper)
        elif method == 'zscore':
            z_scores = np.abs(stats.zscore(data))
            outlier_mask = z_scores > threshold
        
        return data[outlier_mask].index
    
    @staticmethod
    def normalize_data(df, numeric_columns, method='standard'):
        """数据标准化"""
        df_normalized = df.copy()
        
        if method == 'standard':
            scaler = StandardScaler()
        elif method == 'minmax':
            scaler = MinMaxScaler()
        else:
            raise ValueError(f"未知方法: {method}")
        
        df_normalized[numeric_columns] = scaler.fit_transform(
            df_normalized[numeric_columns]
        )
        
        return df_normalized, scaler
    
    @staticmethod
    def encode_categorical(df, categorical_columns, method='label'):
        """编码分类变量"""
        df_encoded = df.copy()
        
        if method == 'label':
            le = LabelEncoder()
            for col in categorical_columns:
                if col in df_encoded.columns:
                    df_encoded[col] = le.fit_transform(df_encoded[col])
        elif method == 'onehot':
            df_encoded = pd.get_dummies(
                df_encoded, 
                columns=categorical_columns, 
                drop_first=False
            )
        
        return df_encoded
    
    @staticmethod
    def clean_text(text):
        """清洗文本"""
        import re
        
        if not isinstance(text, str):
            return text
        
        # 转小写
        text = text.lower()
        # 移除特殊字符
        text = re.sub(r'[^\w\s]', '', text)
        # 移除多余空格
        text = ' '.join(text.split())
        
        return text

# ==================== 数据探索工具 ====================

class DataExplorer:
    """数据探索工具类"""
    
    @staticmethod
    def descriptive_stats(df, columns=None):
        """描述性统计"""
        if columns:
            df = df[columns]
        
        return df.describe(include='all')
    
    @staticmethod
    def correlation_matrix(df, method='pearson'):
        """相关系数矩阵"""
        numeric_df = df.select_dtypes(include=[np.number])
        return numeric_df.corr(method=method)
    
    @staticmethod
    def value_counts(df, column):
        """值计数"""
        return df[column].value_counts()
    
    @staticmethod
    def group_aggregate(df, group_by, agg_dict):
        """分组聚合"""
        return df.groupby(group_by).agg(agg_dict)
    
    @staticmethod
    def pivot_table(df, index, columns, values, aggfunc='mean'):
        """数据透视"""
        return df.pivot_table(
            index=index,
            columns=columns,
            values=values,
            aggfunc=aggfunc,
            fill_value=0
        )

# ==================== 统计分析工具 ====================

class StatisticalAnalyzer:
    """统计分析工具类"""
    
    @staticmethod
    def t_test(sample1, sample2):
        """独立样本 t 检验"""
        statistic, p_value = stats.ttest_ind(sample1, sample2)
        return {
            'statistic': statistic,
            'p_value': p_value,
            'significant': p_value < 0.05
        }
    
    @staticmethod
    def chi_square(observed, expected=None):
        """卡方检验"""
        if expected is None:
            # 期望值假设为均匀分布
            expected = np.ones_like(observed) * observed.mean()
        
        statistic, p_value = stats.chisquare(observed, expected)
        return {
            'statistic': statistic,
            'p_value': p_value,
            'significant': p_value < 0.05
        }
    
    @staticmethod
    def anova(*samples):
        """单因素方差分析"""
        statistic, p_value = stats.f_oneway(*samples)
        return {
            'statistic': statistic,
            'p_value': p_value,
            'significant': p_value < 0.05
        }
    
    @staticmethod
    def normality_test(data):
        """正态性检验"""
        statistic, p_value = stats.shapiro(data)
        return {
            'statistic': statistic,
            'p_value': p_value,
            'is_normal': p_value > 0.05
        }

# ==================== 可视化工具 ====================

class DataVisualizer:
    """数据可视化工具类"""
    
    @staticmethod
    def plot_histogram(df, column, bins=30):
        """直方图"""
        plt.figure(figsize=(10, 6))
        plt.hist(df[column].dropna(), bins=bins, edgecolor='black')
        plt.title(f'{column} 分布')
        plt.xlabel(column)
        plt.ylabel('频数')
        plt.grid(True, alpha=0.3)
        plt.show()
    
    @staticmethod
    def plot_boxplot(df, columns):
        """箱线图"""
        plt.figure(figsize=(12, 6))
        df[columns].boxplot()
        plt.title('箱线图')
        plt.ylabel('值')
        plt.grid(True, alpha=0.3)
        plt.show()
    
    @staticmethod
    def plot_scatter(df, x, y, hue=None):
        """散点图"""
        plt.figure(figsize=(10, 6))
        
        if hue:
            for category in df[hue].unique():
                data = df[df[hue] == category]
                plt.scatter(data[x], data[y], label=category, alpha=0.6)
            plt.legend()
        else:
            plt.scatter(df[x], df[y], alpha=0.6)
        
        plt.xlabel(x)
        plt.ylabel(y)
        plt.title(f'{x} vs {y}')
        plt.grid(True, alpha=0.3)
        plt.show()
    
    @staticmethod
    def plot_correlation_heatmap(df):
        """相关性热图"""
        corr = df.select_dtypes(include=[np.number]).corr()
        
        plt.figure(figsize=(12, 10))
        sns.heatmap(corr, annot=True, cmap='coolwarm', center=0,
                    square=True, linewidths=1)
        plt.title('相关性热图')
        plt.show()
    
    @staticmethod
    def plot_time_series(df, date_column, value_column):
        """时间序列图"""
        df_sorted = df.sort_values(date_column)
        
        plt.figure(figsize=(14, 6))
        plt.plot(df_sorted[date_column], df_sorted[value_column])
        plt.xlabel('日期')
        plt.ylabel(value_column)
        plt.title(f'{value_column} 时间序列')
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.show()
    
    @staticmethod
    def plot_bar_chart(df, x_column, y_column):
        """柱状图"""
        plt.figure(figsize=(12, 6))
        plt.bar(df[x_column], df[y_column])
        plt.xlabel(x_column)
        plt.ylabel(y_column)
        plt.title(f'{y_column} by {x_column}')
        plt.xticks(rotation=45)
        plt.grid(True, alpha=0.3, axis='y')
        plt.show()

# ==================== 机器学习工具 ====================

class MachineLearningTool:
    """机器学习工具类"""
    
    def __init__(self):
        self.models = {}
        self.results = {}
    
    def split_data(self, X, y, test_size=0.2, random_state=42):
        """分割数据集"""
        return train_test_split(X, y, test_size=test_size, random_state=random_state)
    
    def train_linear_regression(self, X_train, y_train):
        """训练线性回归"""
        model = LinearRegression()
        model.fit(X_train, y_train)
        self.models['linear_regression'] = model
        return model
    
    def train_logistic_regression(self, X_train, y_train):
        """训练逻辑回归"""
        model = LogisticRegression(max_iter=1000)
        model.fit(X_train, y_train)
        self.models['logistic_regression'] = model
        return model
    
    def train_decision_tree(self, X_train, y_train, max_depth=5):
        """训练决策树"""
        model = DecisionTreeClassifier(max_depth=max_depth, random_state=42)
        model.fit(X_train, y_train)
        self.models['decision_tree'] = model
        return model
    
    def train_random_forest(self, X_train, y_train, n_estimators=100):
        """训练随机森林"""
        model = RandomForestClassifier(n_estimators=n_estimators, random_state=42)
        model.fit(X_train, y_train)
        self.models['random_forest'] = model
        return model
    
    def train_svm(self, X_train, y_train):
        """训练支持向量机"""
        model = SVC(kernel='rbf', random_state=42)
        model.fit(X_train, y_train)
        self.models['svm'] = model
        return model
    
    def train_kmeans(self, X, n_clusters=3):
        """训练 K-Means 聚类"""
        model = KMeans(n_clusters=n_clusters, random_state=42)
        labels = model.fit_predict(X)
        self.models['kmeans'] = model
        return model, labels
    
    def evaluate_model(self, model, X_test, y_test, model_name='model'):
        """评估模型"""
        y_pred = model.predict(X_test)
        
        accuracy = accuracy_score(y_test, y_pred)
        report = classification_report(y_test, y_pred)
        conf_matrix = confusion_matrix(y_test, y_pred)
        
        self.results[model_name] = {
            'accuracy': accuracy,
            'report': report,
            'confusion_matrix': conf_matrix
        }
        
        return {
            'accuracy': accuracy,
            'report': report,
            'confusion_matrix': conf_matrix
        }
    
    def predict(self, model_name, X):
        """使用模型预测"""
        if model_name not in self.models:
            raise ValueError(f"模型 {model_name} 未训练")
        
        return self.models[model_name].predict(X)

# ==================== 报告生成工具 ====================

class ReportGenerator:
    """报告生成工具类"""
    
    @staticmethod
    def generate_summary_report(df, title="数据分析报告"):
        """生成摘要报告"""
        report = f"""
# {title}

## 数据概览
- 总行数: {len(df)}
- 总列数: {len(df.columns)}
- 缺失值: {df.isnull().sum().sum()}
- 重复行: {df.duplicated().sum()}

## 数据类型
{df.dtypes.value_counts().to_string()}

## 描述性统计
{df.describe().to_string()}

## 缺失值统计
{df.isnull().sum().to_string()}
"""
        return report
    
    @staticmethod
    def generate_model_report(results, model_name):
        """生成模型报告"""
        report = f"""
# {model_name} 模型报告

## 准确率
{results['accuracy']:.4f}

## 分类报告
{results['report']}

## 混淆矩阵
{results['confusion_matrix']}
"""
        return report
    
    @staticmethod
    def save_report(report, file_path):
        """保存报告到文件"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"报告已保存到: {file_path}")

# ==================== 完整工作流示例 ====================

def complete_data_analysis_pipeline(file_path, target_column):
    """
    完整的数据分析流程
    
    参数:
        file_path: 数据文件路径
        target_column: 目标列名
    
    返回:
        dict: 分析结果
    """
    print("=" * 60)
    print("AI 数据分析完整流程")
    print("=" * 60)
    
    # 1. 数据收集
    print("\n[1] 数据收集...")
    df = DataCollector.read_file(file_path)
    print(f"✓ 数据加载成功: {df.shape}")
    
    # 2. 数据清洗
    print("\n[2] 数据清洗...")
    df_clean = DataCleaner.handle_missing_values(df, 'mean')
    df_clean, dup_count = DataCleaner.remove_duplicates(df_clean)
    print(f"✓ 清洗完成: 删除 {dup_count} 条重复")
    
    # 3. 数据探索
    print("\n[3] 数据探索...")
    stats = DataExplorer.descriptive_stats(df_clean)
    print(f"✓ 统计描述完成")
    
    # 4. 统计分析
    print("\n[4] 统计分析...")
    corr = DataExplorer.correlation_matrix(df_clean)
    print(f"✓ 相关性分析完成")
    
    # 5. 机器学习
    print("\n[5] 机器学习...")
    if target_column in df_clean.columns:
        # 准备数据
        X = df_clean.select_dtypes(include=[np.number]).drop(columns=[target_column])
        y = df_clean[target_column]
        
        ml_tool = MachineLearningTool()
        X_train, X_test, y_train, y_test = ml_tool.split_data(X, y)
        
        # 训练模型
        model = ml_tool.train_random_forest(X_train, y_train)
        results = ml_tool.evaluate_model(model, X_test, y_test, 'random_forest')
        
        print(f"✓ 模型训练完成: 准确率 {results['accuracy']:.2%}")
    
    # 6. 生成报告
    print("\n[6] 生成报告...")
    report = ReportGenerator.generate_summary_report(df_clean)
    ReportGenerator.save_report(report, 'analysis_report.md')
    print("✓ 报告生成完成")
    
    print("\n" + "=" * 60)
    print("分析完成！")
    print("=" * 60)
    
    return {
        'data': df_clean,
        'statistics': stats,
        'correlation': corr,
        'model_results': results if target_column in df_clean.columns else None
    }

# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 创建示例数据
    np.random.seed(42)
    
    sample_data = pd.DataFrame({
        'age': np.random.randint(18, 80, 1000),
        'income': np.random.normal(50000, 15000, 1000),
        'score': np.random.uniform(0, 100, 1000),
        'category': np.random.choice(['A', 'B', 'C'], 1000),
        'target': np.random.choice([0, 1], 1000)
    })
    
    # 保存示例数据
    sample_data.to_csv('sample_data.csv', index=False)
    
    # 运行完整分析流程
    results = complete_data_analysis_pipeline('sample_data.csv', 'target')
    
    # 生成可视化
    print("\n生成可视化...")
    visualizer = DataVisualizer()
    
    # 相关性热图
    visualizer.plot_correlation_heatmap(sample_data)
    
    # 直方图
    visualizer.plot_histogram(sample_data, 'age')
    
    # 散点图
    visualizer.plot_scatter(sample_data, 'age', 'income', hue='category')
