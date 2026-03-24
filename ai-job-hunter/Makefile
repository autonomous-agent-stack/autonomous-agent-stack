.PHONY: help install test run example clean

# 默认目标
help:
	@echo "AI Job Hunter - 多平台求职工具"
	@echo ""
	@echo "可用命令:"
	@echo "  make install    - 安装依赖"
	@echo "  make test       - 运行示例"
	@echo "  make run        - 运行基础搜索"
	@echo "  make example    - 运行所有示例"
	@echo "  make clean      - 清理生成的文件"
	@echo ""

# 安装依赖
install:
	@echo "📦 安装依赖..."
	pip install -r requirements.txt
	@echo "✅ 安装完成"

# 运行测试示例
test:
	@echo "🧪 运行示例..."
	python example.py

# 运行基础搜索
run:
	@echo "🔍 搜索 AI 工程师职位..."
	python main.py search "AI Engineer" --location "Remote"

# 运行完整示例
example:
	@echo "📚 运行所有示例..."
	python example.py

# 清理生成的文件
clean:
	@echo "🧹 清理生成的文件..."
	rm -f *.json *.csv *.md saved_jobs.json
	@echo "✅ 清理完成"
