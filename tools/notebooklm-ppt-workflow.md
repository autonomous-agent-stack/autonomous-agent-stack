# NotebookLM PPT 全流程指南

> 从生成到去水印的完整自动化流程

---

## 🎯 流程概览

```
1. 准备内容 → 2. NotebookLM 生成 PPT → 3. 下载 → 4. 自动去水印 → 5. 完成
```

---

## 1️⃣ NotebookLM 生成 PPT 提示词模板

### 基础模板

```
请基于以下内容创建一个完整的 PPT 演示文稿：

【主题】：[你的主题]
【目标受众】：[受众群体]
【幻灯片数量】：[10-20页]
【风格】：[专业/简约/创意]

【内容大纲】：
1. 封面页（标题 + 副标题）
2. 目录页
3. [核心内容 1]
4. [核心内容 2]
5. [核心内容 3]
...
N. 总结页
N+1. Q&A 页

【要求】：
- 每页包含清晰的标题和要点
- 使用图表、列表等可视化元素
- 保持简洁，每页不超过 5-6 个要点
- 包含过渡页和总结页
```

### 进阶模板（带数据）

```
请创建一个数据分析 PPT：

【主题】：[数据主题]
【数据来源】：[描述数据]

【结构】：
1. 封面
2. 数据概览（关键指标）
3. 趋势分析（图表）
4. 对比分析（表格）
5. 洞察发现
6. 建议与行动
7. 附录

【可视化要求】：
- 使用柱状图、折线图、饼图
- 数据表格清晰
- 关键数字突出显示
```

### 教育培训模板

```
请创建一个培训课件 PPT：

【主题】：[培训主题]
【时长】：[X 小时]
【学员水平】：[初学者/中级/高级]

【结构】：
1. 课程目标
2. 知识点 1（理论 + 案例）
3. 知识点 2（理论 + 案例）
4. 实践练习
5. 总结与测验
6. 延伸阅读

【互动元素】：
- 思考题
- 讨论环节
- 实操步骤
```

---

## 2️⃣ NotebookLM 操作步骤

### Step 1: 打开 NotebookLM

访问：https://notebooklm.google.com/

### Step 2: 创建笔记本

1. 点击 **"New notebook"**
2. 上传源材料：
   - 文档（PDF、DOCX、TXT）
   - 网页链接
   - 视频链接
   - 或直接粘贴文本

### Step 3: 生成 PPT

1. 在对话中输入提示词（使用上面的模板）
2. 等待 NotebookLM 生成内容
3. 查看生成的大纲
4. 如需调整，输入修改指令：
   ```
   请增加一页关于 [主题] 的内容
   请将第 3 页改为图表展示
   请简化第 5 页的内容
   ```

### Step 4: 导出 PPT

1. 点击生成内容右上角的 **"..."** 菜单
2. 选择 **"Export to Google Slides"** 或 **"Download as PPTX"**
3. 等待下载完成

**注意**：导出的 PPT 可能包含 NotebookLM 水印

---

## 3️⃣ 自动去水印

### 方法 1：Python 脚本（推荐）

#### 安装依赖

```bash
pip install python-pptx
```

#### 单个文件

```bash
python tools/remove_ppt_watermark.py input.pptx output.pptx
```

#### 批量处理

```bash
# 处理整个文件夹
python tools/remove_ppt_watermark.py --batch ./ppt_folder/

# 输出到指定文件夹
python tools/remove_ppt_watermark.py --batch ./ppt_folder/ --output ./cleaned/
```

### 方法 2：PowerPoint 手动

1. 打开下载的 PPT
2. 视图 → 幻灯片母版
3. 找到水印元素（通常在母版页底部）
4. 删除水印
5. 关闭母版视图
6. 保存

### 方法 3：Google Slides

1. 打开 Google Slides
2. 上传 PPTX 文件
3. 点击 **"幻灯片" → "编辑主题"**
4. 删除水印元素
5. 文件 → 下载 → Microsoft PowerPoint (.pptx)

---

## 4️⃣ 完整自动化流程脚本

### Bash 脚本（一键处理）

```bash
#!/bin/bash
# notebooklm-pipeline.sh
# 用法: ./notebooklm-pipeline.sh <input_folder>

INPUT_DIR=${1:-"./notebooklm_ppts"}
OUTPUT_DIR="./cleaned_ppts"

# 创建输出目录
mkdir -p "$OUTPUT_DIR"

# 检查 Python 依赖
if ! python -c "import pptx" 2>/dev/null; then
    echo "安装 python-pptx..."
    pip install python-pptx
fi

# 批量处理
echo "开始处理 $INPUT_DIR 中的 PPT 文件..."
python tools/remove_ppt_watermark.py --batch "$INPUT_DIR" --output "$OUTPUT_DIR"

echo "✅ 完成！清理后的文件保存在 $OUTPUT_DIR"
```

### Python 完整脚本（包含下载）

```python
#!/usr/bin/env python3
"""
NotebookLM PPT 完整处理流程
1. 监控下载文件夹
2. 自动检测新 PPT
3. 去除水印
4. 保存到指定位置
"""

import os
import time
import shutil
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from remove_ppt_watermark import process_pptx

class PPTHandler(FileSystemEventHandler):
    def __init__(self, output_dir):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def on_created(self, event):
        if event.is_directory:
            return
        
        if event.src_path.endswith('.pptx'):
            print(f"检测到新 PPT: {event.src_path}")
            time.sleep(2)  # 等待文件完全下载
            
            output_path = self.output_dir / f"{Path(event.src_path).stem}_cleaned.pptx"
            print(f"正在处理...")
            
            result = process_pptx(event.src_path, str(output_path))
            
            if result:
                print(f"✅ 完成！保存至: {output_path}")
                print(f"删除了 {result['watermarks_removed']} 个水印")

def monitor_downloads(watch_dir="~/Downloads", output_dir="./cleaned_ppts"):
    """监控下载文件夹，自动处理新 PPT"""
    watch_path = Path(watch_dir).expanduser()
    
    event_handler = PPTHandler(output_dir)
    observer = Observer()
    observer.schedule(event_handler, str(watch_path), recursive=False)
    observer.start()
    
    print(f"🔍 监控中: {watch_path}")
    print(f"📁 输出目录: {output_dir}")
    print("按 Ctrl+C 停止...")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    
    observer.join()

if __name__ == "__main__":
    monitor_downloads()
```

---

## 5️⃣ 最佳实践

### 提示词优化技巧

1. **明确结构**：指定幻灯片数量和每页内容
2. **提供上下文**：说明受众、目的、场景
3. **迭代优化**：先生成大纲，再逐步完善
4. **使用示例**：提供参考 PPT 的结构

### 去水印技巧

1. **先检查母版**：水印通常在母版页
2. **批量处理**：使用脚本一次性处理多个文件
3. **备份原文件**：处理前保留原始文件
4. **验证结果**：打开检查是否完全去除

### 质量检查清单

- [ ] 封面页标题清晰
- [ ] 目录页链接正确
- [ ] 内容逻辑连贯
- [ ] 图表数据准确
- [ ] 水印已完全去除
- [ ] 格式统一美观
- [ ] 拼写语法正确
- [ ] 导出质量良好

---

## 6️⃣ 常见问题

### Q1: NotebookLM 生成的 PPT 质量不高？

**解决方案**：
- 提供更详细的源材料
- 使用结构化提示词
- 多次迭代优化
- 手动调整关键页面

### Q2: 水印无法去除？

**解决方案**：
- 检查是否为背景图片（需要替换背景）
- 使用 PowerPoint 母版编辑
- 手动删除特定元素
- 尝试导出为 PDF 再转回 PPT

### Q3: 批量处理速度慢？

**解决方案**：
- 使用 SSD 硬盘
- 减少文件大小（压缩图片）
- 并行处理多个文件
- 使用更快的 CPU

---

## 7️⃣ 资源和工具

### NotebookLM
- 官网：https://notebooklm.google.com/
- 文档：https://support.google.com/notebooklm/

### 去水印工具
- Python 脚本：`tools/remove_ppt_watermark.py`
- PowerPoint 母版编辑
- Google Slides 主题编辑

### 相关工具
- **LibreOffice Impress**：免费 PPT 编辑
- **Google Slides**：在线协作
- **Canva**：设计模板

---

## 8️⃣ 快速开始

### 一键命令

```bash
# 1. 安装依赖
pip install python-pptx

# 2. 下载 NotebookLM 生成的 PPT 到 ~/Downloads

# 3. 批量去水印
python tools/remove_ppt_watermark.py --batch ~/Downloads --output ./cleaned_ppts

# 4. 查看结果
open ./cleaned_ppts
```

### 自动监控模式

```bash
# 启动监控（自动处理新下载的 PPT）
python tools/notebooklm_auto_processor.py

# 然后在 NotebookLM 中生成并下载 PPT
# 脚本会自动检测并处理
```

---

**更新时间**: 2026-03-24 19:28
