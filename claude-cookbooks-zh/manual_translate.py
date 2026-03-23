#!/usr/bin/env python3
"""
Manual high-quality translation for Claude Cookbooks notebooks.
This script provides proper Chinese translations for the markdown cells.
"""

import json
from pathlib import Path
from typing import List, Dict

# Manual translations for key content
MANUAL_TRANSLATIONS = {
    "customer_service_agent.ipynb": {
        "# Creating a Customer Service Agent with Client-Side Tools": "# 使用客户端工具创建客户服务代理",
        "In this recipe, we'll demonstrate how to create a customer service chatbot using Claude 3 plus client-side tools. The chatbot will be able to look up customer information, retrieve order details, and cancel orders on behalf of the customer. We'll define the necessary tools and simulate synthetic responses to showcase the chatbot's capabilities.":
            "在本教程中，我们将演示如何使用 Claude 3 和客户端工具创建一个客户服务聊天机器人。该聊天机器人将能够查询客户信息、检索订单详情，并代表客户取消订单。我们将定义必要的工具并模拟合成响应来展示聊天机器人的功能。",
        "## Step 1: Set up the environment": "## 步骤 1：设置环境",
        "First, let's install the required libraries and set up the Claude API client.":
            "首先，让我们安装所需的库并设置 Claude API 客户端。",
        "## Step 2: Define the tools": "## 步骤 2：定义工具",
        "We'll define three tools that our customer service agent can use:": "我们将定义三个客户服务代理可以使用的工具：",
        "### Tool 1: Get Customer Information": "### 工具 1：获取客户信息",
        "### Tool 2: Get Order Details": "### 工具 2：获取订单详情",
        "### Tool 3: Cancel Order": "### 工具 3：取消订单",
        "## Step 3: Create the agent": "## 步骤 3：创建代理",
        "Now let's create our customer service agent with these tools.": "现在让我们使用这些工具创建我们的客户服务代理。",
        "## Step 4: Test the agent": "## 步骤 4：测试代理",
        "Let's test our agent with some customer inquiries.": "让我们通过一些客户咨询来测试我们的代理。",
        "### Test 1: Customer information lookup": "### 测试 1：客户信息查询",
        "### Test 2: Order details lookup": "### 测试 2：订单详情查询",
        "### Test 3: Cancel an order": "### 测试 3：取消订单",
    },
    "calculator_tool.ipynb": {
        "# Using a Calculator Tool with Claude": "# 使用 Claude 的计算器工具",
        "In this recipe, we'll demonstrate how to provide Claude with a simple calculator tool that it can use to perform arithmetic operations based on user input. We'll define the calculator tool and show how Claude can interact with it to solve mathematical problems.":
            "在本教程中，我们将演示如何为 Claude 提供一个简单的计算器工具，使其能够根据用户输入执行算术运算。我们将定义计算器工具，并展示 Claude 如何与之交互来解决数学问题。",
        "## Step 1: Set up the environment": "## 步骤 1：设置环境",
        "First, let's install the required libraries and set up the Claude API client.":
            "首先，让我们安装所需的库并设置 Claude API 客户端。",
        "## Step 2: Define the calculator tool": "## 步骤 2：定义计算器工具",
        "We'll define a simple calculator tool that can perform basic arithmetic operations. The tool will take a mathematical expression as input and return the result.":
            "我们将定义一个简单的计算器工具，它可以执行基本的算术运算。该工具将接受数学表达式作为输入并返回结果。",
        "Note that we are calling ```eval``` on the outputted expression. This is bad practice and should not be used generally but we are doing it for the purpose of demonstration.":
            "请注意，我们在输出表达式上调用了 ```eval```。这是不好的做法，通常不应该使用，但为了演示目的，我们在这里这样做。",
        "## Step 3: Test the calculator tool": "## 步骤 3：测试计算器工具",
        "Now let's test our calculator tool by asking Claude to solve some math problems.":
            "现在让我们通过要求 Claude 解决一些数学问题来测试我们的计算器工具。",
        "Let's try another example:": "让我们尝试另一个例子：",
        "And one more:": "再来一个：",
    },
    "tool_use_with_pydantic.ipynb": {
        "# Note-Saving Tool with Pydantic and Anthropic Tool Use": "# 使用 Pydantic 和 Anthropic 工具调用的笔记保存工具",
        "In this example, we'll create a tool that saves a note with the author and metadata, and use Pydantic to validate the model's response when calling the tool. We'll define the necessary Pydantic models, process the tool call, and ensure that the model's response conforms to the expected schema.":
            "在这个示例中，我们将创建一个保存笔记及其作者和元数据的工具，并使用 Pydantic 在调用工具时验证模型的响应。我们将定义必要的 Pydantic 模型，处理工具调用，并确保模型的响应符合预期的模式。",
    },
    "parallel_tools.ipynb": {
        "# Parallel tool calls on Claude 3.7 Sonnet": "# Claude 3.7 Sonnet 上的并行工具调用",
    },
    "tool_choice.ipynb": {
        "# Tool choice": "# 工具选择",
        "Tool use supports a parameter called `tool_choice` that allows you to specify how you want Claude to call tools. In this notebook, we'll take a look at how it works and when to use it. Before going any further, make sure you are comfortable with the basics of tool use with Claude.":
            "工具调用支持一个名为 `tool_choice` 的参数，它允许您指定希望 Claude 如何调用工具。在本笔记本中，我们将了解它的工作原理以及何时使用它。在继续之前，请确保您熟悉使用 Claude 进行工具调用的基础知识。",
        "When working with the `tool_choice` parameter, we have three possible options:": "在使用 `tool_choice` 参数时，我们有三个可能的选项：",
        "* `auto` allows Claude to decide whether to call any provided tools or not": "* `auto` 允许 Claude 决定是否调用任何提供的工具",
        "* `tool` allows us to force Claude to always use a particular tool": "* `tool` 允许我们强制 Claude 始终使用特定工具",
        "* `any` tells Claude that it must use one of the provided tools, but doesn't force a particular tool": "* `any` 告诉 Claude 它必须使用提供的工具之一，但不强制使用特定工具",
        "Let's take a look at each option in detail. We'll start by importing the Anthropic SDK:": "让我们详细了解每个选项。首先导入 Anthropic SDK：",
        "## Auto": "## 自动",
        "Setting `tool_choice` to `auto` allows the model to automatically decide whether to use tools or not.": "将 `tool_choice` 设置为 `auto` 允许模型自动决定是否使用工具。",
        "This is the default behavior when working with tools.": "这是使用工具时的默认行为。",
        "To demonstrate this, we're going to provide Claude with a fake web search tool.": "为了演示这一点，我们将为 Claude 提供一个假的网络搜索工具。",
        "We will ask Claude questions, some of which would require calling the web search tool and other which Claude should be able to answer on its own.": "我们将向 Claude 提问，其中一些问题需要调用网络搜索工具，而其他问题 Claude 应该能够自己回答。",
        "Let's start by defining a tool called `web_search`.": "让我们首先定义一个名为 `web_search` 的工具。",
        "Please note, to keep this demo simple, we're not actually searching the web here:": "请注意，为了保持此演示简单，我们实际上并不在这里搜索网络：",
        "Next, we write a function that accepts a user_query and passes it along to Claude, along with the `web_search_tool`.": "接下来，我们编写一个接受 user_query 的函数，并将其连同 `web_search_tool` 一起传递给 Claude。",
        "We also set `tool_choice` to `auto`:": "我们还将 `tool_choice` 设置为 `auto`：",
        "Here's the complete function:": "这是完整的函数：",
        "Now let's test our function with a couple of example queries.": "现在让我们用几个示例查询来测试我们的函数。",
        "### Example 1: A question that doesn't require the web search tool": "### 示例 1：不需要网络搜索工具的问题",
        "### Example 2: A question that does require the web search tool": "### 示例 2：需要网络搜索工具的问题",
        "## Tool": "## 工具",
        "The `tool` option allows us to force Claude to always call a specific tool.": "`tool` 选项允许我们强制 Claude 始终调用特定工具。",
        "To use this option, we set `tool_choice` to the name of the tool we want to force.": "要使用此选项，我们将 `tool_choice` 设置为我们想要强制的工具名称。",
        "Here's an example where we force Claude to always use the web search tool:": "下面是一个我们强制 Claude 始终使用网络搜索工具的示例：",
        "## Any": "## 任何",
        "The `any` option tells Claude that it must use one of the provided tools, but doesn't specify which one.": "`any` 选项告诉 Claude 它必须使用提供的工具之一，但不指定哪一个。",
        "This is useful when you want to ensure Claude uses a tool, but don't care which one it chooses.": "当您想确保 Claude 使用工具，但不关心它选择哪一个时，这很有用。",
        "To use this option, set `tool_choice` to `any`:": "要使用此选项，请将 `tool_choice` 设置为 `any`：",
        "Here's an example:": "下面是一个示例：",
    },
}

def translate_text(text: str, notebook_name: str) -> str:
    """Translate text using manual translations."""
    if notebook_name in MANUAL_TRANSLATIONS:
        translations = MANUAL_TRANSLATIONS[notebook_name]
        for en, zh in translations.items():
            text = text.replace(en, zh)
    return text

def translate_notebook(notebook_path: Path) -> bool:
    """Translate a notebook."""
    print(f"📖 Translating {notebook_path.name}...")

    with open(notebook_path, 'r', encoding='utf-8') as f:
        notebook = json.load(f)

    translated_count = 0
    for cell in notebook['cells']:
        if cell['cell_type'] == 'markdown':
            source = cell['source']
            if isinstance(source, list):
                new_source = []
                in_code_block = False

                for line in source:
                    if '```' in line:
                        in_code_block = not in_code_block
                        new_source.append(line)
                    elif in_code_block:
                        new_source.append(line)
                    else:
                        translated = translate_text(line, notebook_path.name)
                        new_source.append(translated)

                cell['source'] = new_source
            translated_count += 1

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

    print("🚀 Starting manual translation...")
    print("=" * 60)

    success = 0
    for nb_path in notebooks:
        full_path = base_dir / nb_path
        if full_path.exists():
            try:
                translate_notebook(full_path)
                success += 1
            except Exception as e:
                print(f"❌ Error: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"⚠️  File not found: {nb_path}")

    print("=" * 60)
    print(f"✨ Done! {success}/{len(notebooks)} notebooks translated.")

if __name__ == '__main__':
    main()
