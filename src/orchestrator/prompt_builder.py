import re
from typing import List, Dict

class PromptBuilder:
    """Prompt组装器（去除工厂化语气）"""
    
    FACTORY_WORDS = ["工厂", "批量", "流水线", "生产线", "规模化", "工业化"]
    PROFESSIONAL_KEYWORDS = ["专业", "精准", "高端", "定制", "匠心"]
    CORE_SELLING_POINTS = {
        "玛露6g罐装遮瑕膏": ["持妆", "免调色", "高遮瑕", "12小时", "一抹成型"]
    }
    
    @classmethod
    def build(cls, task: str) -> str:
        """构建专业Prompt"""
        # 基础Prompt
        prompt = f"任务: {task}\n\n要求:\n"
        
        # 添加专业要求
        prompt += "1. 使用专业、精准的语气\n"
        prompt += "2. 避免工厂化、流水线式的表述\n"
        prompt += "3. 突出产品的核心卖点\n\n"
        
        # 添加核心卖点
        for product, points in cls.CORE_SELLING_POINTS.items():
            if product in task:
                prompt += f"核心卖点: {', '.join(points)}\n"
        
        return prompt
    
    @classmethod
    def validate_tone(cls, text: str) -> Dict[str, float]:
        """验证文案语气"""
        # 检查工厂化词语
        factory_count = sum(1 for word in cls.FACTORY_WORDS if word in text)
        
        # 检查专业关键词
        professional_count = sum(1 for word in cls.PROFESSIONAL_KEYWORDS if word in text)
        
        # 检查核心卖点
        selling_points = 0
        for product, points in cls.CORE_SELLING_POINTS.items():
            selling_points += sum(1 for point in points if point in text)
        
        return {
            "factory_score": max(0, 1 - factory_count * 0.5),  # 越低越好
            "professional_score": min(1, professional_count * 0.3),  # 越高越好
            "selling_points_coverage": selling_points / 5,  # 覆盖率
            "overall_score": (1 - factory_count * 0.5) + professional_count * 0.3 + selling_points * 0.1
        }

# 测试
if __name__ == "__main__":
    builder = PromptBuilder()
    
    # 构建Prompt
    prompt = builder.build("推销玛露6g罐装遮瑕膏")
    print("生成的Prompt:")
    print(prompt)
    
    # 验证语气
    test_text = """
    玛露6g罐装遮瑕膏，专业级遮瑕效果，持妆12小时不脱妆。
    免调色设计，一抹成型，精准遮盖瑕疵。
    """
    score = builder.validate_tone(test_text)
    print("\n语气评分:")
    print(f"  工厂化程度: {score['factory_score']:.2f}")
    print(f"  专业度: {score['professional_score']:.2f}")
    print(f"  卖点覆盖率: {score['selling_points_coverage']:.2f}")
    print(f"  综合评分: {score['overall_score']:.2f}")
    
    assert score["factory_score"] >= 0.8
    assert score["overall_score"] >= 1.0
    print("\n✅ 玛露业务验收测试通过")
