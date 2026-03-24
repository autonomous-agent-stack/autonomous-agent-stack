# 自动化知识图谱构建技术方案

> **创建时间**: 2026-03-24
> **作者**: AI Assistant
> **目标**: 从非结构化文档自动构建知识图谱
> **版本**: 1.0

---

## 📋 目录

1. [项目概述](#项目概述)
2. [技术架构](#技术架构)
3. [文档处理流水线](#文档处理流水线)
4. [实体和关系抽取](#实体和关系抽取)
5. [知识图谱构建](#知识图谱构建)
6. [知识推理和应用](#知识推理和应用)
7. [实际案例：openclaw-memory知识图谱](#实际案例openclaw-memory知识图谱)
8. [性能评估和优化](#性能评估和优化)
9. [完整代码实现](#完整代码实现)
10. [部署和运维](#部署和运维)

---

## 项目概述

### 目标

自动化知识图谱构建项目旨在从非结构化文档（PDF、Word、Markdown等）中自动提取实体、关系和属性，构建结构化的知识图谱，并支持知识推理和智能问答。

### 核心能力

1. **自动实体识别**：识别文本中的命名实体（人名、地名、机构、技术术语等）
2. **自动关系抽取**：识别实体之间的语义关系
3. **自动知识推理**：基于已有知识推导新知识
4. **知识可视化**：提供图谱可视化界面
5. **智能问答**：支持基于知识图谱的问答系统

### 技术栈

- **语言**: Python 3.10+
- **NLP**: spaCy, Hugging Face Transformers, LlamaIndex
- **图数据库**: Neo4j
- **向量数据库**: ChromaDB, Weaviate (可选，用于混合检索)
- **文档解析**: PyPDF2, python-docx, pypandoc
- **可视化**: Pyvis, Neo4j Bloom
- **Web框架**: FastAPI, Streamlit

---

## 技术架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                     文档输入层                               │
│  PDF | Word | Markdown | HTML | 纯文本                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  文档处理流水线                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                   │
│  │ 文档解析  │→ │ 文本清洗  │→ │ 结构识别  │                   │
│  └──────────┘  └──────────┘  └──────────┘                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              NLP 信息抽取层                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                   │
│  │ NER实体  │→ │关系抽取  │→ │共指消解  │                   │
│  └──────────┘  └──────────┘  └──────────┘                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              知识图谱存储层                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                   │
│  │ Neo4j    │  │ 索引优化  │→ │ 图查询   │                   │
│  │ 图数据库  │  └──────────┘  └──────────┘                   │
│  └──────────┘                                                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              应用服务层                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                   │
│  │ 知识推理  │  │ 智能问答  │  │ 图谱可视化│                   │
│  └──────────┘  └──────────┘  └──────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

### 核心模块

#### 1. 文档处理模块
- 多格式文档解析
- 文本清洗和标准化
- 章节和段落结构识别
- 表格数据提取

#### 2. NLP 抽取模块
- 命名实体识别（NER）
- 关系抽取
- 共指消解
- 属性提取

#### 3. 图谱构建模块
- 图数据库连接和操作
- 知识表示（节点、边、属性）
- 索引和约束管理
- 批量数据导入

#### 4. 推理和应用模块
- 基于规则的推理
- 图算法（路径查找、中心性分析等）
- 自然语言问答
- 知识补全

---

## 文档处理流水线

### 1.1 文档解析

#### 支持的文档格式

| 格式 | Python库 | 特点 |
|------|---------|------|
| PDF | PyPDF2, pdfplumber | 支持表格、图片提取 |
| Word | python-docx | 保持格式、样式 |
| Markdown | markdown, frontmatter | 结构化文本、元数据 |
| HTML | BeautifulSoup | 网页内容提取 |
| 纯文本 | 原生Python | 最简单处理 |

#### PDF 解析实现

```python
import pdfplumber
from typing import List, Dict
import re

class PDFParser:
    """PDF文档解析器"""
    
    def __init__(self):
        self.text = ""
        self.pages = []
        self.tables = []
        self.metadata = {}
    
    def parse(self, file_path: str) -> Dict:
        """
        解析PDF文件
        
        Args:
            file_path: PDF文件路径
            
        Returns:
            解析结果字典
        """
        result = {
            "text": "",
            "pages": [],
            "tables": [],
            "metadata": {}
        }
        
        with pdfplumber.open(file_path) as pdf:
            # 提取元数据
            result["metadata"] = {
                "title": pdf.metadata.get("Title", ""),
                "author": pdf.metadata.get("Author", ""),
                "creator": pdf.metadata.get("Creator", ""),
                "producer": pdf.metadata.get("Producer", ""),
                "page_count": len(pdf.pages)
            }
            
            # 逐页处理
            for i, page in enumerate(pdf.pages):
                page_data = {
                    "page_num": i + 1,
                    "text": page.extract_text(),
                    "tables": page.extract_tables()
                }
                
                result["pages"].append(page_data)
                result["text"] += page_data["text"] + "\n\n"
                
                # 提取表格
                if page_data["tables"]:
                    for table in page_data["tables"]:
                        result["tables"].append({
                            "page": i + 1,
                            "data": table
                        })
        
        return result
    
    def extract_structure(self, text: str) -> List[Dict]:
        """
        从文本中提取章节结构
        
        Args:
            text: 文本内容
            
        Returns:
            章节列表
        """
        sections = []
        lines = text.split('\n')
        
        current_section = {
            "title": "Introduction",
            "level": 0,
            "content": []
        }
        
        section_patterns = {
            1: r'^#{1}\s+(.+)$',
            2: r'^#{2}\s+(.+)$',
            3: r'^#{3}\s+(.+)$',
            4: r'^#{4}\s+(.+)$'
        }
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 检测章节标题
            matched = False
            for level, pattern in section_patterns.items():
                match = re.match(pattern, line)
                if match:
                    # 保存当前章节
                    if current_section["content"]:
                        sections.append(current_section.copy())
                    
                    # 开始新章节
                    current_section = {
                        "title": match.group(1),
                        "level": level,
                        "content": []
                    }
                    matched = True
                    break
            
            if not matched:
                current_section["content"].append(line)
        
        # 添加最后一个章节
        if current_section["content"]:
            sections.append(current_section)
        
        return sections
```

#### Word 文档解析

```python
from docx import Document
from typing import Dict, List

class WordParser:
    """Word文档解析器"""
    
    def __init__(self):
        pass
    
    def parse(self, file_path: str) -> Dict:
        """
        解析Word文档
        
        Args:
            file_path: Word文件路径
            
        Returns:
            解析结果字典
        """
        doc = Document(file_path)
        
        result = {
            "text": "",
            "paragraphs": [],
            "tables": [],
            "metadata": {}
        }
        
        # 提取元数据
        core_props = doc.core_properties
        result["metadata"] = {
            "title": core_props.title or "",
            "author": core_props.author or "",
            "created": core_props.created,
            "modified": core_props.modified,
            "page_count": len(doc.paragraphs)
        }
        
        # 提取段落
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                result["paragraphs"].append({
                    "text": text,
                    "style": para.style.name if para.style else "",
                    "level": self._get_heading_level(para.style.name)
                })
                result["text"] += text + "\n"
        
        # 提取表格
        for table in doc.tables:
            table_data = []
            for row in table.rows:
                row_data = [cell.text.strip() for cell in row.cells]
                table_data.append(row_data)
            result["tables"].append(table_data)
        
        return result
    
    def _get_heading_level(self, style_name: str) -> int:
        """获取标题级别"""
        if 'Heading' in style_name:
            return int(style_name.split(' ')[-1])
        return 0
```

### 1.2 文本清洗和预处理

```python
import re
import unicodedata
from typing import List, Tuple
import jieba
from jieba import posseg

class TextCleaner:
    """文本清洗器"""
    
    def __init__(self):
        # 中文停用词
        self.stopwords = set([
            "的", "了", "在", "是", "我", "有", "和", "就", "不", "人",
            "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去",
            "你", "会", "着", "没有", "看", "好", "自己", "这", "那", "么"
        ])
        
        # 初始化jieba分词
        jieba.initialize()
    
    def clean(self, text: str) -> str:
        """
        清洗文本
        
        Args:
            text: 原始文本
            
        Returns:
            清洗后的文本
        """
        # 移除特殊字符和多余空白
        text = self._remove_special_chars(text)
        
        # 标准化Unicode字符
        text = unicodedata.normalize('NFKC', text)
        
        # 移除HTML标签
        text = re.sub(r'<[^>]+>', '', text)
        
        # 移除多余空白
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _remove_special_chars(self, text: str) -> str:
        """移除特殊字符"""
        # 保留中文、英文、数字、常见标点
        pattern = r'[^\u4e00-\u9fa5a-zA-Z0-9\s.,;:!?()""''""'""—……]'
        return re.sub(pattern, '', text)
    
    def tokenize(self, text: str) -> List[Tuple[str, str]]:
        """
        中文分词和词性标注
        
        Args:
            text: 文本
            
        Returns:
            [(词语, 词性), ...]
        """
        words = posseg.cut(text)
        return [(word.word, word.flag) for word in words 
                if len(word.word) > 1 and word.word not in self.stopwords]
    
    def extract_sentences(self, text: str) -> List[str]:
        """
        句子分割
        
        Args:
            text: 文本
            
        Returns:
            句子列表
        """
        # 中文句子分割
        sentences = re.split(r'[。！？；]', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def extract_paragraphs(self, text: str) -> List[str]:
        """
        段落分割
        
        Args:
            text: 文本
            
        Returns:
            段落列表
        """
        paragraphs = text.split('\n\n')
        return [p.strip() for p in paragraphs if p.strip()]
```

### 1.3 章节结构识别

```python
from typing import List, Dict
import re

class StructureExtractor:
    """章节结构提取器"""
    
    def __init__(self):
        # 章节标题模式
        self.heading_patterns = {
            1: [r'^第[一二三四五六七八九十百]+章\s+(.+)$', r'^#{1}\s+(.+)$'],
            2: [r'^\d+\.\d+\s+(.+)$', r'^#{2}\s+(.+)$'],
            3: [r'^\d+\.\d+\.\d+\s+(.+)$', r'^#{3}\s+(.+)$'],
            4: [r'^#{4}\s+(.+)$']
        }
    
    def extract(self, text: str) -> List[Dict]:
        """
        提取章节结构
        
        Args:
            text: 文本内容
            
        Returns:
            章节列表
        """
        lines = text.split('\n')
        sections = []
        
        current_section = {
            "id": 0,
            "title": "前言",
            "level": 0,
            "content": [],
            "children": []
        }
        
        section_stack = [current_section]
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 检测是否为章节标题
            level, title = self._match_heading(line)
            
            if level > 0:
                # 保存当前章节
                if current_section["content"]:
                    sections.append(current_section.copy())
                    current_section["content"] = []
                
                # 创建新章节
                new_section = {
                    "id": len(sections),
                    "title": title,
                    "level": level,
                    "content": [],
                    "children": []
                }
                
                # 更新章节栈
                while section_stack and section_stack[-1]["level"] >= level:
                    section_stack.pop()
                
                if section_stack:
                    section_stack[-1]["children"].append(new_section)
                
                section_stack.append(new_section)
                current_section = new_section
            else:
                current_section["content"].append(line)
        
        # 添加最后一个章节
        if current_section["content"]:
            sections.append(current_section)
        
        return self._flatten_structure(sections[0] if sections else {})
    
    def _match_heading(self, line: str) -> Tuple[int, str]:
        """匹配章节标题"""
        for level, patterns in self.heading_patterns.items():
            for pattern in patterns:
                match = re.match(pattern, line)
                if match:
                    return level, match.group(1)
        return 0, ""
    
    def _flatten_structure(self, root: Dict) -> List[Dict]:
        """扁平化章节结构"""
        result = []
        
        def traverse(section: Dict, path: List[str]):
            current_path = path + [section["title"]]
            section["path"] " ".join(current_path)
            result.append(section.copy())
            
            for child in section.get("children", []):
                traverse(child, current_path)
        
        traverse(root, [])
        return result
```

---

## 实体和关系抽取

### 2.1 命名实体识别（NER）

#### 使用spaCy进行实体识别

```python
import spacy
from typing import List, Dict
import spacy.cli

class EntityExtractor:
    """实体提取器"""
    
    def __init__(self, model_name: str = "zh_core_web_lg"):
        """
        初始化实体提取器
        
        Args:
            model_name: spaCy模型名称
        """
        try:
            self.nlp = spacy.load(model_name)
        except OSError:
            # 下载模型
            spacy.cli.download(model_name)
            self.nlp = spacy.load(model_name)
        
        # 自定义实体类型
        self.custom_entities = {
            "TECHNOLOGY": ["Python", "JavaScript", "React", "Vue", "Neo4j"],
            "FRAMEWORK": ["LangGraph", "Temporale", "Airflow"],
            "TOOL": ["spaCy", "Hugging Face", "LlamaIndex"]
        }
    
    def extract(self, text: str) -> List[Dict]:
        """
        提取实体
        
        Args:
            text: 文本内容
            
        Returns:
            实体列表
        """
        doc = self.nlp(text)
        entities = []
        
        for ent in doc.ents:
            entity = {
                "text": ent.text,
                "label": ent.label_,
                "start": ent.start_char,
                "end": ent.end_char,
                "description": spacy.explain(ent.label_)
            }
            entities.append(entity)
        
        # 添加自定义实体
        entities.extend(self._extract_custom_entities(text))
        
        return entities
    
    def _extract_custom_entities(self, text: str) -> List[Dict]:
        """提取自定义实体"""
        entities = []
        
        for entity_type, keywords in self.custom_entities.items():
            for keyword in keywords:
                if keyword in text:
                    # 查找所有出现位置
                    start = 0
                    while True:
                        pos = text.find(keyword, start)
                        if pos == -1:
                            break
                        entities.append({
                            "text": keyword,
                            "label": entity_type,
                            "start": pos,
                            "end": pos + len(keyword),
                            "description": f"自定义实体: {entity_type}"
                        })
                        start = pos + 1
        
        return entities
    
    def extract_with_context(self, text: str, window_size: int = 20) -> List[Dict]:
        """
        提取实体及其上下文
        
        Args:
            text: 文本内容
            window_size: 上下文窗口大小
            
        Returns:
            带上下文的实体列表
        """
        entities = self.extract(text)
        
        for entity in entities:
            start = max(0, entity["start"] - window_size)
            end = min(len(text), entity["end"] + window_size)
            entity["context"] = text[start:end].strip()
        
        return entities
```

#### 使用Hugging Face Transformers进行实体识别

```python
from transformers import AutoTokenizer, AutoModelForTokenClassification
import torch
from typing import List, Dict

class TransformerEntityExtractor:
    """基于Transformer的实体提取器"""
    
    def __init__(self, model_name: str = "ckiplab/bert-base-chinese-ner"):
        """
        初始化提取器
        
        Args:
            model_name: Hugging Face模型名称
        """
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForTokenClassification.from_pretrained(model_name)
        
        # 标签映射
        self.label_map = {
            "B-LOC": "LOCATION",
            "I-LOC": "LOCATION",
            "B-PER": "PERSON",
            "I-PER": "PERSON",
            "B-ORG": "ORGANIZATION",
            "I-ORG": "ORGANIZATION"
        }
    
    def extract(self, text: str) -> List[Dict]:
        """
        提取实体
        
        Args:
            text: 文本内容
            
        Returns:
            实体列表
        """
        # Tokenize
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512
        )
        
        # 预测
        with torch.no_grad():
            outputs = self.model(**inputs)
        
        predictions = torch.argmax(outputs.logits, dim=2)[0]
        
        # 解码标签
        entities = self._decode_entities(
            text,
            inputs["input_ids"][0],
            predictions
        )
        
        return entities
    
    def _decode_entities(self, text: str, input_ids: torch.Tensor, 
                        predictions: torch.Tensor) -> List[Dict]:
        """解码实体标签"""
        entities = []
        current_entity = None
        
        for idx, (token_id, pred_id) in enumerate(zip(input_ids, predictions)):
            if token_id in [self.tokenizer.cls_token_id, 
                           self.tokenizer.sep_token_id,
                           self.tokenizer.pad_token_id]:
                continue
            
            token = self.tokenizer.decode([token_id])
            label = self.model.config.id2label[pred_id.item()]
            
            # 处理BIO标签
            if label.startswith("B-"):
                # 保存前一个实体
                if current_entity:
                    entities.append(current_entity)
                
                # 开始新实体
                entity_type = self.label_map.get(label, label)
                current_entity = {
                    "text": token,
                    "label": entity_type,
                    "tokens": [token]
                }
            
            elif label.startswith("I-") and current_entity:
                # 继续当前实体
                entity_type = self.label_map.get(label, label)
                if current_entity["label"] == entity_type:
                    current_entity["text"] += token
                    current_entity["tokens"].append(token)
            else:
                # 结束当前实体
                if current_entity:
                    entities.append(current_entity)
                    current_entity = None
        
        # 添加最后一个实体
        if current_entity:
            entities.append(current_entity)
        
        return entities
```

### 2.2 关系抽取

#### 基于规则的关系抽取

```python
import re
from typing import List, Dict, Tuple
import spacy

class RelationExtractor:
    """关系抽取器"""
    
    def __init__(self):
        self.nlp = spacy.load("zh_core_web_lg")
        
        # 关系模式
        self.relation_patterns = {
            "WORKS_FOR": [
                r'(.+?)在(.+?)工作',
                r'(.+?)是(.+?)的员工',
                r'(.+?)就职于(.+?)'
            ],
            "LOCATED_IN": [
                r'(.+?)位于(.+?)',
                r'(.+?)在(.+?)',
                r'(.+?)坐落在(.+?)'
            ],
            "CREATED_BY": [
                r'(.+?)由(.+?)创建',
                r'(.+?)是(.+?)的作品',
                r'(.+?)出自(.+?)之手'
            ],
            "USE_TECHNOLOGY": [
                r'(.+?)使用(.+?)',
                r'(.+?)采用(.+?)技术',
                r'(.+?)基于(.+?)开发'
            ]
        }
        
        # 关系类型映射
        self.relation_types = {
            "WORKS_FOR": "works_for",
            "LOCATED_IN": "located_in",
            "CREATED_BY": "created_by",
            "USE_TECHNOLOGY": "uses"
        }
    
    def extract(self, text: str, entities: List[Dict]) -> List[Dict]:
        """
        提取关系
        
        Args:
            text: 文本内容
            entities: 实体列表
            
        Returns:
            关系列表
        """
        relations = []
        
        # 方法1: 基于模式匹配
        pattern_relations = self._extract_by_patterns(text)
        relations.extend(pattern_relations)
        
        # 方法2: 基于依存句法分析
        dep_relations = self._extract_by_dependencies(text, entities)
        relations.extend(dep_relations)
        
        # 去重
        relations = self._deduplicate_relations(relations)
        
        return relations
    
    def _extract_by_patterns(self, text: str) -> List[Dict]:
        """基于模式匹配提取关系"""
        relations = []
        
        for relation_type, patterns in self.relation_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text)
                for match in matches:
                    if len(match.groups()) >= 2:
                        entity1 = match.group(1).strip()
                        entity2 = match.group(2).strip()
                        
                        relations.append({
                            "source": entity1,
                            "target": entity2,
                            "type": relation_type,
                            "confidence": 0.8,
                            "method": "pattern_matching"
                        })
        
        return relations
    
    def _extract_by_dependencies(self, text: str, 
                                 entities: List[Dict]) -> List[Dict]:
        """基于依存句法分析提取关系"""
        relations = []
        
        doc = self.nlp(text)
        
        # 构建实体字典
        entity_map = {}
        for entity in entities:
            entity_map[entity["text"]] = entity
        
        # 遍历依存关系
        for token in doc:
            # 查找主谓宾结构
            if token.dep_ in ["nsubj", "nsubjpass"]:
                # 主语
                subject = token.text
                # 谓语
                verb = token.head.text
                # 宾语
                objects = [child.text for child in token.head.children 
                          if child.dep_ in ["dobj", "obj"]]
                
                if objects:
                    for obj in objects:
                        # 判断是否为已知实体
                        if subject in entity_map and obj in entity_map:
                            relations.append({
                                "source": subject,
                                "target": obj,
                                "type": self._infer_relation_type(verb),
                                "confidence": 0.7,
                                "method": "dependency_parsing"
                            })
        
        return relations
    
    def _infer_relation_type(self, verb: str) -> str:
        """推断关系类型"""
        verb = verb.lower()
        
        if verb in ["工作", "就职", "任职"]:
            return "WORKS_FOR"
        elif verb in ["位于", "在", "坐落"]:
            return "LOCATED_IN"
        elif verb in ["创建", "开发", "制作"]:
            return "CREATED_BY"
        elif verb in ["使用", "采用", "应用"]:
            return "USE_TECHNOLOGY"
        else:
            return "RELATED_TO"
    
    def _deduplicate_relations(self, relations: List[Dict]) -> List[Dict]:
        """去重"""
        seen = set()
        unique_relations = []
        
        for rel in relations:
            key = (rel["source"], rel["target"], rel["type"])
            if key not in seen:
                seen.add(key)
                unique_relations.append(rel)
        
        return unique_relations
```

#### 基于LLM的关系抽取

```python
from openai import OpenAI
from typing import List, Dict

class LLMRelationExtractor:
    """基于大语言模型的关系抽取器"""
    
    def __init__(self, api_key: str = None):
        """
        初始化
        
        Args:
            api_key: OpenAI API密钥
        """
        self.client = OpenAI(api_key=api_key)
        
        self.system_prompt = """
        你是一个专业的实体关系抽取专家。你的任务是从给定的文本中识别实体并提取它们之间的关系。

        请返回JSON格式的结果，包含以下字段：
        - entities: 实体列表，每个实体包含text和label
        - relations: 关系列表，每个关系包含source（源实体）、target（目标实体）、type（关系类型）和confidence（置信度）

        常见的关系类型包括：
        - WORKS_FOR: 工作关系
        - LOCATED_IN: 位置关系
        - CREATED_BY: 创建关系
        - USE_TECHNOLOGY: 使用技术关系
        - RELATED_TO: 通用相关关系
        """
    
    def extract(self, text: str) -> Dict:
        """
        使用LLM提取关系
        
        Args:
            text: 文本内容
            
        Returns:
            包含实体和关系的字典
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"文本: {text}"}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            return result
        
        except Exception as e:
            print(f"LLM提取失败: {e}")
            return {"entities": [], "relations": []}
```

### 2.3 共指消解

```python
import spacy
from typing import List, Dict
import neuralcoref

class CoreferenceResolver:
    """共指消解器"""
    
    def __init__(self):
        """初始化共指消解器"""
        self.nlp = spacy.load("en_core_web_lg")
        neuralcoref.add_to_pipe(self.nlp)
    
    def resolve(self, text: str) -> str:
        """
        执行共指消解
        
        Args:
            text: 原始文本
            
        Returns:
            消解后的文本
        """
        doc = self.nlp(text)
        
        # neuralcoref会自动解析共指
        resolved = doc._.coref_resolved
        
        return resolved
    
    def get_coref_clusters(self, text: str) -> List[Dict]:
        """
        获取共指簇
        
        Args:
            text: 文本内容
            
        Returns:
            共指簇列表
        """
        doc = self.nlp(text)
        
        clusters = []
        for cluster in doc._.coref_clusters:
            cluster_info = {
                "main": cluster.main.text,
                "mentions": [m.text for m in cluster.mentions]
            }
            clusters.append(cluster_info)
        
        return clusters
```

---

## 知识图谱构建

### 3.1 Neo4j图数据库集成

```python
from neo4j import GraphDatabase
from typing import List, Dict, Any
import json

class Neo4jManager:
    """Neo4j数据库管理器"""
    
    def __init__(self, uri: str, user: str, password: str):
        """
        初始化数据库连接
        
        Args:
            uri: Neo4j数据库URI
            user: 用户名
            password: 密码
        """
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.database = "neo4j"
    
    def close(self):
        """关闭数据库连接"""
        self.driver.close()
    
    def execute_query(self, query: str, parameters: Dict = None) -> Any:
        """
        执行Cypher查询
        
        Args:
            query: Cypher查询语句
            parameters: 查询参数
            
        Returns:
            查询结果
        """
        with self.driver.session(database=self.database) as session:
            result = session.run(query, parameters)
            return [record for record in result]
    
    def create_constraint(self, label: str, property: str):
        """
        创建唯一性约束
        
        Args:
            label: 节点标签
            property: 属性名
        """
        query = f"""
        CREATE CONSTRAINT IF NOT EXISTS 
        FOR (n:{label}) REQUIRE n.{property} IS UNIQUE
        """
        self.execute_query(query)
    
    def create_index(self, label: str, property: str):
        """
        创建索引
        
        Args:
            label: 节点标签
            property: 属性名
        """
        query = f"""
        CREATE INDEX IF NOT EXISTS 
        FOR (n:{label}) ON (n.{property})
        """
        self.execute_query(query)
    
    def initialize_schema(self):
        """初始化数据库schema"""
        # 创建实体节点的唯一性约束
        entity_types = ["Person", "Organization", "Location", 
                        "Technology", "Concept", "Document"]
        
        for entity_type in entity_types:
            self.create_constraint(entity_type, "id")
            self.create_index(entity_type, "name")
        
        # 创建关系索引
        relation_types = ["WORKS_FOR", "LOCATED_IN", "CREATED_BY", 
                          "USE_TECHNOLOGY", "RELATED_TO"]
        
        # 创建全文索引
        self.create_fulltext_index(["Person", "Organization"], "name")
    
    def create_fulltext_index(self, labels: List[str], property: str):
        """
        创建全文索引
        
        Args:
            labels: 标签列表
            property: 属性名
        """
        labels_str = ":".join(labels)
        query = f"""
        CREATE FULLTEXT INDEX node_fulltext_{property} 
        IF NOT EXISTS 
        FOR (n:{labels_str}) 
        ON EACH [n.{property}]
        """
        self.execute_query(query)
    
    def add_node(self, label: str, properties: Dict) -> str:
        """
        添加节点
        
        Args:
            label: 节点标签
            properties: 节点属性
            
        Returns:
            节点ID
        """
        query = f"""
        MERGE (n:{label} {{id: $id}})
        SET n += $properties
        RETURN n.id as id
        """
        result = self.execute_query(query, {
            "id": properties.get("id"),
            "properties": properties
        })
        
        return result[0]["id"] if result else None
    
    def add_relationship(self, source_id: str, target_id: str, 
                        relation_type: str, properties: Dict = None):
        """
        添加关系
        
        Args:
            source_id: 源节点ID
            target_id: 目标节点ID
            relation_type: 关系类型
            properties: 关系属性
        """
        properties = properties or {}
        query = f"""
        MATCH (source {{id: $source_id}})
        MATCH (target {{id: $target_id}})
        MERGE (source)-[r:{relation_type}]->(target)
        SET r += $properties
        """
        
        self.execute_query(query, {
            "source_id": source_id,
            "target_id": target_id,
            "properties": properties
        })
    
    def batch_add_nodes(self, nodes: List[Dict]):
        """
        批量添加节点
        
        Args:
            nodes: 节点列表，每个节点包含label和properties
        """
        # 按标签分组
        label_groups = {}
        for node in nodes:
            label = node["label"]
            if label not in label_groups:
                label_groups[label] = []
            label_groups[label].append(node["properties"])
        
        # 批量导入
        for label, properties_list in label_groups.items():
            query = f"""
            UNWIND $nodes AS node
            MERGE (n:{label} {{id: node.id}})
            SET n += node
            """
            
            self.execute_query(query, {"nodes": properties_list})
    
    def batch_add_relationships(self, relationships: List[Dict]):
        """
        批量添加关系
        
        Args:
            relationships: 关系列表
        """
        query = """
        UNWIND $rels AS rel
        MATCH (source {id: rel.source_id})
        MATCH (target {id: rel.target_id})
        MERGE (source)-[r:rel.type]->(target)
        SET r += rel.properties
        """
        
        self.execute_query(query, {"rels": relationships})
    
    def find_node_by_name(self, name: str, label: str = None) -> Dict:
        """
        根据名称查找节点
        
        Args:
            name: 节点名称
            label: 节点标签（可选）
            
        Returns:
            节点信息
        """
        if label:
            query = f"""
            MATCH (n:{label} {{name: $name}})
            RETURN n
            """
        else:
            query = """
            MATCH (n {name: $name})
            RETURN n
            """
        
        result = self.execute_query(query, {"name": name})
        return result[0]["n"] if result else None
    
    def fulltext_search(self, query: str, label: str = None, 
                       limit: int = 10) -> List[Dict]:
        """
        全文搜索
        
        Args:
            query: 搜索查询
            label: 节点标签（可选）
            limit: 返回数量限制
            
        Returns:
            搜索结果
        """
        index_name = f"node_fulltext_name"
        
        if label:
            cypher_query = f"""
            CALL db.index.fulltext.queryNodes($index_name, $query)
            YIELD node, score
            WHERE node:{label}
            RETURN node.name as name, labels(node) as labels, score
            ORDER BY score DESC
            LIMIT $limit
            """
        else:
            cypher_query = f"""
            CALL db.index.fulltext.queryNodes($index_name, $query)
            YIELD node, score
            RETURN node.name as name, labels(node) as labels, score
            ORDER BY score DESC
            LIMIT $limit
            """
        
        result = self.execute_query(cypher_query, {
            "index_name": index_name,
            "query": query,
            "limit": limit
        })
        
        return result
    
    def get_neighbors(self, node_id: str, depth: int = 1) -> Dict:
        """
        获取节点的邻居
        
        Args:
            node_id: 节点ID
            depth: 深度
            
        Returns:
            邻居信息
        """
        query = f"""
        MATCH (n {{id: $node_id}})
        CALL {{
            WITH n
            MATCH (n)-[r*1..{depth}]-(neighbor)
            RETURN neighbor
        }}
        RETURN DISTINCT neighbor
        """
        
        result = self.execute_query(query, {"node_id": node_id})
        return result
    
    def find_shortest_path(self, source_id: str, target_id: str) -> List[Dict]:
        """
        查找最短路径
        
        Args:
            source_id: 源节点ID
            target_id: 目标节点ID
            
        Returns:
            路径
        """
        query = """
        MATCH path = shortestPath(
            (source {id: $source_id})-[*]-(target {id: $target_id})
        )
        RETURN path
        """
        
        result = self.execute_query(query, {
            "source_id": source_id,
            "target_id": target_id
        })
        
        return result
```

### 3.2 知识表示和存储

```python
from typing import List, Dict
import hashlib
import json

class KnowledgeGraphBuilder:
    """知识图谱构建器"""
    
    def __init__(self, neo4j_manager: Neo4jManager):
        """
        初始化
        
        Args:
            neo4j_manager: Neo4j数据库管理器
        """
        self.neo4j = neo4j_manager
        
        # 实体类型映射
        self.entity_type_map = {
            "PERSON": "Person",
            "ORG": "Organization",
            "GPE": "Location",
            "TECHNOLOGY": "Technology",
            "CONCEPT": "Concept",
            "DOCUMENT": "Document"
        }
    
    def build_from_documents(self, documents: List[Dict]):
        """
        从文档构建知识图谱
        
        Args:
            documents: 文档列表，每个文档包含text、entities、relations
        """
        # 批量添加文档节点
        doc_nodes = []
        for i, doc in enumerate(documents):
            doc_node = {
                "label": "Document",
                "properties": {
                    "id": f"doc_{i}",
                    "title": doc.get("title", f"Document {i}"),
                    "content": doc["text"],
                    "metadata": json.dumps(doc.get("metadata", {}))
                }
            }
            doc_nodes.append(doc_node)
        
        self.neo4j.batch_add_nodes(doc_nodes)
        
        # 处理每个文档
        for i, doc in enumerate(documents):
            self._process_document(doc, f"doc_{i}")
    
    def _process_document(self, doc: Dict, doc_id: str):
        """
        处理单个文档
        
        Args:
            doc: 文档数据
            doc_id: 文档ID
        """
        # 添加实体节点
        entities = doc.get("entities", [])
        entity_nodes = self._create_entity_nodes(entities, doc_id)
        
        # 添加关系
        relations = doc.get("relations", [])
        self._create_relationships(relations, entity_nodes)
        
        # 将实体与文档关联
        for entity_node in entity_nodes:
            self.neo4j.add_relationship(
                doc_id,
                entity_node["id"],
                "CONTAINS",
                {"source": doc.get("title", "")}
            )
    
    def _create_entity_nodes(self, entities: List[Dict], 
                           doc_id: str) -> List[Dict]:
        """
        创建实体节点
        
        Args:
            entities: 实体列表
            doc_id: 文档ID
            
        Returns:
            实体节点列表
        """
        entity_nodes = []
        
        for i, entity in enumerate(entities):
            # 确定实体类型
            entity_type = self.entity_type_map.get(
                entity.get("label", "CONCEPT"),
                "Concept"
            )
            
            # 生成唯一ID
            entity_id = self._generate_entity_id(
                entity["text"],
                entity_type
            )
            
            # 创建节点属性
            properties = {
                "id": entity_id,
                "name": entity["text"],
                "type": entity.get("label", "CONCEPT"),
                "frequency": entity.get("frequency", 1),
                "source_doc": doc_id
            }
            
            # 添加节点
            self.neo4j.add_node(entity_type, properties)
            
            entity_nodes.append({
                "id": entity_id,
                "text": entity["text"],
                "type": entity_type
            })
        
        return entity_nodes
    
    def _create_relationships(self, relations: List[Dict], 
                            entity_nodes: List[Dict]):
        """
        创建关系
        
        Args:
            relations: 关系列表
            entity_nodes: 实体节点列表
        """
        # 构建实体名称到ID的映射
        entity_map = {node["text"]: node["id"] for node in entity_nodes}
        
        for relation in relations:
            source_name = relation["source"]
            target_name = relation["target"]
            relation_type = relation["type"]
            
            # 检查实体是否存在
            if source_name in entity_map and target_name in entity_map:
                self.neo4j.add_relationship(
                    entity_map[source_name],
                    entity_map[target_name],
                    relation_type,
                    {
                        "confidence": relation.get("confidence", 0.5),
                        "source": relation.get("source_doc", "")
                    }
                )
    
    def _generate_entity_id(self, text: str, entity_type: str) -> str:
        """
        生成实体唯一ID
        
        Args:
            text: 实体文本
            entity_type: 实体类型
            
        Returns:
            实体ID
        """
        # 使用哈希生成唯一ID
        hash_input = f"{entity_type}:{text}"
        hash_hex = hashlib.md5(hash_input.encode()).hexdigest()
        return f"{entity_type}_{hash_hex[:8]}"
```

### 3.3 图谱可视化

```python
from pyvis.network import Network
import networkx as nx
from typing import List, Dict

class KnowledgeGraphVisualizer:
    """知识图谱可视化器"""
    
    def __init__(self, neo4j_manager: Neo4jManager):
        """
        初始化
        
        Args:
            neo4j_manager: Neo4j数据库管理器
        """
        self.neo4j = neo4j_manager
    
    def create_interactive_graph(self, output_path: str = "graph.html",
                                limit: int = 100):
        """
        创建交互式图谱
        
        Args:
            output_path: 输出文件路径
            limit: 节点数量限制
        """
        # 创建网络图
        net = Network(height="750px", width="100%", 
                      bgcolor="#222222", font_color="white")
        
        # 查询节点和关系
        query = f"""
        MATCH (n)-[r]->(m)
        RETURN n, r, m
        LIMIT {limit}
        """
        
        result = self.neo4j.execute_query(query)
        
        # 添加节点和边
        added_nodes = set()
        
        for record in result:
            source = record["n"]
            target = record["m"]
            relation = record["r"]
            
            # 添加源节点
            if source.element_id not in added_nodes:
                label = source.get("name", source.get("id", ""))
                node_type = list(source.labels)[0] if source.labels else "Node"
                
                net.add_node(
                    source.element_id,
                    label=label,
                    title=f"{node_type}: {label}",
                    group=node_type,
                    size=15
                )
                added_nodes.add(source.element_id)
            
            # 添加目标节点
            if target.element_id not in added_nodes:
                label = target.get("name", target.get("id", ""))
                node_type = list(target.labels)[0] if target.labels else "Node"
                
                net.add_node(
                    target.element_id,
                    label=label,
                    title=f"{node_type}: {label}",
                    group=node_type,
                    size=15
                )
                added_nodes.add(target.element_id)
            
            # 添加边
            net.add_edge(
                source.element_id,
                target.element_id,
                label=type(relation).__name__,
                title=f"{type(relation).__name__}"
            )
        
        # 设置物理布局
        net.set_options("""
        {
          "physics": {
            "enabled": true,
            "barnesHut": {
              "gravitationalConstant": -8000,
              "centralGravity": 0.3,
              "springLength": 95,
              "springConstant": 0.04,
              "damping": 0.09,
              "avoidOverlap": 0
            },
            "maxVelocity": 50,
            "minVelocity": 0.1,
            "solver": "barnesHut",
            "timestep": 0.5,
            "stabilization": {
              "enabled": true,
              "iterations": 1000,
              "updateInterval": 50,
              "onlyDynamicEdges": false,
              "fit": true
            }
          }
        }
        """)
        
        # 保存
        net.save_graph(output_path)
        print(f"图谱已保存到: {output_path}")
    
    def create_static_visualization(self, output_path: str = "graph.png",
                                    layout: str = "spring"):
        """
        创建静态可视化
        
        Args:
            output_path: 输出文件路径
            layout: 布局算法（spring, circular, kamada_kawai, random）
        """
        import matplotlib.pyplot as plt
        
        # 创建NetworkX图
        G = nx.Graph()
        
        # 查询数据
        query = """
        MATCH (n)-[r]->(m)
        RETURN n, r, m
        LIMIT 50
        """
        
        result = self.neo4j.execute_query(query)
        
        # 添加节点和边
        for record in result:
            source = record["n"]
            target = record["m"]
            
            source_id = source.get("name", source.element_id)
            target_id = target.get("name", target.element_id)
            
            G.add_node(source_id, 
                       label=list(source.labels)[0] if source.labels else "Node")
            G.add_node(target_id,
                       label=list(target.labels)[0] if target.labels else "Node")
            G.add_edge(source_id, target_id)
        
        # 选择布局
        if layout == "spring":
            pos = nx.spring_layout(G)
        elif layout == "circular":
            pos = nx.circular_layout(G)
        elif layout == "kamada_kawai":
            pos = nx.kamada_kawai_layout(G)
        else:
            pos = nx.random_layout(G)
        
        # 绘制
        plt.figure(figsize=(12, 8))
        
        # 节点颜色
        node_colors = [G.nodes[n].get("label", "Node") for n in G.nodes()]
        color_map = plt.cm.tab20
        
        # 绘制节点
        nx.draw_networkx_nodes(G, pos, node_size=500,
                              node_color=[color_map(i % 20) 
                                        for i in range(len(G.nodes()))])
        
        # 绘制边
        nx.draw_networkx_edges(G, pos, alpha=0.5)
        
        # 绘制标签
        nx.draw_networkx_labels(G, pos, font_size=8, font_family='sans-serif')
        
        plt.title("Knowledge Graph Visualization")
        plt.axis('off')
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"静态图谱已保存到: {output_path}")
```

---

## 知识推理和应用

### 4.1 知识推理

```python
from typing import List, Dict, Any

class KnowledgeReasoner:
    """知识推理器"""
    
    def __init__(self, neo4j_manager: Neo4jManager):
        """
        初始化
        
        Args:
            neo4j_manager: Neo4j数据库管理器
        """
        self.neo4j = neo4j_manager
    
    def infer_missing_relations(self, entity_id: str, 
                                max_hops: int = 2) -> List[Dict]:
        """
        推断缺失的关系
        
        Args:
            entity_id: 实体ID
            max_hops: 最大跳数
            
        Returns:
            推断的关系
        """
        inferred_relations = []
        
        # 查询实体的邻居
        query = f"""
        MATCH (start {{id: $entity_id}})-[r*1..{max_hops}]-(end)
        RETURN DISTINCT end, r
        """
        
        result = self.neo4j.execute_query(query, {"entity_id": entity_id})
        
        # 分析路径，寻找潜在关系
        for record in result:
            end_node = record["end"]
            path = record["r"]
            
            # 如果路径长度大于1，推断潜在关系
            if len(path) > 1:
                inferred_type = self._infer_relation_from_path(path)
                inferred_relations.append({
                    "source": entity_id,
                    "target": end_node.get("id", ""),
                    "type": inferred_type,
                    "confidence": 0.6,
                    "reasoning": "基于路径推断"
                })
        
        return inferred_relations
    
    def _infer_relation_from_path(self, path) -> str:
        """
        从路径推断关系类型
        
        Args:
            path: 路径
            
        Returns:
            推断的关系类型
        """
        # 简单的基于传递性的推断
        relation_types = [type(rel).__name__ for rel in path]
        
        # 如果路径中包含同一关系类型多次，可能是传递关系
        if len(set(relation_types)) == 1:
            return f"INFERRED_{relation_types[0]}"
        
        return "RELATED_TO"
    
    def find_communities(self) -> List[Dict]:
        """
        发现社区
        
        Returns:
            社区列表
        """
        query = """
        CALL gds.nodeSimilarity.stream('myGraph')
        YIELD node1, node2, similarity
        WHERE similarity > 0.8
        RETURN gds.util.asNode(node1).name AS node1,
               gds.util.asNode(node2).name AS node2,
               similarity
        ORDER BY similarity DESC
        LIMIT 100
        """
        
        try:
            result = self.neo4j.execute_query(query)
            communities = self._group_by_community(result)
            return communities
        except:
            # 如果GDS插件不可用，使用简单聚类
            return self._simple_clustering()
    
    def _group_by_community(self, similarities: List[Dict]) -> List[Dict]:
        """基于相似度分组"""
        # 这里简化处理，实际应使用图聚类算法
        communities = []
        visited = set()
        
        for item in similarities:
            node1 = item["node1"]
            node2 = item["node2"]
            
            if node1 not in visited and node2 not in visited:
                community = {"members": [node1, node2], "similarity": item["similarity"]}
                communities.append(community)
                visited.update([node1, node2])
        
        return communities
    
    def _simple_clustering(self) -> List[Dict]:
        """简单聚类"""
        query = """
        MATCH (n)-[r]-(m)
        WITH n, collect(DISTINCT m) as neighbors
        RETURN n.name as node, neighbors
        ORDER BY size(neighbors) DESC
        LIMIT 50
        """
        
        result = self.neo4j.execute_query(query)
        
        communities = []
        for i, item in enumerate(result):
            communities.append({
                "id": i,
                "center": item["node"],
                "members": [item["node"]] + item["neighbors"][:5]
            })
        
        return communities
    
    def find_central_entities(self, limit: int = 10) -> List[Dict]:
        """
        查找中心实体（基于度中心性）
        
        Args:
            limit: 返回数量限制
            
        Returns:
            中心实体列表
        """
        query = f"""
        MATCH (n)-[r]-(m)
        WITH n, count(r) as degree
        RETURN n.name as name, labels(n) as labels, degree
        ORDER BY degree DESC
        LIMIT {limit}
        """
        
        result = self.neo4j.execute_query(query)
        return result
    
    def knowledge_completion(self, entity_id: str, 
                           relation_type: str = None) -> List[Dict]:
        """
        知识补全：给定实体和关系类型，寻找缺失的目标实体
        
        Args:
            entity_id: 实体ID
            relation_type: 关系类型（可选）
            
        Returns:
            补全结果
        """
        if relation_type:
            query = """
            MATCH (n {id: $entity_id})
            CALL {
                WITH n
                MATCH (n)-[r:RELATION_TYPE]->(m)
                WHERE r.confidence > 0.5
                RETURN m, r.confidence as confidence
            }
            RETURN m.name as name, labels(m) as labels, confidence
            ORDER BY confidence DESC
            LIMIT 10
            """.replace("RELATION_TYPE", relation_type)
        else:
            query = """
            MATCH (n {id: $entity_id})-[r]->(m)
            RETURN m.name as name, labels(m) as labels, 
                   type(r) as relation, r.confidence as confidence
            ORDER BY confidence DESC
            LIMIT 10
            """
        
        result = self.neo4j.execute_query(query, {"entity_id": entity_id})
        return result
```

### 4.2 智能问答

```python
from typing import List, Dict, Optional
import re

class KnowledgeQA:
    """基于知识图谱的问答系统"""
    
    def __init__(self, neo4j_manager: Neo4jManager):
        """
        初始化
        
        Args:
            neo4j_manager: Neo4j数据库管理器
        """
        self.neo4j = neo4j_manager
        
        # 问题模式映射
        self.question_patterns = {
            r"(.+?)是谁$": "what_is",
            r"(.+?)是什么$": "what_is",
            r"(.+?)在哪里$": "where_is",
            r"(.+?)在哪里工作$": "works_where",
            r"(.+?)创建了(.+?)$": "who_created",
            r"(.+?)使用什么技术$": "what_tech"
        }
    
    def answer(self, question: str) -> Dict:
        """
        回答问题
        
        Args:
            question: 问题
            
        Returns:
            回答结果
        """
        # 识别问题类型
        question_type, entities = self._parse_question(question)
        
        if question_type == "what_is":
            return self._answer_what_is(entities[0] if entities else None)
        elif question_type == "where_is":
            return self._answer_where_is(entities[0] if entities else None)
        elif question_type == "works_where":
            return self._answer_works_where(entities[0] if entities else None)
        elif question_type == "who_created":
            return self._answer_who_created(entities)
        elif question_type == "what_tech":
            return self._answer_what_tech(entities[0] if entities else None)
        else:
            return self._answer_general(question)
    
    def _parse_question(self, question: str) -> tuple:
        """
        解析问题
        
        Args:
            question: 问题
            
        Returns:
            (问题类型, 实体列表)
        """
        for pattern, qtype in self.question_patterns.items():
            match = re.match(pattern, question)
            if match:
                entities = [g for g in match.groups() if g]
                return qtype, entities
        
        return "general", []
    
    def _answer_what_is(self, entity_name: str) -> Dict:
        """回答"是什么"类问题"""
        if not entity_name:
            return {"answer": "请提供实体名称", "confidence": 0.0}
        
        # 查找实体
        node = self.neo4j.find_node_by_name(entity_name)
        
        if not node:
            return {
                "answer": f"未找到实体: {entity_name}",
                "confidence": 0.0
            }
        
        # 获取实体的属性和关系
        properties = {k: v for k, v in node.items() 
                     if k not in ["element_id", "labels"]}
        
        # 获取相关实体
        query = """
        MATCH (n {id: $entity_id})-[r]-(m)
        RETURN m.name as related_name, type(r) as relation
        LIMIT 10
        """
        
        relations = self.neo4j.execute_query(query, {
            "entity_id": node.get("id", "")
        })
        
        answer = f"{entity_name} 是一个 {', '.join(node.labels)}"
        if properties:
            answer += f"，属性包括: {', '.join([f'{k}: {v}' for k, v in properties.items()])}"
        
        if relations:
            related = [f"{r['relation']} {r['related_name']}" for r in relations]
            answer += f"，相关实体: {', '.join(related)}"
        
        return {
            "answer": answer,
            "confidence": 0.8,
            "entity": entity_name,
            "type": node.labels,
            "properties": properties,
            "relations": relations
        }
    
    def _answer_where_is(self, entity_name: str) -> Dict:
        """回答"在哪里"类问题"""
        if not entity_name:
            return {"answer": "请提供实体名称", "confidence": 0.0}
        
        # 查找位置关系
        query = """
        MATCH (n {name: $entity_name})-[r:LOCATED_IN|LOCATED_AT]-(m:Location)
        RETURN m.name as location
        """
        
        result = self.neo4j.execute_query(query, {"entity_name": entity_name})
        
        if result:
            locations = [r["location"] for r in result]
            answer = f"{entity_name} 位于 {', '.join(locations)}"
            return {"answer": answer, "confidence": 0.8}
        else:
            return {
                "answer": f"未找到 {entity_name} 的位置信息",
                "confidence": 0.0
            }
    
    def _answer_works_where(self, person_name: str) -> Dict:
        """回答"在哪里工作"类问题"""
        if not person_name:
            return {"answer": "请提供人名", "confidence": 0.0}
        
        # 查找工作关系
        query = """
        MATCH (p:Person {name: $person_name})-[r:WORKS_FOR]->(o:Organization)
        RETURN o.name as organization
        """
        
        result = self.neo4j.execute_query(query, {"person_name": person_name})
        
        if result:
            organizations = [r["organization"] for r in result]
            answer = f"{person_name} 在 {', '.join(organizations)} 工作"
            return {"answer": answer, "confidence": 0.8}
        else:
            return {
                "answer": f"未找到 {person_name} 的工作信息",
                "confidence": 0.0
            }
    
    def _answer_who_created(self, entities: List[str]) -> Dict:
        """回答"谁创建了"类问题"""
        if len(entities) < 2:
            return {"answer": "请提供完整的查询", "confidence": 0.0}
        
        target = entities[1]
        
        # 查找创建关系
        query = """
        MATCH (c)-[r:CREATED_BY]->(t {name: $target})
        RETURN c.name as creator
        """
        
        result = self.neo4j.execute_query(query, {"target": target})
        
        if result:
            creators = [r["creator"] for r in result]
            answer = f"{', '.join(creators)} 创建了 {target}"
            return {"answer": answer, "confidence": 0.8}
        else:
            return {
                "answer": f"未找到 {target} 的创建者信息",
                "confidence": 0.0
            }
    
    def _answer_what_tech(self, entity_name: str) -> Dict:
        """回答"使用什么技术"类问题"""
        if not entity_name:
            return {"answer": "请提供实体名称", "confidence": 0.0}
        
        # 查找技术关系
        query = """
        MATCH (e {name: $entity_name})-[r:USE_TECHNOLOGY]->(t:Technology)
        RETURN t.name as technology
        """
        
        result = self.neo4j.execute_query(query, {"entity_name": entity_name})
        
        if result:
            technologies = [r["technology"] for r in result]
            answer = f"{entity_name} 使用了 {', '.join(technologies)}"
            return {"answer": answer, "confidence": 0.8}
        else:
            return {
                "answer": f"未找到 {entity_name} 使用的技术信息",
                "confidence": 0.0
            }
    
    def _answer_general(self, question: str) -> Dict:
        """回答一般问题（使用全文搜索）"""
        # 提取关键词
        keywords = self._extract_keywords(question)
        
        if not keywords:
            return {
                "answer": "无法理解您的问题",
                "confidence": 0.0
            }
        
        # 全文搜索
        results = self.neo4j.fulltext_search(" ".join(keywords), limit=5)
        
        if results:
            entities = [r["name"] for r in results]
            answer = f"找到相关实体: {', '.join(entities)}"
            return {
                "answer": answer,
                "confidence": 0.6,
                "results": results
            }
        else:
            return {
                "answer": "未找到相关信息",
                "confidence": 0.0
            }
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 简单实现：移除停用词
        stopwords = {"是", "什么", "哪里", "谁", "怎么", "为什么", "的", "了", "在"}
        keywords = []
        
        for word in text.split():
            if word not in stopwords and len(word) > 1:
                keywords.append(word)
        
        return keywords
```

### 4.3 知识检索

```python
from typing import List, Dict, Tuple
import math

class KnowledgeRetriever:
    """知识检索器"""
    
    def __init__(self, neo4j_manager: Neo4jManager):
        """
        初始化
        
        Args:
            neo4j_manager: Neo4j数据库管理器
        """
        self.neo4j = neo4j_manager
    
    def search_by_entity(self, entity_name: str) -> Dict:
        """
        按实体搜索
        
        Args:
            entity_name: 实体名称
            
        Returns:
            搜索结果
        """
        node = self.neo4j.find_node_by_name(entity_name)
        
        if not node:
            return {
                "found": False,
                "message": f"未找到实体: {entity_name}"
            }
        
        # 获取相关实体和关系
        query = """
        MATCH (n {id: $entity_id})-[r]-(m)
        RETURN m.name as related_name, type(r) as relation,
               labels(m) as labels
        """
        
        relations = self.neo4j.execute_query(query, {
            "entity_id": node.get("id", "")
        })
        
        return {
            "found": True,
            "entity": {
                "name": node.get("name", ""),
                "labels": list(node.labels),
                "properties": {k: v for k, v in node.items() 
                            if k not in ["element_id", "labels"]}
            },
            "relations": relations
        }
    
    def search_by_relation(self, relation_type: str, 
                          limit: int = 20) -> List[Dict]:
        """
        按关系类型搜索
        
        Args:
            relation_type: 关系类型
            limit: 返回数量限制
            
        Returns:
            关系列表
        """
        query = f"""
        MATCH (n)-[r:{relation_type}]->(m)
        RETURN n.name as source, m.name as target, r.confidence as confidence
        ORDER BY r.confidence DESC
        LIMIT {limit}
        """
        
        result = self.neo4j.execute_query(query)
        return result
    
    def path_search(self, source: str, target: str) -> Dict:
        """
        路径搜索
        
        Args:
            source: 源实体名称
            target: 目标实体名称
            
        Returns:
            路径信息
        """
        source_node = self.neo4j.find_node_by_name(source)
        target_node = self.neo4j.find_node_by_name(target)
        
        if not source_node or not target_node:
            return {
                "found": False,
                "message": "未找到源或目标实体"
            }
        
        # 查找最短路径
        result = self.neo4j.find_shortest_path(
            source_node.get("id", ""),
            target_node.get("id", "")
        )
        
        if result:
            path = result[0]["path"]
            nodes = [node for node in path.nodes]
            relationships = [rel for rel in path.relationships]
            
            return {
                "found": True,
                "path_length": len(relationships),
                "nodes": [{"name": n.get("name", ""), 
                          "labels": list(n.labels)} for n in nodes],
                "relationships": [type(r).__name__ for r in relationships]
            }
        else:
            return {
                "found": False,
                "message": "未找到路径"
            }
    
    def similarity_search(self, entity_name: str, 
                         top_k: int = 5) -> List[Dict]:
        """
        相似性搜索（基于共享关系）
        
        Args:
            entity_name: 实体名称
            top_k: 返回数量
            
        Returns:
            相似实体列表
        """
        query = """
        MATCH (n {name: $entity_name})-[r1]-(m)-[r2]-(similar)
        WHERE similar.name <> $entity_name
        WITH similar, count(DISTINCT r1) as shared_relations
        RETURN similar.name as name, labels(similar) as labels, 
               shared_relations
        ORDER BY shared_relations DESC
        LIMIT $top_k
        """
        
        result = self.neo4j.execute_query(query, {
            "entity_name": entity_name,
            "top_k": top_k
        })
        
        return result
```

---

## 实际案例：openclaw-memory知识图谱

### 案例概述

我们将使用 openclaw-memory 项目作为实际案例，从其文档中自动构建知识图谱。这个项目包含了大量关于 AI Agent、知识库、自动化等内容的技术文档。

### 5.1 数据收集和预处理

```python
import os
from pathlib import Path
from typing import List, Dict
import json

class OpenClawMemoryDataset:
    """openclaw-memory数据集处理器"""
    
    def __init__(self, base_path: str):
        """
        初始化
        
        Args:
            base_path: 项目根目录
        """
        self.base_path = Path(base_path)
        self.documents = []
    
    def load_documents(self) -> List[Dict]:
        """
        加载所有Markdown文档
        
        Returns:
            文档列表
        """
        # 查找所有.md文件
        md_files = list(self.base_path.rglob("*.md"))
        
        print(f"找到 {len(md_files)} 个Markdown文件")
        
        for md_file in md_files:
            # 跳过隐藏文件和某些特殊文件
            if md_file.name.startswith(".") or "node_modules" in str(md_file):
                continue
            
            doc = self._parse_markdown(md_file)
            if doc:
                self.documents.append(doc)
        
        print(f"成功加载 {len(self.documents)} 个文档")
        return self.documents
    
    def _parse_markdown(self, file_path: Path) -> Dict:
        """
        解析Markdown文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            文档字典
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 提取标题
            title = self._extract_title(content)
            
            # 提取章节结构
            sections = self._extract_sections(content)
            
            return {
                "file_path": str(file_path.relative_to(self.base_path)),
                "title": title,
                "content": content,
                "sections": sections,
                "metadata": {
                    "file_size": len(content),
                    "section_count": len(sections)
                }
            }
        
        except Exception as e:
            print(f"解析文件失败 {file_path}: {e}")
            return None
    
    def _extract_title(self, content: str) -> str:
        """提取文档标题"""
        lines = content.split('\n')
        for line in lines[:10]:  # 只在前10行查找
            line = line.strip()
            if line.startswith('#'):
                # 移除#号和空格
                return re.sub(r'^#+\s*', '', line)
        
        return "Untitled"
    
    def _extract_sections(self, content: str) -> List[Dict]:
        """提取章节"""
        sections = []
        lines = content.split('\n')
        
        current_section = {
            "title": "Introduction",
            "level": 0,
            "content": []
        }
        
        for line in lines:
            # 检测标题
            if line.strip().startswith('#'):
                # 保存当前章节
                if current_section["content"]:
                    sections.append(current_section.copy())
                
                # 创建新章节
                level = len(line) - len(line.lstrip('#'))
                title = line.lstrip('#').strip()
                
                current_section = {
                    "title": title,
                    "level": level,
                    "content": []
                }
            else:
                if line.strip():
                    current_section["content"].append(line)
        
        # 添加最后一个章节
        if current_section["content"]:
            sections.append(current_section)
        
        return sections
    
    def get_statistics(self) -> Dict:
        """
        获取数据集统计信息
        
        Returns:
            统计信息
        """
        total_chars = sum(len(doc["content"]) for doc in self.documents)
        total_sections = sum(doc["metadata"]["section_count"] for doc in self.documents)
        
        return {
            "document_count": len(self.documents),
            "total_characters": total_chars,
            "total_sections": total_sections,
            "avg_doc_length": total_chars / len(self.documents) if self.documents else 0,
            "avg_sections": total_sections / len(self.documents) if self.documents else 0
        }
```

### 5.2 构建知识图谱

```python
import hashlib
import json

class OpenClawMemoryKGBuilder:
    """openclaw-memory知识图谱构建器"""
    
    def __init__(self, neo4j_manager: Neo4jManager):
        """
        初始化
        
        Args:
            neo4j_manager: Neo4j数据库管理器
        """
        self.neo4j = neo4j_manager
        self.entity_extractor = EntityExtractor()
        self.relation_extractor = RelationExtractor()
        self.kg_builder = KnowledgeGraphBuilder(neo4j_manager)
    
    def build(self, documents: List[Dict]):
        """
        从文档构建知识图谱
        
        Args:
            documents: 文档列表
        """
        print("开始构建知识图谱...")
        
        # 处理每个文档
        processed_docs = []
        for i, doc in enumerate(documents):
            print(f"处理文档 {i+1}/{len(documents)}: {doc['title']}")
            
            # 提取实体
            entities = self.entity_extractor.extract(doc["content"])
            
            # 提取关系
            relations = self.relation_extractor.extract(doc["content"], entities)
            
            processed_doc = {
                "title": doc["title"],
                "text": doc["content"],
                "metadata": doc["metadata"],
                "entities": entities,
                "relations": relations,
                "file_path": doc["file_path"]
            }
            
            processed_docs.append(processed_doc)
        
        # 构建知识图谱
        print("构建图数据库...")
        self.kg_builder.build_from_documents(processed_docs)
        
        print(f"知识图谱构建完成！处理了 {len(processed_docs)} 个文档")
        
        return processed_docs
    
    def build_topic_graph(self, documents: List[Dict]):
        """
        构建主题图
        
        Args:
            documents: 文档列表
        """
        print("构建主题图...")
        
        # 提取主题（文档标题）
        topics = []
        for i, doc in enumerate(documents):
            topic = {
                "label": "Topic",
                "properties": {
                    "id": f"topic_{i}",
                    "name": doc["title"],
                    "file_path": doc["file_path"]
                }
            }
            topics.append(topic)
        
        self.neo4j.batch_add_nodes(topics)
        
        # 提取关键词作为子主题
        keyword_map = {}
        for doc in documents:
            for section in doc.get("sections", []):
                keywords = self._extract_keywords_from_section(section)
                for keyword in keywords:
                    if keyword not in keyword_map:
                        keyword_map[keyword] = []
                    keyword_map[keyword].append(doc["title"])
        
        # 创建关键词节点和关系
        keyword_nodes = []
        for i, (keyword, doc_titles) in enumerate(keyword_map.items()):
            if len(keyword) > 2:  # 过滤太短的关键词
                node = {
                    "label": "Keyword",
                    "properties": {
                        "id": f"keyword_{i}",
                        "name": keyword,
                        "frequency": len(doc_titles)
                    }
                }
                keyword_nodes.append(node)
        
        self.neo4j.batch_add_nodes(keyword_nodes)
        
        print("主题图构建完成！")
    
    def _extract_keywords_from_section(self, section: Dict) -> List[str]:
        """从章节中提取关键词"""
        text = " ".join(section["content"])
        
        # 简单的关键词提取
        keywords = []
        for word in text.split():
            word = word.strip()
            if len(word) > 2 and word.isalpha():
                keywords.append(word)
        
        # 去重
        return list(set(keywords))
```

### 5.3 实际应用场景

#### 场景1：技术知识查询

```python
# 查询"AI Agent"相关信息
qa = KnowledgeQA(neo4j_manager)
answer = qa.answer("AI Agent是什么")
print(answer["answer"])

# 查询"LangGraph"的使用技术
answer = qa.answer("LangGraph使用什么技术")
print(answer["answer"])
```

#### 场景2：技术栈推荐

```python
# 基于知识图谱推荐技术栈
def recommend_tech_stack(project_type: str, neo4j_manager: Neo4jManager):
    """推荐技术栈"""
    query = """
    MATCH (d:Document)-[r:CONTAINS]->(t:Technology)
    WHERE d.title CONTAINS $project_type
    RETURN DISTINCT t.name as technology, 
           count(d) as usage_count
    ORDER BY usage_count DESC
    LIMIT 10
    """
    
    result = neo4j_manager.execute_query(query, {
        "project_type": project_type
    })
    
    print(f"推荐 {project_type} 相关技术栈:")
    for item in result:
        print(f"- {item['technology']} (使用次数: {item['usage_count']})")

recommend_tech_stack("AI Agent", neo4j_manager)
```

#### 场景3：学习路径推荐

```python
def recommend_learning_path(topic: str, neo4j_manager: Neo4jManager):
    """推荐学习路径"""
    query = """
    MATCH (t1:Topic {name: $topic})-[r:RELATED_TO*1..3]-(t2:Topic)
    RETURN DISTINCT t2.name as topic, 
           length(r) as distance
    ORDER BY distance
    LIMIT 20
    """
    
    result = neo4j_manager.execute_query(query, {"topic": topic})
    
    print(f"推荐 {topic} 学习路径:")
    current_distance = 0
    for item in result:
        if item["distance"] > current_distance:
            current_distance = item["distance"]
            print(f"\n阶段 {current_distance}:")
        print(f"- {item['topic']}")
```

---

## 性能评估和优化

### 6.1 性能指标

#### 抽取质量指标

1. **精确率 (Precision)**
   ```python
   def calculate_precision(extracted_entities, ground_truth):
       """计算精确率"""
       true_positives = len(set(extracted_entities) & set(ground_truth))
       predicted_positives = len(extracted_entities)
       return true_positives / predicted_positives if predicted_positives > 0 else 0
   ```

2. **召回率 (Recall)**
   ```python
   def calculate_recall(extracted_entities, ground_truth):
       """计算召回率"""
       true_positives = len(set(extracted_entities) & set(ground_truth))
       actual_positives = len(ground_truth)
       return true_positives / actual_positives if actual_positives > 0 else 0
   ```

3. **F1分数 (F1 Score)**
   ```python
   def calculate_f1_score(precision, recall):
       """计算F1分数"""
       if precision + recall == 0:
           return 0
       return 2 * (precision * recall) / (precision + recall)
   ```

#### 图谱性能指标

1. **查询响应时间**
   ```python
   import time
   
   def measure_query_time(neo4j_manager, query, parameters=None):
       """测量查询时间"""
       start_time = time.time()
       result = neo4j_manager.execute_query(query, parameters)
       end_time = time.time()
       
       return {
           "response_time": end_time - start_time,
           "result_count": len(result)
       }
   ```

2. **索引效率**
   ```python
   def check_index_efficiency(neo4j_manager):
       """检查索引效率"""
       query = """
       CALL apoc.cypher.runTime(
         "MATCH (n:Person {name: 'Alice'}) RETURN n",
         {}
       )
       YIELD time
       RETURN time
       """
       
       result = neo4j_manager.execute_query(query)
       return result[0]["time"] if result else None
   ```

### 6.2 优化策略

#### 数据库优化

1. **索引优化**
   ```python
   def optimize_indexes(neo4j_manager):
       """优化索引"""
       # 创建复合索引
       query = """
       CREATE INDEX entity_name_type 
       IF NOT EXISTS 
       FOR (n:Entity) 
       ON (n.name, n.type)
       """
       neo4j_manager.execute_query(query)
       
       # 创建关系索引
       query = """
       CREATE INDEX relation_confidence 
       IF NOT EXISTS 
       FOR ()-[r:RELATED_TO]->() 
       ON (r.confidence)
       """
       neo4j_manager.execute_query(query)
   ```

2. **查询优化**
   ```python
   def optimize_query(query: str) -> str:
       """优化查询"""
       # 添加查询提示
       optimized = query.replace("MATCH", "MATCH /*+ INDEX(n:Entity name) */")
       
       # 使用EXPLAIN分析查询计划
       explain_query = f"EXPLAIN {optimized}"
       
       return optimized
   ```

3. **批量操作优化**
   ```python
   def optimized_batch_import(neo4j_manager, nodes: List[Dict], 
                             batch_size: int = 1000):
       """优化的批量导入"""
       # 分批处理
       for i in range(0, len(nodes), batch_size):
           batch = nodes[i:i + batch_size]
           neo4j_manager.batch_add_nodes(batch)
           print(f"已导入 {i + len(batch)}/{len(nodes)} 个节点")
   ```

#### NLP 模型优化

1. **模型选择优化**
   ```python
   class OptimizedEntityExtractor:
       """优化的实体提取器"""
       
       def __init__(self):
           # 根据任务选择合适的模型
           self.light_model = spacy.load("zh_core_web_sm")
           self.heavy_model = spacy.load("zh_core_web_lg")
       
       def extract(self, text: str, use_fast: bool = True):
           """提取实体"""
           if use_fast or len(text) < 500:
               # 使用轻量级模型
               return self._extract_with_model(self.light_model, text)
           else:
               # 使用高质量模型
               return self._extract_with_model(self.heavy_model, text)
       
       def _extract_with_model(self, model, text: str):
           """使用指定模型提取"""
           doc = model(text)
           entities = [
               {
                   "text": ent.text,
                   "label": ent.label_,
                   "confidence": ent._.confidence if hasattr(ent._, "confidence") else 0.8
               }
               for ent in doc.ents
           ]
           return entities
   ```

2. **缓存优化**
   ```python
   from functools import lru_cache
   
   class CachedEntityExtractor:
       """带缓存的实体提取器"""
       
       def __init__(self):
           self.extractor = EntityExtractor()
       
       @lru_cache(maxsize=1000)
       def extract(self, text_hash: str, text: str) -> List[Dict]:
           """提取实体（带缓存）"""
           return self.extractor.extract(text)
       
       def extract_with_cache(self, text: str) -> List[Dict]:
           """提取实体并使用缓存"""
           text_hash = hashlib.md5(text.encode()).hexdigest()
           return self.extract(text_hash, text)
   ```

#### 内存优化

1. **流式处理**
   ```python
   def stream_process_documents(file_path: str, batch_size: int = 100):
       """流式处理文档"""
       with open(file_path, 'r', encoding='utf-8') as f:
           batch = []
           for line in f:
               doc = json.loads(line)
               batch.append(doc)
               
               if len(batch) >= batch_size:
                   # 处理批次
                   process_batch(batch)
                   batch = []
           
           # 处理剩余文档
           if batch:
               process_batch(batch)
   ```

2. **内存池管理**
   ```python
   import gc
   
   class MemoryAwareProcessor:
       """内存感知处理器"""
       
       def __init__(self, max_memory_gb: int = 4):
           self.max_memory = max_memory_gb * 1024 ** 3
       
       def check_memory(self):
           """检查内存使用"""
           import psutil
           process = psutil.Process()
           mem_info = process.memory_info()
           return mem_info.rss
       
       def process_with_memory_check(self, data: List):
           """带内存检查的处理"""
           for i, item in enumerate(data):
               self.process_item(item)
               
               # 定期检查内存
               if i % 100 == 0:
                   if self.check_memory() > self.max_memory:
                       print("内存接近上限，执行垃圾回收")
                       gc.collect()
   ```

### 6.3 性能基准测试

```python
import time
import statistics
from typing import List

class PerformanceBenchmark:
    """性能基准测试"""
    
    def __init__(self, neo4j_manager, entity_extractor):
        self.neo4j = neo4j_manager
        self.extractor = entity_extractor
        self.results = {}
    
    def benchmark_entity_extraction(self, texts: List[str], 
                                    iterations: int = 10):
        """基准测试实体提取"""
        times = []
        
        for i in range(iterations):
            start = time.time()
            for text in texts:
                self.extractor.extract(text)
            end = time.time()
            times.append(end - start)
        
        self.results["entity_extraction"] = {
            "mean_time": statistics.mean(times),
            "std_time": statistics.stdev(times) if len(times) > 1 else 0,
            "min_time": min(times),
            "max_time": max(times),
            "throughput": len(texts) / statistics.mean(times)
        }
        
        return self.results["entity_extraction"]
    
    def benchmark_query_performance(self, queries: List[Dict]):
        """基准测试查询性能"""
        results = []
        
        for query_info in queries:
            times = []
            for _ in range(10):
                start = time.time()
                result = self.neo4j.execute_query(
                    query_info["query"],
                    query_info.get("parameters", {})
                )
                end = time.time()
                times.append(end - start)
            
            results.append({
                "query": query_info["name"],
                "mean_time": statistics.mean(times),
                "result_count": len(result)
            })
        
        self.results["query_performance"] = results
        return results
    
    def generate_report(self):
        """生成性能报告"""
        report = []
        
        report.append("=== 性能基准测试报告 ===\n")
        
        if "entity_extraction" in self.results:
            report.append("## 实体提取性能")
            report.append(f"- 平均时间: {self.results['entity_extraction']['mean_time']:.4f}s")
            report.append(f"- 吞吐量: {self.results['entity_extraction']['throughput']:.2f} docs/s\n")
        
        if "query_performance" in self.results:
            report.append("## 查询性能")
            for q in self.results["query_performance"]:
                report.append(f"- {q['query']}: {q['mean_time']:.4f}s ({q['result_count']} results)")
        
        return "\n".join(report)
```

---

## 完整代码实现

### 7.1 主程序

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
自动化知识图谱构建系统
从非结构化文档自动构建知识图谱
"""

import os
import sys
import argparse
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from document_processing import PDFParser, WordParser, TextCleaner
from nlp_extraction import EntityExtractor, RelationExtractor
from knowledge_graph import Neo4jManager, KnowledgeGraphBuilder, KnowledgeQA
from visualization import KnowledgeGraphVisualizer
from openclaw_memory_case import OpenClawMemoryDataset, OpenClawMemoryKGBuilder


class KnowledgeGraphSystem:
    """知识图谱构建系统"""
    
    def __init__(self, config: Dict):
        """
        初始化系统
        
        Args:
            config: 配置字典
        """
        self.config = config
        
        # 初始化组件
        self.neo4j = Neo4jManager(
            uri=config["neo4j"]["uri"],
            user=config["neo4j"]["user"],
            password=config["neo4j"]["password"]
        )
        
        self.entity_extractor = EntityExtractor()
        self.relation_extractor = RelationExtractor()
        self.kg_builder = KnowledgeGraphBuilder(self.neo4j)
        self.qa = KnowledgeQA(self.neo4j)
        self.visualizer = KnowledgeGraphVisualizer(self.neo4j)
    
    def initialize(self):
        """初始化系统"""
        print("初始化知识图谱系统...")
        
        # 初始化数据库schema
        self.neo4j.initialize_schema()
        
        print("系统初始化完成！")
    
    def build_from_documents(self, document_paths: List[str]):
        """
        从文档构建知识图谱
        
        Args:
            document_paths: 文档路径列表
        """
        print(f"开始从 {len(document_paths)} 个文档构建知识图谱...")
        
        documents = []
        
        for doc_path in document_paths:
            print(f"处理文档: {doc_path}")
            
            # 解析文档
            doc = self._parse_document(doc_path)
            if doc:
                # 提取实体和关系
                doc["entities"] = self.entity_extractor.extract(doc["text"])
                doc["relations"] = self.relation_extractor.extract(
                    doc["text"],
                    doc["entities"]
                )
                
                documents.append(doc)
        
        # 构建知识图谱
        self.kg_builder.build_from_documents(documents)
        
        print(f"知识图谱构建完成！处理了 {len(documents)} 个文档")
        print(f"- 提取实体: {sum(len(d['entities']) for d in documents)}")
        print(f"- 提取关系: {sum(len(d['relations']) for d in documents)}")
    
    def _parse_document(self, file_path: str) -> Dict:
        """解析文档"""
        ext = Path(file_path).suffix.lower()
        
        if ext == ".pdf":
            parser = PDFParser()
            result = parser.parse(file_path)
            return {
                "file_path": file_path,
                "title": result["metadata"].get("title", Path(file_path).stem),
                "text": result["text"],
                "metadata": result["metadata"]
            }
        
        elif ext == ".docx":
            parser = WordParser()
            result = parser.parse(file_path)
            return {
                "file_path": file_path,
                "title": result["metadata"].get("title", Path(file_path).stem),
                "text": result["text"],
                "metadata": result["metadata"]
            }
        
        elif ext == ".md" or ext == ".txt":
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            return {
                "file_path": file_path,
                "title": Path(file_path).stem,
                "text": text,
                "metadata": {"format": ext[1:]}
            }
        
        else:
            print(f"不支持的文件格式: {ext}")
            return None
    
    def query(self, question: str) -> Dict:
        """
        查询知识图谱
        
        Args:
            question: 问题
            
        Returns:
            回答
        """
        return self.qa.answer(question)
    
    def visualize(self, output_path: str = "graph.html"):
        """
        可视化知识图谱
        
        Args:
            output_path: 输出路径
        """
        self.visualizer.create_interactive_graph(output_path)
    
    def close(self):
        """关闭系统"""
        self.neo4j.close()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="自动化知识图谱构建系统")
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # 构建命令
    build_parser = subparsers.add_parser("build", help="构建知识图谱")
    build_parser.add_argument("--input", "-i", nargs="+", required=True,
                            help="输入文档路径")
    build_parser.add_argument("--output", "-o", default="graph.html",
                            help="可视化输出路径")
    
    # 查询命令
    query_parser = subparsers.add_parser("query", help="查询知识图谱")
    query_parser.add_argument("question", help="问题")
    
    # 可视化命令
    vis_parser = subparsers.add_parser("visualize", help="可视化知识图谱")
    vis_parser.add_argument("--output", "-o", default="graph.html",
                          help="输出路径")
    
    # OpenClaw Memory案例
    case_parser = subparsers.add_parser("openclaw", help="OpenClaw Memory案例")
    case_parser.add_argument("--path", "-p", 
                            default=".",
                            help="OpenClaw Memory项目路径")
    
    args = parser.parse_args()
    
    # 配置
    config = {
        "neo4j": {
            "uri": "bolt://localhost:7687",
            "user": "neo4j",
            "password": "password"  # 请修改为实际密码
        }
    }
    
    # 创建系统
    system = KnowledgeGraphSystem(config)
    system.initialize()
    
    try:
        if args.command == "build":
            system.build_from_documents(args.input)
            system.visualize(args.output)
        
        elif args.command == "query":
            answer = system.query(args.question)
            print(f"问题: {args.question}")
            print(f"回答: {answer['answer']}")
            if "confidence" in answer:
                print(f"置信度: {answer['confidence']}")
        
        elif args.command == "visualize":
            system.visualize(args.output)
        
        elif args.command == "openclaw":
            # OpenClaw Memory案例
            dataset = OpenClawMemoryDataset(args.path)
            documents = dataset.load_documents()
            
            # 统计信息
            stats = dataset.get_statistics()
            print("\n=== 数据集统计 ===")
            for key, value in stats.items():
                print(f"{key}: {value}")
            
            # 构建知识图谱
            builder = OpenClawMemoryKGBuilder(system.neo4j)
            builder.build(documents)
            
            # 可视化
            system.visualize("openclaw_graph.html")
    
    finally:
        system.close()


if __name__ == "__main__":
    main()
```

### 7.2 依赖安装

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 7.3 requirements.txt

```
# NLP和文本处理
spacy>=3.7.0
jieba>=0.42.1
transformers>=4.30.0
torch>=2.0.0

# 图数据库
neo4j>=5.10.0

# 文档解析
PyPDF2>=3.0.0
pdfplumber>=0.9.0
python-docx>=1.1.0
pypandoc>=1.11

# 可视化
pyvis>=0.3.0
networkx>=3.1.0
matplotlib>=3.7.0

# 其他工具
tqdm>=4.65.0
python-dotenv>=1.0.0
```

---

## 部署和运维

### 8.1 Docker部署

#### Dockerfile

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    pandoc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 下载spaCy模型
RUN python -m spacy download zh_core_web_lg

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 7474 7687 8080

# 启动命令
CMD ["python", "main.py", "--help"]
```

#### docker-compose.yml

```yaml
version: '3.8'

services:
  neo4j:
    image: neo4j:5.10.0
    container_name: neo4j
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      NEO4J_AUTH: neo4j/password
      NEO4J_dbms_memory_heap_initial__size: 512m
      NEO4J_dbms_memory_heap_max__size: 512m
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
    networks:
      - kg_network

  knowledge_graph:
    build: .
    container_name: knowledge_graph_app
    ports:
      - "8080:8080"
    environment:
      NEO4J_URI: bolt://neo4j:7687
      NEO4J_USER: neo4j
      NEO4J_PASSWORD: password
    depends_on:
      - neo4j
    volumes:
      - ./data:/app/data
      - ./output:/app/output
    networks:
      - kg_network

volumes:
  neo4j_data:
  neo4j_logs:

networks:
  kg_network:
    driver: bridge
```

### 8.2 监控和日志

#### 日志配置

```python
import logging
from logging.handlers import RotatingFileHandler

def setup_logging(log_level=logging.INFO):
    """配置日志"""
    # 创建日志目录
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 配置根日志器
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # 文件处理器
    file_handler = RotatingFileHandler(
        log_dir / "knowledge_graph.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(log_level)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    
    # 格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger
```

#### 性能监控

```python
import time
import psutil
from typing import Dict

class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.process = psutil.Process()
        self.metrics = []
    
    def record_metric(self, name: str, value: float, unit: str = ""):
        """记录指标"""
        metric = {
            "timestamp": time.time(),
            "name": name,
            "value": value,
            "unit": unit
        }
        self.metrics.append(metric)
    
    def get_system_metrics(self) -> Dict:
        """获取系统指标"""
        return {
            "cpu_percent": self.process.cpu_percent(),
            "memory_mb": self.process.memory_info().rss / 1024 / 1024,
            "memory_percent": self.process.memory_percent(),
            "num_threads": self.process.num_threads()
        }
    
    def export_metrics(self, file_path: str):
        """导出指标"""
        import json
        with open(file_path, 'w') as f:
            json.dump(self.metrics, f, indent=2)
```

### 8.3 备份和恢复

#### 备份脚本

```python
from datetime import datetime
import subprocess

def backup_neo4j(backup_dir: str = "backups"):
    """备份Neo4j数据库"""
    # 创建备份目录
    backup_path = Path(backup_dir)
    backup_path.mkdir(exist_ok=True)
    
    # 生成备份文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_path / f"neo4j_backup_{timestamp}.dump"
    
    # 执行备份
    cmd = [
        "neo4j-admin",
        "database",
        "dump",
        "neo4j",
        "--to-path", str(backup_file.parent),
        "--verbose"
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True)
        print(f"备份成功: {backup_file}")
        return backup_file
    except subprocess.CalledProcessError as e:
        print(f"备份失败: {e}")
        return None
```

#### 恢复脚本

```python
def restore_neo4j(backup_file: str, database: str = "neo4j"):
    """恢复Neo4j数据库"""
    cmd = [
        "neo4j-admin",
        "database",
        "load",
        "neo4j",
        "--from-path", str(backup_file),
        "--verbose"
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True)
        print(f"恢复成功: {backup_file}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"恢复失败: {e}")
        return False
```

---

## 总结

本技术方案提供了一个完整的自动化知识图谱构建系统，涵盖了从非结构化文档到结构化知识图谱的全流程。主要特点包括：

1. **完整的技术栈**：从文档解析、NLP抽取到图数据库存储和可视化
2. **模块化设计**：各组件独立可扩展
3. **实用性强**：提供了完整的Python代码实现和实际案例
4. **性能优化**：包含多种优化策略和性能评估方法
5. **生产就绪**：提供了Docker部署、监控和备份方案

### 下一步改进方向

1. **增强NLP能力**：集成更先进的预训练模型
2. **支持更多文档格式**：如PPT、Excel等
3. **实时更新**：支持增量更新知识图谱
4. **多语言支持**：支持英文、日文等其他语言
5. **协作功能**：支持多人协同标注和编辑

---

**文档版本**: 1.0
**最后更新**: 2026-03-24
**作者**: AI Assistant
