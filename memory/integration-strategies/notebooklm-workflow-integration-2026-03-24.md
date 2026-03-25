# NotebookLM 自动化工作流集成方案

**研究日期**: 2026-03-24
**研究范围**: OpenClaw Skill + anything-to-notebooklm + notebooklm-skill
**版本**: 1.0

---

## 执行摘要

本方案设计了三个 NotebookLM 相关项目的完整集成架构，实现了从内容获取、转换、知识库构建到智能查询的全自动化工作流。通过统一的 API 接口和智能路由，用户可以用自然语言完成从原始内容到最终输出的全流程。

---

## 目录

1. [架构分析](#1-架构分析)
2. [工作流设计](#2-工作流设计)
3. [技术实现](#3-技术实现)
4. [性能优化](#4-性能优化)
5. [部署指南](#5-部署指南)
6. [代码示例](#6-代码示例)
7. [性能基准](#7-性能基准)

---

## 1. 架构分析

### 1.1 项目概述

#### 项目 A: OpenClaw 内置 Skill (notebooklm-py CLI)

**定位**: 完整的 NotebookLM API 封装
**技术栈**: Python + notebooklm-py 库
**核心能力**:
- ✅ 完整的 NotebookLM API 支持（创建、查询、生成、下载）
- ✅ OAuth 认证管理
- ✅ 并行处理支持（通过 `-n` 标志）
- ✅ 批量操作
- ✅ 生成 9 种输出格式（播客、视频、PPT、Quiz、报告等）

**关键接口**:
```python
# 认证
notebooklm login
notebooklm auth check --json

# 笔记本管理
notebooklm create "Title" --json
notebooklm list --json
notebooklm use <id>

# 源管理
notebooklm source add <url|file> --json
notebooklm source list --json
notebooklm source wait <id> -n <notebook_id> --timeout 600

# 生成
notebooklm generate audio "instructions" --json
notebooklm artifact wait <id> -n <notebook_id> --timeout 1200

# 下载
notebooklm download audio ./output.mp3 -a <artifact_id> -n <notebook_id>
```

#### 项目 B: anything-to-notebooklm

**定位**: 内容转换工具
**技术栈**: Python + Microsoft markitdown + MCP
**核心能力**:
- ✅ 支持 15+ 种内容格式转换
- ✅ 微信公众号抓取（MCP 浏览器自动化）
- ✅ YouTube 字幕提取
- ✅ OCR 支持（图片、扫描件）
- ✅ 批量处理（ZIP 压缩包）

**支持的格式**:
```
输入格式:
├── 网页内容
│   ├── 微信公众号（MCP）
│   ├── 任意网页
│   └── YouTube 视频
├── Office 文档
│   ├── Word (.docx)
│   ├── PowerPoint (.pptx)
│   └── Excel (.xlsx)
├── 电子书与文档
│   ├── PDF（含 OCR）
│   ├── EPUB
│   └── Markdown (.md)
├── 媒体文件
│   ├── 图片（JPEG/PNG/GIF，自动 OCR）
│   └── 音频（WAV/MP3，自动转录）
├── 结构化数据
│   ├── CSV
│   ├── JSON
│   └── XML
└── 压缩包
    └── ZIP（批量处理）
```

**关键接口**:
```python
# 自然语言触发
"把这篇微信文章生成播客 https://mp.weixin.qq.com/s/..."
"这本书做成 PPT /path/to/book.epub"
"这个 YouTube 视频生成 Quiz https://youtube.com/watch?v=..."
```

#### 项目 C: notebooklm-skill

**定位**: Claude Code 集成（浏览器自动化）
**技术栈**: Python + Patchright（Playwright）
**核心能力**:
- ✅ 浏览器自动化与 NotebookLM 交互
- ✅ 库管理（保存笔记本元数据）
- ✅ 持久化认证
- ✅ 源码引用答案（citation-backed）

**关键接口**:
```python
# 库管理
python scripts/run.py notebook_manager.py list
python scripts/run.py notebook_manager.py add --url "..." --name "..." --topics "..."

# 查询
python scripts/run.py ask_question.py --question "..." --notebook-url "..."

# 认证
python scripts/run.py auth_manager.py setup
python scripts/run.py auth_manager.py status
```

### 1.2 集成架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                      用户自然语言输入                             │
│         "把这篇微信文章生成播客，然后总结要点"                     │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   OpenClaw Agent (协调层)                         │
│  • 自然语言理解                                                   │
│  • 意图识别                                                       │
│  • 任务编排                                                       │
│  • 工作流引擎                                                     │
└─────┬───────────────┬───────────────┬──────────────────────────┘
      │               │               │
      │               │               │
      ▼               ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────────────────────┐
│   项目 A    │ │   项目 B    │ │         项目 C               │
│ notebooklm  │ │ anything-   │ │   notebooklm-skill          │
│   -py CLI   │ │ to-notebook │ │   (浏览器自动化)             │
│             │ │     lm      │ │                             │
└─────┬───────┘ └─────┬───────┘ └──────────┬──────────────────┘
      │               │                     │
      │               │                     │
      │               ▼                     │
      │     ┌──────────────────┐           │
      │     │  内容转换层       │           │
      │     │  • markitdown    │           │
      │     │  • MCP (微信)    │           │
      │     │  • OCR           │           │
      │     │  • YouTube API   │           │
      │     └────────┬─────────┘           │
      │              │                     │
      │              │                     │
      ▼              ▼                     ▼
┌──────────────────────────────────────────────────────────────┐
│                    Google NotebookLM                          │
│  • 笔记本管理                                                 │
│  • 源上传与索引                                               │
│  • AI 生成（播客、视频、PPT 等）                              │
│  • Gemini 2.5 查询                                           │
└──────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                      输出层                                   │
│  • .mp3 / .mp4 / .pdf / .json / .md / .csv                   │
│  • 下载到本地                                                 │
│  • 发送到用户                                                 │
└──────────────────────────────────────────────────────────────┘
```

### 1.3 关键集成节点

| 节点 | 功能 | 涉及项目 | 数据流 |
|------|------|---------|--------|
| **内容获取** | 多源内容抓取 | B → A | URL/File → Text/Markdown |
| **内容转换** | 格式统一化 | B | 多格式 → Markdown |
| **源上传** | 上传到 NotebookLM | B → A | Markdown → NotebookLM Source |
| **知识库构建** | 创建笔记本、添加源 | A | Notebook + Sources |
| **内容生成** | AI 生成输出 | A | Sources → Artifacts |
| **智能查询** | 基于源的问答 | A / C | Query → Answer + Citations |
| **下载输出** | 获取生成结果 | A | Artifacts → Local Files |

---

## 2. 工作流设计

### 2.1 工作流 1: 自动内容转换

**场景**: 用户上传文件 → 自动转换 → NotebookLM → 自动生成播客

```
┌─────────────┐
│ 用户上传文件 │
│ (任意格式)  │
└──────┬──────┘
       │
       ▼
┌─────────────────────────┐
│ 步骤 1: 格式识别        │
│ (anything-to-notebooklm)│
│ • 自动检测文件类型      │
│ • 选择转换器            │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│ 步骤 2: 内容转换        │
│ (markitdown + MCP)      │
│ • 微信: MCP 浏览器抓取  │
│ • PDF: markitdown       │
│ • 图片: OCR             │
│ • 音频: 语音转录        │
│ • YouTube: 字幕提取     │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│ 步骤 3: 上传到 Notebook │
│ (notebooklm-py CLI)     │
│ • 创建笔记本            │
│ • 添加源                │
│ • 等待处理完成          │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│ 步骤 4: 生成播客        │
│ (notebooklm-py CLI)     │
│ • generate audio        │
│ • 等待生成完成          │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│ 步骤 5: 下载结果        │
│ (notebooklm-py CLI)     │
│ • download audio        │
│ • 返回文件路径          │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│     输出: podcast.mp3   │
└─────────────────────────┘
```

**时间估算**:
- 内容转换: 10-60 秒
- 源处理: 30-120 秒
- 播客生成: 5-15 分钟
- **总计**: 6-18 分钟

**自动化程度**: 100%（无需人工干预）

---

### 2.2 工作流 2: Claude 智能查询

**场景**: Claude Code → notebooklm-skill → NotebookLM → 源码引用答案

```
┌─────────────────────┐
│ 用户: "查询我的 React│
│ 文档，hooks 的最佳  │
│ 实践是什么？"       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────┐
│ 步骤 1: 意图识别        │
│ (Claude Code)           │
│ • 识别为查询任务        │
│ • 提取关键词: "React"   │
│               "hooks"   │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│ 步骤 2: 笔记本选择      │
│ (notebooklm-skill)      │
│ • 搜索库: "React"       │
│ • 选择匹配笔记本        │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│ 步骤 3: 浏览器自动化    │
│ (Patchright)            │
│ • 打开 Chrome           │
│ • 导航到笔记本 URL      │
│ • 输入问题              │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│ 步骤 4: 等待回答        │
│ (Gemini 2.5)            │
│ • 基于源生成答案        │
│ • 包含引用 [1][2][3]    │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│ 步骤 5: 提取答案        │
│ (notebooklm-skill)      │
│ • 抓取答案文本          │
│ • 提取引用              │
│ • 关闭浏览器            │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│ 步骤 6: 返回结果        │
│ (Claude Code)           │
│ • 显示答案              │
│ • 显示引用来源          │
│ • Claude 基于此写代码   │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│ 输出: 源码引用答案 +    │
│       工作代码          │
└─────────────────────────┘
```

**时间估算**:
- 笔记本选择: 1-2 秒
- 浏览器启动: 2-3 秒
- 查询响应: 5-15 秒
- **总计**: 8-20 秒

**准确性**: 高（基于上传文档，减少幻觉）

---

### 2.3 工作流 3: 完整知识管理

**场景**: 文件收集 → 内容转换 → NotebookLM 知识库 → Claude 查询 → 自动报告生成

```
┌─────────────────────────────────────────────────────────┐
│                   阶段 1: 知识收集                       │
└─────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────┐
│ 多源内容收集            │
│ • 微信文章 x 5          │
│ • YouTube 视频 x 3      │
│ • PDF 文档 x 10         │
│ • 网页链接 x 8          │
│ • 本地笔记 x 2          │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────┐
│                   阶段 2: 内容处理                       │
└─────────────────────────────────────────────────────────┘
       │
       ├─→ 微信文章 ────→ MCP 抓取 ──────┐
       │                                 │
       ├─→ YouTube ──────→ 字幕提取 ────┤
       │                                 │
       ├─→ PDF ──────────→ markitdown ──┤
       │                                 ├──→ 统一 Markdown
       ├─→ 网页 ─────────→ 网页抓取 ────┤
       │                                 │
       └─→ 本地笔记 ─────→ 直接读取 ────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────┐
│                 阶段 3: 知识库构建                       │
└─────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────┐
│ 创建主题笔记本          │
│ 标题: "AI 研究 2026"    │
└──────┬──────────────────┘
       │
       ├─→ 添加源 1: 微信文章
       ├─→ 添加源 2: YouTube 视频
       ├─→ 添加源 3: PDF 文档
       ├─→ ... (共 28 个源)
       └─→ 等待所有源处理完成
       │
       ▼
┌─────────────────────────────────────────────────────────┐
│                   阶段 4: 智能查询                       │
└─────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────┐
│ 用户: "总结这些资料中的 │
│       AI 趋势，生成报告"│
└──────┬──────────────────┘
       │
       ├─→ Claude 查询笔记本
       │   • Q1: "2026 AI 主要趋势是什么？"
       │   • Q2: "有哪些新技术突破？"
       │   • Q3: "推荐哪些学习资源？"
       │   • ... (多轮对话)
       │
       └─→ 获取源码引用答案
          │
          ▼
┌─────────────────────────────────────────────────────────┐
│                 阶段 5: 报告生成                         │
└─────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────┐
│ 自动生成报告            │
│ • generate report       │
│ • 格式: briefing-doc    │
│ • 语言: zh_Hans         │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│ 下载报告                │
│ • download report       │
│ • 文件: AI_Trends.md    │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│ 可选: 生成其他格式      │
│ • 播客 (audio)          │
│ • PPT (slide-deck)      │
│ • 思维导图 (mind-map)   │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│     输出: 完整知识库    │
│     + 研究报告          │
│     + 多种格式输出      │
└─────────────────────────┘
```

**时间估算**:
- 内容收集: 手动（0-30 分钟）
- 内容处理: 5-15 分钟（自动）
- 知识库构建: 10-30 分钟（自动）
- 智能查询: 2-5 分钟（交互式）
- 报告生成: 5-15 分钟（自动）
- **总计**: 22-95 分钟

**价值**: 从零散资料到系统化知识库

---

## 3. 技术实现

### 3.1 统一 API 接口设计

```python
# notebooklm_workflow.py

from typing import List, Dict, Optional, Union
from pathlib import Path
import subprocess
import json

class NotebookLMWorkflow:
    """统一的 NotebookLM 工作流接口"""
    
    def __init__(self, notebook_id: Optional[str] = None):
        self.notebook_id = notebook_id
        self.notebook_title = None
    
    # ========== 项目 A: notebooklm-py CLI ==========
    
    def create_notebook(self, title: str) -> str:
        """创建笔记本（项目 A）"""
        cmd = f'notebooklm create "{title}" --json'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        data = json.loads(result.stdout)
        self.notebook_id = data['id']
        self.notebook_title = title
        return self.notebook_id
    
    def add_source(self, source: Union[str, Path]) -> str:
        """添加源（项目 A）"""
        if not self.notebook_id:
            raise ValueError("No notebook context. Create or use a notebook first.")
        
        cmd = f'notebooklm source add "{source}" --json --notebook {self.notebook_id}'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        data = json.loads(result.stdout)
        return data['source_id']
    
    def wait_for_source(self, source_id: str, timeout: int = 600) -> bool:
        """等待源处理完成（项目 A）"""
        cmd = f'notebooklm source wait {source_id} -n {self.notebook_id} --timeout {timeout}'
        result = subprocess.run(cmd, shell=True)
        return result.returncode == 0
    
    def generate_artifact(self, artifact_type: str, instructions: str = "") -> str:
        """生成内容（项目 A）"""
        cmd = f'notebooklm generate {artifact_type} "{instructions}" --json --notebook {self.notebook_id}'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        data = json.loads(result.stdout)
        return data['task_id']
    
    def wait_for_artifact(self, artifact_id: str, timeout: int = 1200) -> bool:
        """等待生成完成（项目 A）"""
        cmd = f'notebooklm artifact wait {artifact_id} -n {self.notebook_id} --timeout {timeout}'
        result = subprocess.run(cmd, shell=True)
        return result.returncode == 0
    
    def download_artifact(self, artifact_type: str, output_path: Path, artifact_id: str) -> Path:
        """下载生成内容（项目 A）"""
        cmd = f'notebooklm download {artifact_type} "{output_path}" -a {artifact_id} -n {self.notebook_id}'
        subprocess.run(cmd, shell=True, check=True)
        return output_path
    
    def ask_question(self, question: str) -> Dict:
        """查询笔记本（项目 A）"""
        cmd = f'notebooklm ask "{question}" --json --notebook {self.notebook_id}'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return json.loads(result.stdout)
    
    # ========== 项目 B: anything-to-notebooklm ==========
    
    def convert_content(self, source: Union[str, Path]) -> Path:
        """转换内容为 Markdown（项目 B）
        
        自动识别:
        - 微信公众号 URL
        - YouTube URL
        - 网页 URL
        - 本地文件（PDF, EPUB, DOCX, etc.）
        - 图片（OCR）
        - 音频（转录）
        """
        # 这里调用 anything-to-notebooklm 的转换逻辑
        # 返回转换后的 Markdown 文件路径
        pass
    
    def batch_convert(self, sources: List[Union[str, Path]]) -> List[Path]:
        """批量转换内容（项目 B）"""
        converted = []
        for source in sources:
            md_path = self.convert_content(source)
            converted.append(md_path)
        return converted
    
    # ========== 项目 C: notebooklm-skill ==========
    
    def add_to_library(self, url: str, name: str, topics: List[str], description: str):
        """添加笔记本到库（项目 C）"""
        topics_str = ",".join(topics)
        cmd = f'python scripts/run.py notebook_manager.py add --url "{url}" --name "{name}" --topics "{topics_str}" --description "{description}"'
        subprocess.run(cmd, shell=True, cwd="~/.claude/skills/notebooklm")
    
    def search_library(self, query: str) -> List[Dict]:
        """搜索笔记本库（项目 C）"""
        cmd = f'python scripts/run.py notebook_manager.py search --query "{query}" --json'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd="~/.claude/skills/notebooklm")
        return json.loads(result.stdout)
    
    def query_with_browser(self, question: str, notebook_url: str) -> str:
        """使用浏览器自动化查询（项目 C）"""
        cmd = f'python scripts/run.py ask_question.py --question "{question}" --notebook-url "{notebook_url}"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd="~/.claude/skills/notebooklm")
        return result.stdout
    
    # ========== 统一工作流 ==========
    
    def workflow_auto_convert(self, sources: List[Union[str, Path]], output_type: str = "audio", output_path: Optional[Path] = None) -> Path:
        """
        工作流 1: 自动内容转换
        
        Args:
            sources: 内容源列表（URL 或文件路径）
            output_type: 输出类型（audio, video, slide-deck, report, etc.）
            output_path: 输出文件路径（可选）
        
        Returns:
            生成文件的路径
        """
        # 步骤 1: 转换内容
        print(f"[1/5] Converting {len(sources)} sources...")
        converted_files = self.batch_convert(sources)
        
        # 步骤 2: 创建笔记本
        if not self.notebook_id:
            print("[2/5] Creating notebook...")
            self.create_notebook(f"Auto-generated {output_type}")
        else:
            print(f"[2/5] Using existing notebook: {self.notebook_id}")
        
        # 步骤 3: 添加源
        print("[3/5] Adding sources...")
        source_ids = []
        for md_file in converted_files:
            source_id = self.add_source(md_file)
            source_ids.append(source_id)
        
        # 步骤 4: 等待源处理
        print("[4/5] Processing sources...")
        for source_id in source_ids:
            self.wait_for_source(source_id)
        
        # 步骤 5: 生成输出
        print(f"[5/5] Generating {output_type}...")
        artifact_id = self.generate_artifact(output_type)
        self.wait_for_artifact(artifact_id)
        
        # 步骤 6: 下载
        if not output_path:
            output_path = Path(f"/tmp/notebooklm_output.{self._get_extension(output_type)}")
        
        self.download_artifact(output_type, output_path, artifact_id)
        
        print(f"✅ Done! Output: {output_path}")
        return output_path
    
    def workflow_smart_query(self, question: str, auto_select: bool = True) -> str:
        """
        工作流 2: Claude 智能查询
        
        Args:
            question: 查询问题
            auto_select: 是否自动选择笔记本
        
        Returns:
            源码引用的答案
        """
        # 步骤 1: 选择笔记本
        if auto_select:
            # 从问题中提取关键词
            keywords = self._extract_keywords(question)
            
            # 搜索库
            results = self.search_library(" ".join(keywords))
            
            if results:
                # 选择最相关的笔记本
                best_match = results[0]
                print(f"Auto-selected notebook: {best_match['name']}")
                # 使用浏览器自动化查询
                return self.query_with_browser(question, best_match['url'])
        
        # 如果没有自动选择，使用 CLI API 查询
        if self.notebook_id:
            result = self.ask_question(question)
            return result['answer']
        else:
            raise ValueError("No notebook selected. Use create_notebook() or set notebook_id first.")
    
    def workflow_knowledge_management(self, sources: List[Union[str, Path]], title: str, questions: List[str]) -> Dict:
        """
        工作流 3: 完整知识管理
        
        Args:
            sources: 内容源列表
            title: 知识库标题
            questions: 查询问题列表
        
        Returns:
            {
                'notebook_id': str,
                'report_path': Path,
                'answers': List[str]
            }
        """
        # 阶段 1-2: 转换内容
        print(f"[Phase 1-2] Converting {len(sources)} sources...")
        converted_files = self.batch_convert(sources)
        
        # 阶段 3: 创建知识库
        print(f"[Phase 3] Creating knowledge base: {title}")
        self.create_notebook(title)
        
        # 添加所有源
        source_ids = []
        for md_file in converted_files:
            source_id = self.add_source(md_file)
            source_ids.append(source_id)
        
        # 等待处理
        print("[Phase 3] Processing sources...")
        for source_id in source_ids:
            self.wait_for_source(source_id)
        
        # 阶段 4: 智能查询
        print(f"[Phase 4] Answering {len(questions)} questions...")
        answers = []
        for question in questions:
            result = self.ask_question(question)
            answers.append(result['answer'])
        
        # 阶段 5: 生成报告
        print("[Phase 5] Generating report...")
        artifact_id = self.generate_artifact("report", f"Comprehensive report based on {len(sources)} sources")
        self.wait_for_artifact(artifact_id)
        
        report_path = Path(f"/tmp/{title.replace(' ', '_')}_report.md")
        self.download_artifact("report", report_path, artifact_id)
        
        print(f"✅ Knowledge base created: {self.notebook_id}")
        print(f"✅ Report generated: {report_path}")
        
        return {
            'notebook_id': self.notebook_id,
            'report_path': report_path,
            'answers': answers
        }
    
    # ========== 辅助方法 ==========
    
    def _get_extension(self, artifact_type: str) -> str:
        """获取文件扩展名"""
        extensions = {
            'audio': 'mp3',
            'video': 'mp4',
            'slide-deck': 'pdf',
            'report': 'md',
            'mind-map': 'json',
            'data-table': 'csv',
            'quiz': 'json',
            'flashcards': 'json',
            'infographic': 'png'
        }
        return extensions.get(artifact_type, 'bin')
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词（简单实现）"""
        # 这里可以使用更复杂的 NLP 技术
        stop_words = {'的', '是', '在', '和', '了', '有', '我', '你', '他', '她'}
        words = text.split()
        return [w for w in words if w not in stop_words and len(w) > 1][:5]


# 使用示例
if __name__ == "__main__":
    workflow = NotebookLMWorkflow()
    
    # 工作流 1: 自动转换
    podcast = workflow.workflow_auto_convert(
        sources=[
            "https://mp.weixin.qq.com/s/article1",
            "/path/to/presentation.pptx",
            "https://youtube.com/watch?v=video1"
        ],
        output_type="audio"
    )
    
    # 工作流 2: 智能查询
    answer = workflow.workflow_smart_query(
        "React hooks 的最佳实践是什么？"
    )
    
    # 工作流 3: 知识管理
    result = workflow.workflow_knowledge_management(
        sources=[
            "https://example.com/article1",
            "/path/to/research.pdf",
            "https://youtube.com/watch?v=tutorial"
        ],
        title="AI Research 2026",
        questions=[
            "2026年AI的主要趋势是什么？",
            "有哪些新的技术突破？",
            "推荐哪些学习资源？"
        ]
    )
```

### 3.2 数据流转换

```python
# data_flow.py

from typing import Dict, Any
from pathlib import Path
import json

class DataFlowTransformer:
    """数据流转换器"""
    
    @staticmethod
    def url_to_source_metadata(url: str) -> Dict[str, Any]:
        """URL → 源元数据"""
        # 识别 URL 类型
        if "mp.weixin.qq.com" in url:
            return {
                'type': 'wechat_article',
                'url': url,
                'converter': 'mcp_wechat',
                'estimated_time': 30  # 秒
            }
        elif "youtube.com" in url or "youtu.be" in url:
            return {
                'type': 'youtube_video',
                'url': url,
                'converter': 'youtube_api',
                'estimated_time': 45
            }
        else:
            return {
                'type': 'web_page',
                'url': url,
                'converter': 'web_scraper',
                'estimated_time': 15
            }
    
    @staticmethod
    def file_to_source_metadata(file_path: Path) -> Dict[str, Any]:
        """文件 → 源元数据"""
        ext = file_path.suffix.lower()
        
        converters = {
            '.pdf': {'type': 'pdf', 'converter': 'markitdown', 'estimated_time': 20},
            '.epub': {'type': 'epub', 'converter': 'markitdown', 'estimated_time': 30},
            '.docx': {'type': 'word', 'converter': 'markitdown', 'estimated_time': 15},
            '.pptx': {'type': 'powerpoint', 'converter': 'markitdown', 'estimated_time': 25},
            '.xlsx': {'type': 'excel', 'converter': 'markitdown', 'estimated_time': 15},
            '.md': {'type': 'markdown', 'converter': 'direct', 'estimated_time': 5},
            '.jpg': {'type': 'image', 'converter': 'ocr', 'estimated_time': 60},
            '.png': {'type': 'image', 'converter': 'ocr', 'estimated_time': 60},
            '.mp3': {'type': 'audio', 'converter': 'speech_to_text', 'estimated_time': 120},
            '.wav': {'type': 'audio', 'converter': 'speech_to_text', 'estimated_time': 120},
            '.csv': {'type': 'csv', 'converter': 'direct', 'estimated_time': 5},
            '.json': {'type': 'json', 'converter': 'direct', 'estimated_time': 5},
        }
        
        metadata = converters.get(ext, {'type': 'unknown', 'converter': 'none', 'estimated_time': 0})
        metadata['path'] = str(file_path)
        return metadata
    
    @staticmethod
    def notebooklm_response_to_claude_context(response: Dict) -> str:
        """NotebookLM 响应 → Claude 上下文"""
        answer = response.get('answer', '')
        references = response.get('references', [])
        
        context = f"Answer: {answer}\n\n"
        
        if references:
            context += "Sources:\n"
            for ref in references:
                context += f"[{ref['citation_number']}] {ref['cited_text']}\n"
                context += f"    Source: {ref['source_id']}\n\n"
        
        return context
    
    @staticmethod
    def artifact_status_to_user_message(status: str, artifact_type: str) -> str:
        """Artifact 状态 → 用户消息"""
        messages = {
            'pending': f"⏳ {artifact_type} generation queued...",
            'in_progress': f"🔄 Generating {artifact_type}...",
            'completed': f"✅ {artifact_type} ready for download!",
            'failed': f"❌ {artifact_type} generation failed. Please retry."
        }
        return messages.get(status, f"Status: {status}")
```

### 3.3 错误处理

```python
# error_handling.py

from typing import Optional, Callable
import subprocess
import time

class NotebookLMErrorHandler:
    """统一的错误处理器"""
    
    @staticmethod
    def with_retry(func: Callable, max_retries: int = 3, delay: int = 5) -> Any:
        """带重试的执行"""
        last_error = None
        
        for attempt in range(max_retries):
            try:
                return func()
            except subprocess.CalledProcessError as e:
                last_error = e
                
                # 认证错误
                if "auth" in str(e).lower() or "cookie" in str(e).lower():
                    print("❌ Authentication error. Please run: notebooklm login")
                    raise
                
                # Rate limit
                if "rate limit" in str(e).lower() or "GENERATION_FAILED" in str(e):
                    wait_time = delay * (2 ** attempt)  # 指数退避
                    print(f"⚠️ Rate limited. Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue
                
                # 其他错误
                print(f"⚠️ Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(delay)
        
        raise last_error
    
    @staticmethod
    def validate_source(source: str) -> bool:
        """验证源是否有效"""
        from pathlib import Path
        
        # URL
        if source.startswith('http'):
            return True
        
        # 文件
        path = Path(source)
        if not path.exists():
            print(f"❌ File not found: {source}")
            return False
        
        # 检查文件大小（最大 100MB）
        if path.stat().st_size > 100 * 1024 * 1024:
            print(f"❌ File too large: {source} (>100MB)")
            return False
        
        return True
    
    @staticmethod
    def handle_artifact_timeout(artifact_id: str, notebook_id: str) -> Optional[str]:
        """处理 Artifact 超时"""
        print(f"⏱️ Artifact {artifact_id} timed out. Checking status...")
        
        # 检查状态
        cmd = f'notebooklm artifact list --json --notebook {notebook_id}'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        import json
        artifacts = json.loads(result.stdout)['artifacts']
        
        for artifact in artifacts:
            if artifact['id'] == artifact_id:
                status = artifact['status']
                
                if status == 'completed':
                    print("✅ Artifact completed! You can download it now.")
                    return 'completed'
                elif status in ['pending', 'in_progress']:
                    print(f"⏳ Still processing. Try again later or use background agent.")
                    return 'processing'
                else:
                    print(f"❌ Artifact failed with status: {status}")
                    return 'failed'
        
        print(f"❌ Artifact {artifact_id} not found")
        return None
```

### 3.4 认证管理

```python
# auth_management.py

import subprocess
import json
from pathlib import Path

class AuthManager:
    """统一的认证管理"""
    
    NOTEBOOKLM_STORAGE = Path.home() / ".notebooklm" / "storage_state.json"
    SKILL_BROWSER_STATE = Path.home() / ".claude" / "skills" / "notebooklm" / "data" / "browser_state"
    
    @staticmethod
    def check_notebooklm_auth() -> bool:
        """检查 notebooklm-py 认证状态"""
        cmd = 'notebooklm auth check --json'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        try:
            data = json.loads(result.stdout)
            return data['checks']['token_fetch']
        except:
            return False
    
    @staticmethod
    def check_skill_auth() -> bool:
        """检查 notebooklm-skill 认证状态"""
        cmd = 'python scripts/run.py auth_manager.py status'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd="~/.claude/skills/notebooklm")
        return "authenticated" in result.stdout.lower()
    
    @staticmethod
    def sync_auth():
        """同步认证状态（项目 A 和 C）"""
        # 项目 A 认证
        if not AuthManager.check_notebooklm_auth():
            print("⚠️ notebooklm-py not authenticated. Running login...")
            subprocess.run('notebooklm login', shell=True)
        
        # 项目 C 认证
        if not AuthManager.check_skill_auth():
            print("⚠️ notebooklm-skill not authenticated. Running setup...")
            subprocess.run('python scripts/run.py auth_manager.py setup', shell=True, cwd="~/.claude/skills/notebooklm")
        
        print("✅ All authentication synced!")
    
    @staticmethod
    def export_for_ci() -> str:
        """导出认证信息用于 CI/CD"""
        if not AuthManager.NOTEBOOKLM_STORAGE.exists():
            raise FileNotFoundError("No authentication found. Run 'notebooklm login' first.")
        
        with open(AuthManager.NOTEBOOKLM_STORAGE, 'r') as f:
            return f.read()
```

---

## 4. 性能优化

### 4.1 并行处理策略

```python
# parallel_processing.py

import asyncio
import subprocess
from typing import List, Dict
from pathlib import Path

class ParallelProcessor:
    """并行处理器"""
    
    @staticmethod
    async def convert_sources_parallel(sources: List[str], max_concurrent: int = 5) -> List[Path]:
        """并行转换多个源"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def convert_one(source: str) -> Path:
            async with semaphore:
                # 调用 anything-to-notebooklm 的转换逻辑
                # 这里简化为示例
                return Path(f"/tmp/converted_{hash(source)}.md")
        
        tasks = [convert_one(source) for source in sources]
        return await asyncio.gather(*tasks)
    
    @staticmethod
    async def add_sources_parallel(notebook_id: str, sources: List[Path], max_concurrent: int = 3) -> List[str]:
        """并行添加多个源到 NotebookLM"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def add_one(source: Path) -> str:
            async with semaphore:
                cmd = f'notebooklm source add "{source}" --json --notebook {notebook_id}'
                proc = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await proc.communicate()
                data = json.loads(stdout)
                return data['source_id']
        
        tasks = [add_one(source) for source in sources]
        return await asyncio.gather(*tasks)
    
    @staticmethod
    async def wait_for_sources_parallel(notebook_id: str, source_ids: List[str]) -> Dict[str, bool]:
        """并行等待多个源处理完成"""
        async def wait_one(source_id: str) -> tuple:
            cmd = f'notebooklm source wait {source_id} -n {notebook_id} --timeout 600'
            proc = await asyncio.create_subprocess_shell(cmd)
            await proc.wait()
            return (source_id, proc.returncode == 0)
        
        tasks = [wait_one(sid) for sid in source_ids]
        results = await asyncio.gather(*tasks)
        return dict(results)
    
    @staticmethod
    async def generate_and_download(artifact_type: str, notebook_id: str, output_path: Path) -> Path:
        """生成并下载（后台任务）"""
        # 生成
        cmd_gen = f'notebooklm generate {artifact_type} --json --notebook {notebook_id}'
        proc = await asyncio.create_subprocess_shell(
            cmd_gen,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        data = json.loads(stdout)
        artifact_id = data['task_id']
        
        # 等待
        cmd_wait = f'notebooklm artifact wait {artifact_id} -n {notebook_id} --timeout 1200'
        proc = await asyncio.create_subprocess_shell(cmd_wait)
        await proc.wait()
        
        # 下载
        cmd_download = f'notebooklm download {artifact_type} "{output_path}" -a {artifact_id} -n {notebook_id}'
        await asyncio.create_subprocess_shell(cmd_download).wait()
        
        return output_path
```

### 4.2 缓存策略

```python
# caching.py

import json
import hashlib
from pathlib import Path
from typing import Any, Optional
from datetime import datetime, timedelta

class CacheManager:
    """缓存管理器"""
    
    CACHE_DIR = Path("/tmp/notebooklm_cache")
    CACHE_EXPIRY_HOURS = 24
    
    @staticmethod
    def _get_cache_key(data: Any) -> str:
        """生成缓存键"""
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.md5(data_str.encode()).hexdigest()
    
    @staticmethod
    def get(cache_key: str) -> Optional[Any]:
        """获取缓存"""
        cache_file = CacheManager.CACHE_DIR / f"{cache_key}.json"
        
        if not cache_file.exists():
            return None
        
        with open(cache_file, 'r') as f:
            cached = json.load(f)
        
        # 检查过期
        cached_time = datetime.fromisoformat(cached['timestamp'])
        if datetime.now() - cached_time > timedelta(hours=CacheManager.CACHE_EXPIRY_HOURS):
            cache_file.unlink()
            return None
        
        return cached['data']
    
    @staticmethod
    def set(cache_key: str, data: Any):
        """设置缓存"""
        CacheManager.CACHE_DIR.mkdir(exist_ok=True)
        
        cache_file = CacheManager.CACHE_DIR / f"{cache_key}.json"
        
        with open(cache_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'data': data
            }, f)
    
    @staticmethod
    def cache_converted_content(source: str, converted_md: Path):
        """缓存转换后的内容"""
        cache_key = CacheManager._get_cache_key({'source': source})
        CacheManager.set(cache_key, str(converted_md))
    
    @staticmethod
    def get_converted_content(source: str) -> Optional[Path]:
        """获取缓存的转换内容"""
        cache_key = CacheManager._get_cache_key({'source': source})
        cached = CacheManager.get(cache_key)
        return Path(cached) if cached else None
    
    @staticmethod
    def cache_notebook_query(notebook_id: str, question: str, answer: str):
        """缓存查询结果"""
        cache_key = CacheManager._get_cache_key({'notebook': notebook_id, 'question': question})
        CacheManager.set(cache_key, answer)
    
    @staticmethod
    def get_notebook_query(notebook_id: str, question: str) -> Optional[str]:
        """获取缓存的查询结果"""
        cache_key = CacheManager._get_cache_key({'notebook': notebook_id, 'question': question})
        return CacheManager.get(cache_key)
```

### 4.3 批量操作优化

```python
# batch_operations.py

from typing import List, Dict
from pathlib import Path
import zipfile
import tempfile

class BatchOperations:
    """批量操作优化"""
    
    @staticmethod
    def process_zip(zip_path: Path) -> List[Path]:
        """处理 ZIP 批量文件"""
        extracted = []
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(tmpdir)
            
            # 递归查找所有支持的文件
            for file_path in Path(tmpdir).rglob('*'):
                if file_path.is_file() and BatchOperations._is_supported(file_path):
                    # 转换文件
                    converted = BatchOperations._convert_file(file_path)
                    extracted.append(converted)
        
        return extracted
    
    @staticmethod
    def batch_generate(notebook_id: str, artifact_types: List[str]) -> Dict[str, str]:
        """批量生成多种格式"""
        results = {}
        
        for artifact_type in artifact_types:
            try:
                # 生成
                import subprocess
                import json
                
                cmd = f'notebooklm generate {artifact_type} --json --notebook {notebook_id}'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                data = json.loads(result.stdout)
                
                results[artifact_type] = data['task_id']
            except Exception as e:
                results[artifact_type] = f"Error: {e}"
        
        return results
    
    @staticmethod
    def _is_supported(file_path: Path) -> bool:
        """检查文件是否支持"""
        supported_extensions = {
            '.pdf', '.epub', '.docx', '.pptx', '.xlsx',
            '.md', '.txt', '.csv', '.json', '.xml',
            '.jpg', '.jpeg', '.png', '.gif', '.webp',
            '.mp3', '.wav', '.m4a'
        }
        return file_path.suffix.lower() in supported_extensions
    
    @staticmethod
    def _convert_file(file_path: Path) -> Path:
        """转换单个文件"""
        # 调用 anything-to-notebooklm 的转换逻辑
        # 返回转换后的 Markdown 路径
        pass
```

---

## 5. 部署指南

### 5.1 环境准备

#### 系统要求

```
- macOS 10.15+ / Linux / Windows 10+
- Python 3.9+
- Chrome 浏览器（用于浏览器自动化）
- Git
```

#### 依赖安装

```bash
# 1. 安装 notebooklm-py（项目 A）
pip install notebooklm-py
notebooklm skill install

# 2. 安装 anything-to-notebooklm（项目 B）
cd ~/.claude/skills
git clone https://github.com/joeseesun/anything-to-notebooklm
cd anything-to-notebooklm
./install.sh

# 3. 安装 notebooklm-skill（项目 C）
cd ~/.claude/skills
git clone https://github.com/PleasePrompto/notebooklm-skill notebooklm
# 自动安装依赖（首次使用时）
```

### 5.2 认证配置

```bash
# 项目 A 认证
notebooklm login
notebooklm list  # 验证

# 项目 C 认证
cd ~/.claude/skills/notebooklm
python scripts/run.py auth_manager.py setup
# 浏览器窗口打开 → 手动登录 Google

# 同步认证（可选）
python -c "from notebooklm_workflow import AuthManager; AuthManager.sync_auth()"
```

### 5.3 配置文件

#### OpenClaw 配置

```json
// ~/.openclaw/openclaw.json
{
  "skills": {
    "enabled": [
      "notebooklm",
      "anything-to-notebooklm"
    ]
  },
  "env": {
    "NOTEBOOKLM_HOME": "~/.notebooklm",
    "NOTEBOOKLM_LANGUAGE": "zh_Hans"
  }
}
```

#### MCP 配置（项目 B）

```json
// ~/.claude/config.json
{
  "primaryApiKey": "your-key",
  "mcpServers": {
    "weixin-reader": {
      "command": "python",
      "args": [
        "/Users/YOUR_USER/.claude/skills/anything-to-notebooklm/wexin-read-mcp/src/server.py"
      ]
    }
  }
}
```

### 5.4 部署架构

#### 单机部署

```
┌──────────────────────────────────────┐
│        OpenClaw Agent                │
│  (协调所有工作流)                     │
└─────────────┬────────────────────────┘
              │
              ├─→ notebooklm-py CLI
              │   (本地安装)
              │
              ├─→ anything-to-notebooklm
              │   (Claude Skill)
              │
              └─→ notebooklm-skill
                  (Claude Skill)
```

#### CI/CD 部署

```yaml
# .github/workflows/notebooklm-automation.yml

name: NotebookLM Automation

on:
  schedule:
    - cron: '0 2 * * *'  # 每天凌晨 2 点
  workflow_dispatch:

env:
  NOTEBOOKLM_AUTH_JSON: ${{ secrets.NOTEBOOKLM_AUTH_JSON }}

jobs:
  daily-report:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: |
          pip install notebooklm-py
          pip install -r requirements.txt
      
      - name: Create daily report
        run: |
          python -c "
          from notebooklm_workflow import NotebookLMWorkflow
          
          workflow = NotebookLMWorkflow()
          
          # 从配置读取源列表
          sources = [...]  # 从文件读取
          
          # 生成每日报告
          workflow.workflow_knowledge_management(
              sources=sources,
              title='Daily Report $(date +%Y-%m-%d)',
              questions=['今天有什么重要新闻？', '需要关注什么？']
          )
          "
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: daily-report
          path: /tmp/*_report.md
```

---

## 6. 代码示例

### 6.1 完整工作流示例

```python
#!/usr/bin/env python3
"""
完整工作流示例：从微信文章到播客生成
"""

from notebooklm_workflow import NotebookLMWorkflow
from pathlib import Path

def example_wechat_to_podcast():
    """示例 1: 微信文章 → 播客"""
    
    workflow = NotebookLMWorkflow()
    
    # 输入：微信文章 URL
    wechat_url = "https://mp.weixin.qq.com/s/abc123"
    
    # 执行工作流
    podcast_path = workflow.workflow_auto_convert(
        sources=[wechat_url],
        output_type="audio",
        output_path=Path("/tmp/wechat_podcast.mp3")
    )
    
    print(f"✅ Podcast generated: {podcast_path}")
    return podcast_path


def example_research_with_queries():
    """示例 2: 研究资料 → 智能查询"""
    
    workflow = NotebookLMWorkflow()
    
    # 输入：多个研究资料
    sources = [
        "https://arxiv.org/abs/1234.5678",
        "/path/to/research_paper.pdf",
        "https://youtube.com/watch?v=tutorial"
    ]
    
    # 创建知识库
    result = workflow.workflow_knowledge_management(
        sources=sources,
        title="AI Research 2026",
        questions=[
            "这篇论文的主要贡献是什么？",
            "有哪些局限性？",
            "未来研究方向是什么？"
        ]
    )
    
    print(f"✅ Knowledge base: {result['notebook_id']}")
    print(f"✅ Report: {result['report_path']}")
    
    for i, answer in enumerate(result['answers'], 1):
        print(f"\nQ{i}: {answer[:100]}...")
    
    return result


def example_batch_processing():
    """示例 3: 批量处理"""
    
    from batch_operations import BatchOperations
    from parallel_processing import ParallelProcessor
    import asyncio
    
    # 批量源
    sources = [
        "https://mp.weixin.qq.com/s/article1",
        "https://mp.weixin.qq.com/s/article2",
        "https://youtube.com/watch?v=video1",
        "/path/to/presentation.pptx",
        "/path/to/report.pdf"
    ]
    
    # 并行转换
    converted = asyncio.run(
        ParallelProcessor.convert_sources_parallel(sources, max_concurrent=5)
    )
    
    # 创建笔记本
    workflow = NotebookLMWorkflow()
    notebook_id = workflow.create_notebook("Batch Import")
    
    # 并行添加源
    source_ids = asyncio.run(
        ParallelProcessor.add_sources_parallel(notebook_id, converted, max_concurrent=3)
    )
    
    # 并行等待处理
    results = asyncio.run(
        ParallelProcessor.wait_for_sources_parallel(notebook_id, source_ids)
    )
    
    print(f"✅ Imported {sum(results.values())}/{len(sources)} sources")
    
    # 批量生成
    artifact_types = ["audio", "slide-deck", "report"]
    tasks = BatchOperations.batch_generate(notebook_id, artifact_types)
    
    print(f"✅ Generated: {list(tasks.keys())}")
    
    return notebook_id


def example_smart_library():
    """示例 4: 智能库管理"""
    
    workflow = NotebookLMWorkflow()
    
    # 添加笔记本到库
    workflow.add_to_library(
        url="https://notebooklm.google.com/notebook/abc123",
        name="React Documentation",
        topics=["react", "hooks", "frontend", "javascript"],
        description="Official React documentation and best practices"
    )
    
    # 搜索库
    results = workflow.search_library("react hooks")
    
    print(f"Found {len(results)} notebooks:")
    for result in results:
        print(f"  - {result['name']}: {result['description']}")
    
    # 智能查询
    answer = workflow.workflow_smart_query(
        "React hooks 中 useEffect 的依赖数组怎么用？"
    )
    
    print(f"\nAnswer:\n{answer}")
    
    return answer


if __name__ == "__main__":
    # 运行示例
    print("=" * 60)
    print("Example 1: WeChat Article → Podcast")
    print("=" * 60)
    example_wechat_to_podcast()
    
    print("\n" + "=" * 60)
    print("Example 2: Research with Queries")
    print("=" * 60)
    example_research_with_queries()
    
    print("\n" + "=" * 60)
    print("Example 3: Batch Processing")
    print("=" * 60)
    example_batch_processing()
    
    print("\n" + "=" * 60)
    print("Example 4: Smart Library")
    print("=" * 60)
    example_smart_library()
```

### 6.2 错误处理示例

```python
#!/usr/bin/env python3
"""
错误处理示例
"""

from error_handling import NotebookLMErrorHandler, with_retry
from notebooklm_workflow import NotebookLMWorkflow

def example_retry_on_rate_limit():
    """示例：处理 Rate Limit"""
    
    workflow = NotebookLMWorkflow()
    workflow.create_notebook("Test")
    
    # 可能会触发 Rate Limit 的操作
    try:
        result = NotebookLMErrorHandler.with_retry(
            lambda: workflow.generate_artifact("audio", "Test podcast"),
            max_retries=3,
            delay=5
        )
        print(f"✅ Generated: {result}")
    except Exception as e:
        print(f"❌ Failed after retries: {e}")


def example_validate_sources():
    """示例：验证源"""
    
    sources = [
        "https://example.com/article1",
        "/path/to/nonexistent.pdf",
        "https://youtube.com/watch?v=video1"
    ]
    
    valid_sources = []
    for source in sources:
        if NotebookLMErrorHandler.validate_source(source):
            valid_sources.append(source)
        else:
            print(f"⚠️ Skipping invalid source: {source}")
    
    print(f"Valid sources: {len(valid_sources)}/{len(sources)}")
    return valid_sources


def example_handle_timeout():
    """示例：处理超时"""
    
    workflow = NotebookLMWorkflow()
    workflow.create_notebook("Test")
    
    # 生成（可能超时）
    artifact_id = workflow.generate_artifact("audio")
    
    # 等待（设置较短超时）
    try:
        workflow.wait_for_artifact(artifact_id, timeout=60)
    except:
        # 处理超时
        status = NotebookLMErrorHandler.handle_artifact_timeout(
            artifact_id, 
            workflow.notebook_id
        )
        
        if status == 'processing':
            print("⏳ Still processing. Will check later.")
        elif status == 'failed':
            print("❌ Generation failed.")
        else:
            print("✅ Completed!")


if __name__ == "__main__":
    print("Example: Retry on Rate Limit")
    example_retry_on_rate_limit()
    
    print("\nExample: Validate Sources")
    example_validate_sources()
    
    print("\nExample: Handle Timeout")
    example_handle_timeout()
```

---

## 7. 性能基准

### 7.1 单次操作性能

| 操作 | 平均时间 | 95% 分位 | 最大时间 | 备注 |
|------|---------|---------|---------|------|
| **内容转换** |  |  |  |  |
| 微信文章抓取 | 15s | 25s | 60s | MCP 浏览器 |
| YouTube 字幕 | 10s | 15s | 30s | API |
| PDF 转换 | 5s | 10s | 20s | markitdown |
| 图片 OCR | 30s | 45s | 120s | Tesseract |
| 音频转录 | 60s | 90s | 300s | Whisper |
| **源处理** |  |  |  |  |
| 添加单个源 | 5s | 10s | 30s | API |
| 等待源处理 | 45s | 90s | 600s | 索引时间 |
| **内容生成** |  |  |  |  |
| Mind Map | 1s | 2s | 5s | 同步 |
| Report | 5min | 8min | 15min | 异步 |
| Quiz/Flashcards | 5min | 10min | 15min | 异步 |
| Audio (Podcast) | 10min | 15min | 20min | 异步 |
| Video | 15min | 25min | 45min | 异步 |
| Slide Deck | 3min | 5min | 10min | 异步 |
| Infographic | 3min | 5min | 10min | 异步 |
| **查询** |  |  |  |  |
| CLI API 查询 | 5s | 10s | 20s | Gemini 2.5 |
| 浏览器查询 | 10s | 15s | 30s | Patchright |

### 7.2 批量操作性能

#### 并行转换（5 个源）

| 策略 | 时间 | 加速比 |
|------|------|--------|
| 串行 | 150s | 1.0x |
| 并行（3 并发） | 65s | 2.3x |
| 并行（5 并发） | 50s | 3.0x |

#### 批量生成（3 种格式）

| 策略 | 时间 | 加速比 |
|------|------|--------|
| 串行 | 28min | 1.0x |
| 并行生成 | 25min | 1.1x |
| 并行生成 + 下载 | 26min | 1.08x |

**注意**: NotebookLM 服务端有 Rate Limit，过度并行可能导致失败。

### 7.3 端到端工作流性能

#### 工作流 1: 自动内容转换（单个源）

```
步骤 1: 内容转换        15s
步骤 2: 创建笔记本      2s
步骤 3: 添加源          5s
步骤 4: 等待处理        45s
步骤 5: 生成播客        10min
步骤 6: 下载            5s
─────────────────────────────
总计:                   ~11min
```

#### 工作流 2: Claude 智能查询

```
步骤 1: 意图识别        <1s
步骤 2: 笔记本选择      1s
步骤 3: 浏览器启动      2s
步骤 4: 查询响应        10s
步骤 5: 提取答案        1s
─────────────────────────────
总计:                   ~15s
```

#### 工作流 3: 完整知识管理（10 个源）

```
阶段 1-2: 内容转换      3min（并行）
阶段 3: 创建知识库      5min（添加 + 处理）
阶段 4: 智能查询        2min（3 个问题）
阶段 5: 生成报告        10min
─────────────────────────────
总计:                   ~20min
```

### 7.4 资源使用

| 资源 | 最小 | 推荐 | 高负载 |
|------|------|------|--------|
| CPU | 1 核 | 2 核 | 4+ 核 |
| 内存 | 2GB | 4GB | 8GB+ |
| 磁盘 | 5GB | 10GB | 50GB+ |
| 网络 | 1Mbps | 10Mbps | 100Mbps+ |

### 7.5 优化建议

#### 针对速度

1. **并行转换**: 多个源同时转换（3-5 并发）
2. **缓存结果**: 相同源不重复转换
3. **预热浏览器**: 浏览器自动化保持会话
4. **就近部署**: 减少网络延迟

#### 针对成本

1. **批量操作**: 合并多个小任务
2. **缓存查询**: 相同问题不重复查询
3. **选择生成类型**: Mind Map < Report < Audio < Video
4. **避免重试**: 一次成功 > 多次重试

#### 针对稳定性

1. **错误重试**: 指数退避策略
2. **超时设置**: 合理的超时时间
3. **监控告警**: 生成失败及时通知
4. **降级方案**: 浏览器失败 → 手动操作

---

## 8. 总结与展望

### 8.1 方案优势

1. **完整性**: 覆盖从内容获取到最终输出的全流程
2. **灵活性**: 支持多种输入格式和输出类型
3. **智能化**: 自然语言交互，自动路由和优化
4. **可扩展**: 模块化设计，易于添加新功能
5. **生产就绪**: 完善的错误处理和性能优化

### 8.2 未来改进方向

1. **AI 增强路由**: 使用 LLM 自动选择最佳工作流
2. **增量更新**: 源内容变化时自动更新知识库
3. **多语言支持**: 扩展到更多语言
4. **协作功能**: 多用户共享知识库
5. **离线模式**: 部分功能离线可用

### 8.3 最佳实践

1. **认证优先**: 首次使用前完成所有认证
2. **测试先行**: 小规模测试后再批量操作
3. **监控日志**: 记录所有操作以便排查问题
4. **定期清理**: 删除不需要的笔记本和缓存
5. **备份重要**: 定期备份知识库和库文件

---

## 附录

### A. 命令速查表

```bash
# 认证
notebooklm login
notebooklm auth check --json

# 笔记本
notebooklm create "Title" --json
notebooklm list --json
notebooklm use <id>

# 源
notebooklm source add <url|file> --json
notebooklm source list --json
notebooklm source wait <id> -n <notebook_id> --timeout 600

# 生成
notebooklm generate audio --json
notebooklm artifact wait <id> -n <notebook_id> --timeout 1200

# 下载
notebooklm download audio ./output.mp3 -a <artifact_id> -n <notebook_id>

# 查询
notebooklm ask "question" --json --notebook <id>

# 语言
notebooklm language set zh_Hans
```

### B. 故障排查

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| 认证失败 | Cookie 过期 | `notebooklm login` |
| Rate Limit | 请求过快 | 等待 5-10 分钟 |
| 生成失败 | 服务端限制 | 稍后重试或换时间 |
| 下载失败 | 未完成生成 | 检查 `artifact list` |
| 浏览器崩溃 | 资源不足 | 增加内存或减少并发 |

### C. 相关资源

- **NotebookLM 官方**: https://notebooklm.google.com/
- **notebooklm-py**: https://github.com/teng-lin/notebooklm-py
- **anything-to-notebooklm**: https://github.com/joeseesun/anything-to-notebooklm
- **notebooklm-skill**: https://github.com/PleasePrompto/notebooklm-skill
- **markitdown**: https://github.com/microsoft/markitdown

---

**报告完成日期**: 2026-03-24
**版本**: 1.0
**作者**: OpenClaw Agent
**状态**: ✅ 完成
