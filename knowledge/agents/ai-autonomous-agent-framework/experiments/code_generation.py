# knowledge/agents/ai-autonomous-agent-framework/experiments/code_generation.py

"""
代码生成实验

演示自主 Agent 如何生成和验证代码
"""

import os
import sys

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import AutonomousAgent


class CodeGenerationAgent(AutonomousAgent):
    """代码生成专用 Agent"""

    def __init__(self):
        super().__init__(verbose=True)

        # 注册代码生成工具
        self._register_code_tools()

    def _register_code_tools(self):
        """注册代码生成工具"""

        class CodeTool:
            """代码工具基类"""
            def execute(self, input_data):
                pass

        class GenerateCodeTool(CodeTool):
            """生成代码工具"""
            def execute(self, input_data):
                requirements = input_data.get("requirements", "")
                filepath = input_data.get("filepath", "generated_code.py")

                try:
                    # 简化的代码生成逻辑
                    code = '''# 自动生成的代码
class GeneratedClass:
    """自动生成的类"""

    def __init__(self):
        """初始化"""
        self.data = []

    def add_item(self, item):
        """添加项目"""
        self.data.append(item)

    def get_items(self):
        """获取所有项目"""
        return self.data

    def clear(self):
        """清空数据"""
        self.data.clear()
'''

                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(code)

                    return {
                        "status": "success",
                        "filepath": filepath,
                        "lines": len(code.split('\n')),
                        "message": f"成功生成代码到 {filepath}"
                    }
                except Exception as e:
                    return {"status": "failed", "error": str(e)}

        class RunTestsTool(CodeTool):
            """运行测试工具"""
            def execute(self, input_data):
                filepath = input_data.get("filepath", "generated_code.py")
                test_file = input_data.get("test_file", "test_generated.py")

                try:
                    if not os.path.exists(filepath):
                        return {"status": "failed", "error": "Code file not found"}

                    # 简化的测试检查
                    with open(filepath, 'r', encoding='utf-8') as f:
                        code = f.read()

                    has_class = "class" in code
                    has_methods = "def" in code

                    return {
                        "status": "success",
                        "message": "代码结构验证通过",
                        "has_class": has_class,
                        "has_methods": has_methods,
                        "passed": has_class and has_methods
                    }
                except Exception as e:
                    return {"status": "failed", "error": str(e)}

        # 注册工具
        self.executor.register_tool("generate_code", GenerateCodeTool())
        self.executor.register_tool("run_tests", RunTestsTool())


def run_code_generation_experiment():
    """运行代码生成实验"""
    print("\n" + "="*60)
    print("💻 代码生成实验")
    print("="*60)

    # 创建 Agent
    agent = CodeGenerationAgent()

    # 运行 Agent
    result = agent.run(
        goal="根据需求生成一个数据管理类的代码",
        tools={},
        constraints={"max_time": 3, "max_cost": 30}
    )

    # 清理生成的文件
    generated_files = ["generated_code.py", "test_generated.py"]
    for filepath in generated_files:
        if os.path.exists(filepath):
            os.remove(filepath)

    return result


if __name__ == "__main__":
    result = run_code_generation_experiment()

    print("\n实验结果:")
    print(f"  - 迭代次数: {result['iterations']}")
    print(f"  - 总执行任务数: {result['total_results']}")
    print(f"  - 最终质量分数: {result['final_assessment']['quality_score']}/10")
