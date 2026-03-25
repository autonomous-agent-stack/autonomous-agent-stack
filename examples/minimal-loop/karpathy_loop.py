"""
最小闭环示例：展示完整的 Karpathy 循环

这个示例演示如何使用 Autonomous Agent Stack 实现一个最小化的
"改一个东西 → 打分 → 保留/回滚" 循环。
"""

import requests
import json
import time
from pathlib import Path


class MinimalKarpathyLoop:
    """最小化 Karpathy 循环实现"""

    def __init__(self, api_base_url: str = "http://localhost:8000"):
        self.api_base_url = api_base_url
        self.history = []

    def create_variant(self, source_file: str, mutation: dict) -> str:
        """生成变体（简化版）"""
        # 在真实场景中，这里会调用 Generator API
        # 现在我们直接修改变量值
        with open(source_file, 'r') as f:
            content = f.read()

        # 应用变异
        for key, value in mutation.items():
            # 简单替换（实际应使用 AST）
            content = content.replace(f"{key} = ", f"{key} = {value} # mutated\n# ")

        # 保存变体
        variant_file = source_file.replace(".py", "_variant.py")
        with open(variant_file, 'w') as f:
            f.write(content)

        return variant_file

    def evaluate(self, config_path: str, evaluator_command: dict = None) -> dict:
        """评估变体"""
        payload = {
            "task_name": f"karpathy_eval_{int(time.time())}",
            "config_path": config_path
        }

        if evaluator_command:
            payload["evaluator_command"] = evaluator_command

        # 创建评估任务
        response = requests.post(
            f"{self.api_base_url}/api/v1/evaluations",
            json=payload
        )

        task_id = response.json()["task_id"]

        # 等待评估完成
        while True:
            result = requests.get(
                f"{self.api_base_url}/api/v1/evaluations/{task_id}"
            )
            status = result.json()["status"]

            if status in ["completed", "failed", "interrupted"]:
                return result.json()

            time.sleep(1)

    def should_keep(self, current_score: float, best_score: float, direction: str = "maximize") -> bool:
        """判断是否保留变体"""
        if direction == "maximize":
            return current_score > best_score
        else:
            return current_score < best_score

    def run_loop(
        self,
        source_file: str,
        config_path: str,
        mutations: list,
        max_iterations: int = 10,
        direction: str = "maximize"
    ):
        """运行 Karpathy 循环"""
        best_score = float('-inf') if direction == "maximize" else float('inf')
        best_file = source_file

        print(f"🚀 开始 Karpathy 循环（最大 {max_iterations} 轮）")
        print(f"目标文件: {source_file}")
        print(f"优化方向: {direction}")
        print("-" * 50)

        for i in range(max_iterations):
            print(f"\n📍 第 {i+1}/{max_iterations} 轮")

            # 1. 生成变体
            mutation = mutations[i % len(mutations)]
            variant_file = self.create_variant(source_file, mutation)
            print(f"✅ 变体已生成: {variant_file}")

            # 2. 评估变体
            result = self.evaluate(
                config_path,
                evaluator_command={
                    "command": ["python", variant_file],
                    "timeout_seconds": 60
                }
            )

            if result["status"] == "completed":
                score = result["result"]["score"]
                print(f"📊 评分: {score:.2f}")

                # 3. 决定是否保留
                if self.should_keep(score, best_score, direction):
                    best_score = score
                    best_file = variant_file
                    print(f"✅ 保留！新最佳分数: {best_score:.2f}")
                else:
                    print(f"❌ 回滚。保持最佳分数: {best_score:.2f}")

                # 记录历史
                self.history.append({
                    "iteration": i + 1,
                    "mutation": mutation,
                    "score": score,
                    "kept": self.should_keep(score, best_score, direction)
                })
            else:
                print(f"❌ 评估失败: {result.get('error', 'Unknown error')}")

        print("\n" + "=" * 50)
        print(f"🎉 循环完成！")
        print(f"最佳分数: {best_score:.2f}")
        print(f"最佳文件: {best_file}")
        print(f"总迭代: {len(self.history)}")

        return {
            "best_score": best_score,
            "best_file": best_file,
            "history": self.history
        }


def main():
    """主函数：演示最小闭环"""

    # 1. 准备配置
    config_path = "task.json"
    source_file = "model.py"

    # 2. 定义变异策略（超参数搜索）
    mutations = [
        {"learning_rate": 0.001},
        {"learning_rate": 0.01},
        {"learning_rate": 0.1},
        {"batch_size": 32},
        {"batch_size": 64},
        {"batch_size": 128},
    ]

    # 3. 初始化循环
    loop = MinimalKarpathyLoop(api_base_url="http://localhost:8000")

    # 4. 运行循环
    result = loop.run_loop(
        source_file=source_file,
        config_path=config_path,
        mutations=mutations,
        max_iterations=10,
        direction="maximize"
    )

    # 5. 保存结果
    with open("karpathy_result.json", "w") as f:
        json.dump(result, f, indent=2)

    print("\n📁 结果已保存到 karpathy_result.json")


if __name__ == "__main__":
    # 检查 API 是否可用
    try:
        response = requests.get("http://localhost:8000/docs")
        if response.status_code == 200:
            print("✅ API 服务可用")
            main()
        else:
            print("❌ API 服务异常")
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到 API 服务")
        print("请先启动 API 服务:")
        print("  uvicorn src.autoresearch.api.main:app --reload --port 8000")
