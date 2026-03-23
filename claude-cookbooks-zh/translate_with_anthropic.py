#!/usr/bin/env python3
"""
使用 Anthropic Claude API 翻译 Claude Cookbooks notebooks
"""
import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False
    print("错误: 需要安装 anthropic 库")
    print("运行: pip install anthropic")
    sys.exit(1)

# 翻译提示词
TRANSLATION_PROMPT = """你是一个专业的技术文档翻译。请将以下 Markdown 内容翻译成中文。

翻译规则：
1. 保持 Markdown 格式不变
2. 代码块保持不变
3. 链接保持不变（只翻译链接文本）
4. 以下术语保持英文不翻译：
   - RAG, Prompt, Claude, API, Python, LLM, LLMs
   - JSON, SDK, Git, GitHub, HTTP, HTTPS, URL, SQL
   - DataFrame, NumPy, Pandas, Matplotlib, scikit-learn
   - Jupyter, Notebook, Anaconda, pip, Docker
5. 术语翻译对照：
   - Classification → 分类
   - Summarization → 摘要
   - Retrieval Augmented Generation → 检索增强生成
   - chain-of-thought → 思维链
   - few-shot → 少样本
   - zero-shot → 零样本
   - embeddings → 嵌入
   - vector database → 向量数据库

请翻译以下内容：

{text}

只返回翻译后的内容，不要添加任何解释。
"""

def split_text_by_lines(text: str, max_lines: int = 50) -> List[str]:
    """将长文本按行分割成较小的块"""
    lines = text.split('\n')
    chunks = []
    current_chunk = []
    current_length = 0

    for line in lines:
        current_chunk.append(line)
        current_length += len(line)

        # 如果块太大或达到最大行数，就分割
        if len(current_chunk) >= max_lines and current_length > 2000:
            chunks.append('\n'.join(current_chunk))
            current_chunk = []
            current_length = 0

    if current_chunk:
        chunks.append('\n'.join(current_chunk))

    return chunks

def translate_with_claude(text: str, client: anthropic.Anthropic, model: str = "claude-3-haiku-20240307") -> str:
    """使用 Claude 翻译文本"""
    # 检查是否已经包含中文
    has_chinese = any('\u4e00' <= char <= '\u9fff' for char in text)
    if has_chinese:
        return text  # 已经是中文，跳过

    # 检查是否是纯代码或很短
    if not text.strip() or len(text.strip()) < 10:
        return text

    try:
        # 如果文本太长，分割后翻译
        if len(text) > 8000:
            chunks = split_text_by_lines(text, max_lines=30)
            translated_chunks = []

            for chunk in chunks:
                if not chunk.strip():
                    translated_chunks.append(chunk)
                    continue

                message = client.messages.create(
                    model=model,
                    max_tokens=4000,
                    messages=[{
                        "role": "user",
                        "content": TRANSLATION_PROMPT.format(text=chunk)
                    }]
                )

                translated_text = message.content[0].text
                translated_chunks.append(translated_text)

            return '\n'.join(translated_chunks)
        else:
            message = client.messages.create(
                model=model,
                max_tokens=4000,
                messages=[{
                    "role": "user",
                    "content": TRANSLATION_PROMPT.format(text=text)
                }]
            )

            return message.content[0].text

    except Exception as e:
        print(f"翻译出错: {e}")
        return text  # 返回原文

def process_cell(cell: Dict[str, Any], client: anthropic.Anthropic, model: str) -> bool:
    """处理单个单元格"""
    if cell.get('cell_type') != 'markdown':
        return False

    source = cell.get('source', [])
    if isinstance(source, list):
        original_text = ''.join(source)
    else:
        original_text = source

    if not original_text.strip():
        return False

    # 翻译文本
    print(f"  - 翻译文本 (长度: {len(original_text)} 字符)...")
    translated_text = translate_with_claude(original_text, client, model)

    # 更新单元格
    if isinstance(source, list):
        # 将翻译后的文本按行分割
        cell['source'] = translated_text.split('\n')
        # 确保每行都有换行符（Jupyter 格式）
        cell['source'] = [line + '\n' for line in cell['source']]
        # 最后一行不需要换行符
        if cell['source'] and cell['source'][-1].endswith('\n'):
            cell['source'][-1] = cell['source'][-1][:-1]
    else:
        cell['source'] = translated_text

    return True

def process_notebook(notebook_path: Path, client: anthropic.Anthropic, model: str) -> bool:
    """处理单个 notebook 文件"""
    print(f"\n{'='*60}")
    print(f"处理文件: {notebook_path.name}")
    print(f"{'='*60}")

    # 读取 notebook
    with open(notebook_path, 'r', encoding='utf-8') as f:
        notebook = json.load(f)

    modified = False
    markdown_count = 0
    translated_count = 0

    # 处理每个单元格
    for i, cell in enumerate(notebook.get('cells', [])):
        if cell.get('cell_type') == 'markdown':
            markdown_count += 1
            print(f"\n单元格 {i+1}/{markdown_count}:", end=" ")

            source = cell.get('source', [])
            if isinstance(source, list):
                original_text = ''.join(source)
            else:
                original_text = source

            # 检查是否已经翻译
            has_chinese = any('\u4e00' <= char <= '\u9fff' for char in original_text)

            if not has_chinese and original_text.strip():
                if process_cell(cell, client, model):
                    translated_count += 1
                    modified = True
                    print("✓ 已翻译")
                else:
                    print("✗ 翻译失败")
            else:
                print("○ 跳过（已是中文或为空）")

    print(f"\n统计: {markdown_count} 个 markdown 单元格, {translated_count} 个已翻译")

    if modified:
        # 保存修改后的 notebook
        with open(notebook_path, 'w', encoding='utf-8') as f:
            json.dump(notebook, f, ensure_ascii=False, indent=1)
        print(f"✓ 文件已保存")

    return modified

def main():
    """主函数"""
    # 检查 API key
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("错误: 需要设置 ANTHROPIC_API_KEY 环境变量")
        print("运行: export ANTHROPIC_API_KEY='your-api-key'")
        sys.exit(1)

    # 初始化客户端
    client = anthropic.Anthropic(api_key=api_key)
    model = "claude-3-5-haiku-20241022"  # 使用 Haiku 以节省成本

    print("="*60)
    print("Claude Cookbooks 翻译工具")
    print(f"使用模型: {model}")
    print("="*60)

    # 定义要翻译的文件列表
    notebooks = [
        "capabilities/classification/guide.ipynb",
        "capabilities/summarization/guide.ipynb",
        "capabilities/retrieval_augmented_generation/guide.ipynb",
        "capabilities/text_to_sql/guide.ipynb",
    ]

    base_dir = Path.cwd()

    # 处理每个 notebook
    results = {}
    for notebook_path in notebooks:
        full_path = base_dir / notebook_path
        if full_path.exists():
            try:
                modified = process_notebook(full_path, client, model)
                results[notebook_path] = "✓ 已翻译" if modified else "○ 无需翻译"
            except Exception as e:
                print(f"\n✗ 处理失败: {e}")
                import traceback
                traceback.print_exc()
                results[notebook_path] = f"✗ 失败: {e}"
        else:
            print(f"\n✗ 文件不存在: {full_path}")
            results[notebook_path] = "✗ 文件不存在"

    # 打印汇总
    print("\n" + "="*60)
    print("翻译汇总:")
    print("="*60)
    for notebook, status in results.items():
        print(f"  {notebook}: {status}")
    print("="*60)

if __name__ == "__main__":
    main()
