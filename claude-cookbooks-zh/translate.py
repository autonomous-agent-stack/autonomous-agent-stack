#!/usr/bin/env python3
"""
Translate Jupyter notebooks from English to Chinese.
Translates markdown cells using a comprehensive translation dictionary.
"""

import json
import re
from pathlib import Path
from typing import Dict, List

# Comprehensive translation dictionary
TRANSLATIONS: Dict[str, str] = {
    # ===== calculator_tool.ipynb =====
    "Using a Calculator Tool with Claude": "使用 Claude 的计算器工具",
    "In this recipe, we'll demonstrate how to provide Claude with a simple calculator tool that it can use to perform arithmetic operations based on user input. We'll define the calculator tool and show how Claude can interact with it to solve mathematical problems.":
        "在本教程中，我们将演示如何为 Claude 提供一个简单的计算器工具，使其能够根据用户输入执行算术运算。我们将定义计算器工具，并展示 Claude 如何与之交互来解决数学问题。",
    "Step 1: Set up the environment": "步骤 1：设置环境",
    "First, let's install the required libraries and set up the Claude API client.":
        "首先，让我们安装所需的库并设置 Claude API 客户端。",
    "Step 2: Define the calculator tool": "步骤 2：定义计算器工具",
    "We'll define a simple calculator tool that can perform basic arithmetic operations. The tool will take a mathematical expression as input and return the result.":
        "我们将定义一个简单的计算器工具，它可以执行基本的算术运算。该工具将接受数学表达式作为输入并返回结果。",
    "Note that we are calling ```eval``` on the outputted expression. This is bad practice and should not be used generally but we are doing it for the purpose of demonstration.":
        "请注意，我们在输出表达式上调用了 ```eval```。这是不好的做法，通常不应该使用，但为了演示目的，我们在这里这样做。",
    "Step 3: Test the calculator tool": "步骤 3：测试计算器工具",
    "Now let's test our calculator tool by asking Claude to solve some math problems.":
        "现在让我们通过要求 Claude 解决一些数学问题来测试我们的计算器工具。",
    "Let's try another example": "让我们尝试另一个例子",
    "And one more": "再来一个",

    # ===== customer_service_agent.ipynb =====
    "Customer Service Agent": "客户服务代理",
    "This cookbook shows how to use tools to create a simple customer service agent. The agent can look up order status and handle customer inquiries.":
        "本教程展示如何使用工具创建一个简单的客户服务代理。该代理可以查询订单状态并处理客户咨询。",
    "We'll use the Anthropic API to create an agent that can": "我们将使用 Anthropic API 创建一个可以执行以下操作的代理：",
    "Look up order status": "查询订单状态",
    "Process returns": "处理退货",
    "Answer common questions": "回答常见问题",
    "Set up the environment": "设置环境",
    "Install the required packages": "安装所需的软件包",
    "Define the tools": "定义工具",
    "We'll define two tools:": "我们将定义两个工具：",
    "This tool allows the agent to look up the status of an order by order ID.":
        "该工具允许代理通过订单 ID 查询订单状态。",
    "This tool allows the agent to process a return request for an order.":
        "该工具允许代理处理订单的退货请求。",
    "Create the agent": "创建代理",
    "Now let's create our customer service agent using these tools.":
        "现在让我们使用这些工具创建我们的客户服务代理。",
    "Test the agent": "测试代理",
    "Let's test our agent with some customer inquiries.": "让我们通过一些客户咨询来测试我们的代理。",
    "Example 1: Order status inquiry": "示例 1：订单状态查询",
    "Example 2: Return request": "示例 2：退货请求",
    "Example 3: General question": "示例 3：一般性问题",

    # ===== tool_use_with_pydantic.ipynb =====
    "Tool Use with Pydantic": "使用 Pydantic 进行工具调用",
    "This recipe demonstrates how to use Pydantic models to define tools for Claude. Pydantic provides automatic type validation and serialization, making it easier to work with complex tool inputs.":
        "本教程演示如何使用 Pydantic 模型为 Claude 定义工具。Pydantic 提供自动类型验证和序列化，使处理复杂的工具输入变得更加容易。",
    "Define Pydantic models": "定义 Pydantic 模型",
    "We'll define Pydantic models for our tool inputs.": "我们将为工具输入定义 Pydantic 模型。",
    "Create the tool": "创建工具",
    "Convert Pydantic model to tool format": "将 Pydantic 模型转换为工具格式",
    "Use the tool": "使用工具",
    "Now we can use our Pydantic-based tool with Claude.": "现在我们可以在 Claude 中使用基于 Pydantic 的工具。",
    "Benefits of using Pydantic": "使用 Pydantic 的好处",
    "Automatic validation": "自动验证",
    "Type hints": "类型提示",
    "Serialization": "序列化",
    "Documentation": "文档",

    # ===== parallel_tools.ipynb =====
    "Parallel Tool Use": "并行工具调用",
    "This recipe shows how to use multiple tools in parallel. Claude can call multiple tools at once when it makes sense to do so, which can be more efficient than sequential calls.":
        "本教程展示如何并行使用多个工具。在合理的情况下，Claude 可以同时调用多个工具，这比顺序调用更高效。",
    "Define multiple tools": "定义多个工具",
    "We'll define several tools that can be used independently.": "我们将定义几个可以独立使用的工具。",
    "This tool gets the current weather for a location.": "该工具获取某个地点的当前天气。",
    "This tool gets the current time for a timezone.": "该工具获取某个时区的当前时间。",
    "Use tools in parallel": "并行使用工具",
    "Claude will call both tools at the same time": "Claude 将同时调用这两个工具",
    "Notice how Claude calls both tools in a single response": "请注意 Claude 如何在单个响应中调用两个工具",

    # ===== tool_choice.ipynb =====
    "Tool Choice": "工具选择",
    "This recipe demonstrates how to control when and how Claude uses tools. You can force Claude to use a tool, prevent it from using tools, or let it decide automatically.":
        "本教程演示如何控制 Claude 何时以及如何使用工具。您可以强制 Claude 使用工具，阻止它使用工具，或让它自动决定。",
    "Force tool use": "强制使用工具",
    "We can force Claude to always use a specific tool": "我们可以强制 Claude 始终使用特定工具",
    "Auto tool use": "自动使用工具",
    "By default, Claude will decide when to use tools": "默认情况下，Claude 将决定何时使用工具",
    "Prevent tool use": "阻止使用工具",
    "We can also prevent Claude from using tools": "我们也可以阻止 Claude 使用工具",
    "Comparison": "比较",

    # Common phrases
    "recipe": "教程",
    "cookbook": "教程集",
    "Step": "步骤",
    "Example": "示例",
    "Output": "输出",
    "Response": "响应",
    "Request": "请求",
    "Define": "定义",
    "Create": "创建",
    "Use": "使用",
    "Test": "测试",
    "Let's": "让我们",
    "We'll": "我们将",
    "We will": "我们将",
    "You can": "您可以",
    "This": "这",
    "The": "该",
    "A": "一个",
    "An": "一个",
    "For": "用于",
    "With": "使用",
    "From": "从",
    "To": "到",
    "In": "在",
    "On": "在",
    "By": "通过",
    "And": "和",
    "Or": "或",
    "But": "但是",
    "If": "如果",
    "When": "当",
    "Where": "在哪里",
    "How": "如何",
    "What": "什么",
    "Why": "为什么",
    "Which": "哪个",
    "Who": "谁",
    "That": "那个",
    "This": "这个",
    "These": "这些",
    "Those": "那些",
    "It": "它",
    "Its": "它的",
    "They": "它们",
    "Their": "它们的",
    "Is": "是",
    "Are": "是",
    "Was": "是",
    "Were": "是",
    "Be": "是",
    "Been": "是",
    "Being": "是",
    "Have": "有",
    "Has": "有",
    "Had": "有",
    "Do": "做",
    "Does": "做",
    "Did": "做了",
    "Will": "将",
    "Would": "会",
    "Can": "可以",
    "Could": "能够",
    "Should": "应该",
    "May": "可能",
    "Might": "可能",
    "Must": "必须",
    "Shall": "将",
    "Not": "不",
    "No": "没有",
    "Yes": "是",
    "All": "所有",
    "Some": "一些",
    "Many": "许多",
    "Much": "很多",
    "Few": "很少",
    "More": "更多",
    "Most": "大多数",
    "Less": "更少",
    "Least": "最少",
    "Only": "只有",
    "Just": "只是",
    "Also": "也",
    "Too": "太",
    "Very": "非常",
    "Quite": "相当",
    "Rather": "相当",
    "Still": "仍然",
    "Already": "已经",
    "Yet": "还",
    "Now": "现在",
    "Then": "然后",
    "Next": "下一个",
    "Last": "最后",
    "First": "首先",
    "Second": "其次",
    "Third": "第三",
    "Before": "之前",
    "After": "之后",
    "While": "当",
    "During": "在...期间",
    "Since": "自从",
    "Until": "直到",
    "As": "作为",
    "Than": "比",
    "So": "所以",
    "Such": "这样的",
    "Same": "相同",
    "Different": "不同",
    "Other": "其他",
    "Another": "另一个",
    "Each": "每个",
    "Every": "每个",
    "Either": "任一",
    "Neither": "既不",
    "Both": "两者",
    "Between": "之间",
    "Among": "之中",
    "Through": "通过",
    "Over": "在...上方",
    "Under": "在...下方",
    "Above": "在...上方",
    "Below": "在...下方",
    "Up": "向上",
    "Down": "向下",
    "Out": "向外",
    "Off": "关闭",
    "Into": "进入",
    "Onto": "到...上",
    "About": "关于",
    "Against": "反对",
    "Across": "穿过",
    "Along": "沿着",
    "Around": "周围",
    "Behind": "在...后面",
    "Beyond": "超出",
    "From": "从",
    "Near": "靠近",
    "Of": "的",
    "With": "与",
    "Without": "没有",
    "Within": "在...内",
}

# Terms to keep in English
KEEP_ENGLISH = {"API", "Claude", "JSON", "URL", "HTTP", "XML", "HTML", "Pydantic", "eval"}

def translate_line(line: str) -> str:
    """Translate a single line from English to Chinese."""
    if not line or not line.strip():
        return line

    result = line

    # First, preserve terms that should stay in English
    for term in KEEP_ENGLISH:
        # Create a placeholder
        placeholder = f"__KEEP_{term}__"
        pattern = r'\b' + re.escape(term) + r'\b'
        result = re.sub(pattern, placeholder, result, flags=re.IGNORECASE)

    # Apply translations (longer phrases first to avoid partial replacements)
    for en, zh in sorted(TRANSLATIONS.items(), key=lambda x: len(x[0]), reverse=True):
        # Simple word replacement for single words
        if len(en.split()) == 1 and en.islower():
            # Use word boundaries
            pattern = r'\b' + re.escape(en) + r'\b'
            result = re.sub(pattern, zh, result, flags=re.IGNORECASE)
        else:
            # For phrases, do direct replacement (case-sensitive)
            result = result.replace(en, zh)

    # Restore preserved English terms
    for term in KEEP_ENGLISH:
        placeholder = f"__KEEP_{term}__"
        result = result.replace(placeholder, term)

    return result

def translate_markdown_cell(cell: dict) -> dict:
    """Translate a markdown cell while preserving code blocks."""
    if cell['cell_type'] != 'markdown':
        return cell

    source = cell['source']
    if isinstance(source, str):
        source = [source]

    result = []
    in_code_block = False

    for line in source:
        # Check for code block markers
        if '```' in line:
            in_code_block = not in_code_block
            result.append(line)
            continue

        # If in code block, preserve as-is
        if in_code_block:
            result.append(line)
            continue

        # Translate regular text
        translated = translate_line(line)
        result.append(translated)

    cell['source'] = result
    return cell

def translate_notebook(notebook_path: Path) -> bool:
    """Translate a single notebook."""
    print(f"📖 Translating {notebook_path.name}...")

    with open(notebook_path, 'r', encoding='utf-8') as f:
        notebook = json.load(f)

    # Translate all cells
    translated_cells = []
    for cell in notebook['cells']:
        if cell['cell_type'] == 'markdown':
            cell = translate_markdown_cell(cell)
        translated_cells.append(cell)

    notebook['cells'] = translated_cells

    # Save translated notebook
    with open(notebook_path, 'w', encoding='utf-8') as f:
        json.dump(notebook, f, ensure_ascii=False, indent=1)

    print(f"✅ Completed {notebook_path.name}")
    return True

def main():
    """Main translation function."""
    base_dir = Path('/Users/iCloud_GZ/github_GZ/openclaw-memory/claude-cookbooks-zh')

    notebooks = [
        'tool_use/customer_service_agent.ipynb',
        'tool_use/calculator_tool.ipynb',
        'tool_use/tool_use_with_pydantic.ipynb',
        'tool_use/parallel_tools.ipynb',
        'tool_use/tool_choice.ipynb',
    ]

    print(f"🚀 Starting translation of {len(notebooks)} notebooks...")
    print("=" * 60)

    success_count = 0
    for notebook_path in notebooks:
        full_path = base_dir / notebook_path
        if full_path.exists():
            try:
                if translate_notebook(full_path):
                    success_count += 1
            except Exception as e:
                print(f"❌ Error translating {notebook_path}: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"⚠️  File not found: {notebook_path}")

    print("=" * 60)
    print(f"✨ Translation complete! {success_count}/{len(notebooks)} notebooks translated.")

if __name__ == '__main__':
    main()
