#!/usr/bin/env python3
"""
Improved translation script for Claude Cookbooks notebooks.
"""

import json
import re
from pathlib import Path

# Better translation mapping
TRANSLATION_MAP = {
    # Section headers
    "Using a Calculator Tool with Claude": "使用 Claude 的计算器工具",
    "Customer Service Agent": "客户服务代理",
    "Tool Use with Pydantic": "使用 Pydantic 进行工具调用",
    "Parallel Tool Use": "并行工具调用",
    "Tool Choice": "工具选择",

    # Common phrases
    "In this recipe": "在本教程中",
    "we'll demonstrate": "我们将演示",
    "we'll show": "我们将展示",
    "we'll define": "我们将定义",
    "let's install": "让我们安装",
    "let's test": "让我们测试",
    "let's create": "让我们创建",
    "let's try": "让我们尝试",
    "we can use": "我们可以使用",
    "we will use": "我们将使用",
    "you can use": "您可以使用",
    "we'll use": "我们将使用",

    # Step headers
    "Step 1:": "步骤 1：",
    "Step 2:": "步骤 2：",
    "Step 3:": "步骤 3：",
    "Step 4:": "步骤 4：",
    "Step 5:": "步骤 5：",

    # Common terms
    "environment": "环境",
    "Set up the": "设置",
    "Define the": "定义",
    "Create the": "创建",
    "Test the": "测试",
    "Example": "示例",
    "For example": "例如",
    "Note that": "请注意",
    "First": "首先",
    "Next": "接下来",
    "Then": "然后",
    "Finally": "最后",
    "Now": "现在",
    "Also": "也",
    "And": "和",
    "or": "或",
    "with": "使用",
    "from": "从",
    "to": "到",
    "for": "用于",
    "the": "该",
    "a": "一个",
    "an": "一个",
    "is": "是",
    "are": "是",
    "will": "将",
    "can": "可以",
    "this": "这",
    "that": "那",
    "these": "这些",
    "those": "那些",
    "it": "它",
    "its": "它的",
    "we": "我们",
    "you": "您",
    "tool": "工具",
    "tools": "工具",
    "model": "模型",
    "models": "模型",
    "agent": "代理",
    "agents": "代理",
    "output": "输出",
    "input": "输入",
    "response": "响应",
    "request": "请求",
    "call": "调用",
    "calling": "调用",
    "use": "使用",
    "using": "使用",
    "used": "使用",
    "make": "创建",
    "create": "创建",
    "get": "获取",
    "show": "显示",
    "provide": "提供",
    "allow": "允许",
    "perform": "执行",
    "process": "处理",
    "handle": "处理",
    "return": "返回",
    "take": "接受",
    "based on": "基于",
    "user input": "用户输入",
    "order status": "订单状态",
    "look up": "查询",
    "arithmetic operations": "算术运算",
    "mathematical expression": "数学表达式",
    "required libraries": "所需的库",
    "API client": "API 客户端",
    "bad practice": "不好的做法",
    "purpose of demonstration": "演示目的",
    "math problems": "数学问题",
    "order ID": "订单 ID",
    "return request": "退货请求",
    "customer inquiries": "客户咨询",
    "common questions": "常见问题",
    "simple": "简单",
    "basic": "基本",
    "current": "当前",
    "location": "位置",
    "timezone": "时区",
    "weather": "天气",
    "time": "时间",
    "weather for a location": "某个地点的天气",
    "time for a timezone": "某个时区的时间",
    "independently": "独立地",
    "efficient": "高效",
    "sequential": "顺序",
    "parallel": "并行",
    "single response": "单个响应",
    "control": "控制",
    "force": "强制",
    "prevent": "阻止",
    "decide": "决定",
    "automatically": "自动",
    "specific": "特定",
    "default": "默认",
    "comparison": "比较",
}

# Terms to preserve in English
PRESERVE_TERMS = ["API", "Claude", "JSON", "Pydantic", "eval", "anthropic", "Anthropic"]

def smart_translate(text: str) -> str:
    """Smart translation that preserves English terms and handles context."""
    if not text or not text.strip():
        return text

    result = text

    # Step 1: Mark terms to preserve
    placeholders = {}
    for i, term in enumerate(PRESERVE_TERMS):
        placeholder = f"__PRESERVE_{i}__"
        # Use word boundary matching
        pattern = r'\b' + re.escape(term) + r'\b'
        matches = list(re.finditer(pattern, result, flags=re.IGNORECASE))
        # Replace in reverse order to maintain positions
        for match in reversed(matches):
            placeholders[placeholder] = match.group()
            result = result[:match.start()] + placeholder + result[match.end():]

    # Step 2: Apply translations (longest first)
    for en, zh in sorted(TRANSLATION_MAP.items(), key=len, reverse=True):
        # For multi-word phrases
        if ' ' in en:
            result = result.replace(en, zh)
        # For single words, use word boundaries
        else:
            pattern = r'\b' + re.escape(en) + r'\b'
            result = re.sub(pattern, zh, result, flags=re.IGNORECASE)

    # Step 3: Restore preserved terms
    for placeholder, original in placeholders.items():
        result = result.replace(placeholder, original)

    return result

def translate_notebook_file(notebook_path: Path) -> bool:
    """Translate a notebook file."""
    print(f"📖 Processing {notebook_path.name}...")

    with open(notebook_path, 'r', encoding='utf-8') as f:
        notebook = json.load(f)

    translated_count = 0
    for cell in notebook['cells']:
        if cell['cell_type'] == 'markdown':
            source = cell['source']
            if isinstance(source, list):
                # Translate each line, preserving code blocks
                new_source = []
                in_code_block = False

                for line in source:
                    if '```' in line:
                        in_code_block = not in_code_block
                        new_source.append(line)
                    elif in_code_block:
                        new_source.append(line)
                    else:
                        translated = smart_translate(line)
                        new_source.append(translated)

                cell['source'] = new_source
            else:
                cell['source'] = smart_translate(source)
            translated_count += 1

    # Save the translated notebook
    with open(notebook_path, 'w', encoding='utf-8') as f:
        json.dump(notebook, f, ensure_ascii=False, indent=1)

    print(f"✅ Translated {translated_count} markdown cells in {notebook_path.name}")
    return True

def main():
    """Main function."""
    base_dir = Path('/Users/iCloud_GZ/github_GZ/openclaw-memory/claude-cookbooks-zh')

    notebooks = [
        'tool_use/customer_service_agent.ipynb',
        'tool_use/calculator_tool.ipynb',
        'tool_use/tool_use_with_pydantic.ipynb',
        'tool_use/parallel_tools.ipynb',
        'tool_use/tool_choice.ipynb',
    ]

    print("🚀 Starting improved translation...")
    print("=" * 60)

    success = 0
    for nb_path in notebooks:
        full_path = base_dir / nb_path
        if full_path.exists():
            try:
                translate_notebook_file(full_path)
                success += 1
            except Exception as e:
                print(f"❌ Error: {e}")
        else:
            print(f"⚠️  File not found: {nb_path}")

    print("=" * 60)
    print(f"✨ Done! {success}/{len(notebooks)} notebooks translated.")

if __name__ == '__main__':
    main()
