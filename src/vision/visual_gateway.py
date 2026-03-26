"""
Visual Gateway
多模态视觉网关，统一处理图像分析、质感转化、图表解析等视觉任务
"""

import io
import base64
import logging
from typing import Dict, Any, Optional, Union
from pathlib import Path

from PIL import Image
import numpy as np

from .texture_analyzer import TextureAnalyzer
from .chart_parser import ChartParser

# 环境防御：导入安全模块
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from security.apple_double_cleaner import AppleDoubleCleaner

logger = logging.getLogger(__name__)


class VisualGateway:
    """
    多模态视觉网关
    
    提供统一的图像分析接口，支持：
    - 图像类型识别
    - 质感分析
    - 图表解析
    - 结构化数据提取
    """
    
    def __init__(self):
        """初始化视觉网关"""
        # 环境防御：清理 AppleDouble 文件
        AppleDoubleCleaner.clean()
        
        self.texture_analyzer = TextureAnalyzer()
        self.chart_parser = ChartParser()
        
        logger.info("[Agent-Stack-Bridge] Visual gateway initialized")
    
    async def analyze_image(self, image_data: Union[bytes, str, Image.Image]) -> Dict[str, Any]:
        """
        分析图像，提取结构化信息
        
        Args:
            image_data: 图像数据，可以是：
                       - bytes: 二进制数据
                       - str: base64 编码字符串或文件路径
                       - Image: PIL Image 对象
        
        Returns:
            {
                "type": "chart|screenshot|texture|photo",
                "data": {...},
                "text_description": "...",
                "metadata": {...}
            }
        """
        logger.info("[Agent-Stack-Bridge] Analyzing image")
        
        # 转换为 PIL Image
        image = self._to_pil_image(image_data)
        
        # 识别图像类型
        image_type = self._classify_image(image)
        logger.info(f"[Agent-Stack-Bridge] Image classified as: {image_type}")
        
        # 根据类型选择处理策略
        if image_type == 'chart':
            data = await self.chart_to_structured_data(image)
        elif image_type == 'texture':
            data = await self.texture_to_text(image)
        elif image_type == 'screenshot':
            data = await self._analyze_screenshot(image)
        else:
            data = await self._analyze_photo(image)
        
        # 生成文本描述
        text_description = self._generate_description(image_type, data)
        
        result = {
            "type": image_type,
            "data": data,
            "text_description": text_description,
            "metadata": {
                "dimensions": image.size,
                "mode": image.mode,
                "format": getattr(image, 'format', 'UNKNOWN')
            }
        }
        
        logger.info("[Agent-Stack-Bridge] Image analysis complete")
        return result
    
    async def texture_to_text(self, image: Image.Image) -> Dict[str, Any]:
        """
        将图形质感转化为文案描述
        
        Args:
            image: PIL Image 对象
            
        Returns:
            质感分析和文案描述
        """
        logger.info("[Agent-Stack-Bridge] Converting texture to text")
        
        # 分析质感
        quality = self.texture_analyzer.analyze_quality(image)
        features = self.texture_analyzer.analyze_texture_features(image)
        
        # 生成文案
        text = self._generate_texture_copywriting(quality, features)
        
        return {
            "quality": quality,
            "features": features,
            "copywriting": text
        }
    
    async def chart_to_structured_data(self, image: Image.Image) -> Dict[str, Any]:
        """
        将图表截图转化为结构化数据
        
        Args:
            image: PIL Image 对象
            
        Returns:
            结构化图表数据
        """
        logger.info("[Agent-Stack-Bridge] Extracting chart data")
        
        # 解析图表
        chart_data = self.chart_parser.extract_data(image)
        
        # 转换为渲染格式
        render_format = self.chart_parser.to_render_format(chart_data)
        
        return {
            "chart_data": chart_data,
            "render_format": render_format
        }
    
    async def _analyze_screenshot(self, image: Image.Image) -> Dict[str, Any]:
        """
        分析截图类型图像
        
        Args:
            image: PIL Image 对象
            
        Returns:
            截图分析结果
        """
        logger.info("[Agent-Stack-Bridge] Analyzing screenshot")
        
        # 分析截图内容
        img_array = np.array(image)
        
        # 检测 UI 元素
        ui_elements = self._detect_ui_elements(img_array)
        
        # 检测文本区域
        text_regions = self._detect_text_regions(img_array)
        
        return {
            "ui_elements": ui_elements,
            "text_regions": text_regions,
            "layout": self._analyze_layout(img_array)
        }
    
    async def _analyze_photo(self, image: Image.Image) -> Dict[str, Any]:
        """
        分析照片类型图像
        
        Args:
            image: PIL Image 对象
            
        Returns:
            照片分析结果
        """
        logger.info("[Agent-Stack-Bridge] Analyzing photo")
        
        # 分析照片特征
        quality = self.texture_analyzer.analyze_quality(image)
        features = self.texture_analyzer.analyze_texture_features(image)
        
        return {
            "quality": quality,
            "features": features,
            "category": "photo"
        }
    
    def _to_pil_image(self, image_data: Union[bytes, str, Image.Image]) -> Image.Image:
        """
        将各种格式的图像数据转换为 PIL Image
        
        Args:
            image_data: 图像数据
            
        Returns:
            PIL Image 对象
        """
        if isinstance(image_data, Image.Image):
            return image_data
        
        if isinstance(image_data, bytes):
            return Image.open(io.BytesIO(image_data))
        
        if isinstance(image_data, str):
            # 检查是否为 base64 (带前缀)
            if image_data.startswith('data:image'):
                # 移除 data:image/xxx;base64, 前缀
                base64_data = image_data.split(',', 1)[1]
                image_bytes = base64.b64decode(base64_data)
                return Image.open(io.BytesIO(image_bytes))
            
            # 先尝试作为纯 base64 解码
            try:
                image_bytes = base64.b64decode(image_data)
                return Image.open(io.BytesIO(image_bytes))
            except Exception:
                pass  # 不是 base64，继续检查文件路径
            
            # 检查是否为文件路径
            if Path(image_data).exists():
                return Image.open(image_data)
            
            raise ValueError(f"Unable to parse image data: {image_data[:50]}...")
        
        raise TypeError(f"Unsupported image data type: {type(image_data)}")
    
    def _classify_image(self, image: Image.Image) -> str:
        """
        分类图像类型
        
        Args:
            image: PIL Image 对象
            
        Returns:
            图像类型：chart, screenshot, texture, photo
        """
        img_array = np.array(image)
        
        # 特征提取
        h, w = img_array.shape[:2]
        aspect_ratio = w / h
        
        # 颜色复杂度
        if len(img_array.shape) == 3:
            unique_colors = len(np.unique(img_array.reshape(-1, 3), axis=0))
        else:
            unique_colors = len(np.unique(img_array))
        
        # 图表特征：颜色数量较少，有规则的几何形状
        if unique_colors < 50 and aspect_ratio > 1.2:
            return 'chart'
        
        # 截图特征：宽高比接近屏幕比例，有明显的 UI 元素
        if 1.3 < aspect_ratio < 2.5:
            return 'screenshot'
        
        # 质感/纹理图像：颜色数量中等，无明显几何形状
        if 50 < unique_colors < 5000:
            return 'texture'
        
        # 默认为照片
        return 'photo'
    
    def _generate_description(self, image_type: str, data: Dict[str, Any]) -> str:
        """
        生成图像的文本描述
        
        Args:
            image_type: 图像类型
            data: 分析数据
            
        Returns:
            文本描述
        """
        if image_type == 'chart':
            chart_data = data.get('chart_data', {})
            chart_type = chart_data.get('chart_type', 'unknown')
            num_points = len(chart_data.get('data_points', []))
            return f"A {chart_type} chart with {num_points} data points showing {chart_data.get('title', 'data visualization')}"
        
        elif image_type == 'texture':
            quality = data.get('quality', {})
            score = quality.get('overall_score', 0)
            return f"A texture image with overall quality score of {score:.2f}"
        
        elif image_type == 'screenshot':
            ui_count = len(data.get('ui_elements', []))
            return f"A screenshot containing {ui_count} UI elements"
        
        else:
            return f"A {image_type} image"
    
    def _generate_texture_copywriting(self, quality: Dict[str, float], features: Dict[str, Any]) -> str:
        """
        根据质感分析生成文案
        
        Args:
            quality: 质量评分
            features: 纹理特征
            
        Returns:
            文案字符串
        """
        score = quality.get('overall_score', 0)
        
        if score > 0.8:
            quality_desc = "excellent"
        elif score > 0.6:
            quality_desc = "good"
        elif score > 0.4:
            quality_desc = "fair"
        else:
            quality_desc = "needs improvement"
        
        sharpness = quality.get('sharpness', 0)
        contrast = quality.get('contrast', 0)
        harmony = quality.get('color_harmony', 0)
        
        copywriting = f"""
This image exhibits {quality_desc} visual quality with an overall score of {score:.2f}.

Key characteristics:
- Sharpness: {sharpness:.2f} ({'crisp' if sharpness > 0.7 else 'soft'})
- Contrast: {contrast:.2f} ({'high' if contrast > 0.7 else 'moderate'})
- Color Harmony: {harmony:.2f} ({'harmonious' if harmony > 0.7 else 'varied'})

The visual texture creates a {'professional and polished' if score > 0.7 else 'casual and natural'} impression.
"""
        
        return copywriting.strip()
    
    def _detect_ui_elements(self, img_array: np.ndarray) -> list:
        """检测 UI 元素（简化版）"""
        # 实际实现需要更复杂的算法或深度学习模型
        # 这里返回示例数据
        return [
            {"type": "button", "count": 3},
            {"type": "text_field", "count": 2}
        ]
    
    def _detect_text_regions(self, img_array: np.ndarray) -> list:
        """检测文本区域（简化版）"""
        # 实际实现需要 OCR
        return [
            {"region": "top", "estimated_text": "Header"},
            {"region": "center", "estimated_text": "Content"}
        ]
    
    def _analyze_layout(self, img_array: np.ndarray) -> Dict[str, Any]:
        """分析布局"""
        h, w = img_array.shape[:2]
        
        return {
            "orientation": "landscape" if w > h else "portrait",
            "grid_type": "standard",
            "complexity": "medium"
        }
    
    def to_render_format(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        将分析结果转换为极简看板渲染格式
        
        Args:
            analysis_result: analyze_image 的返回结果
            
        Returns:
            极简看板渲染需求格式
        """
        image_type = analysis_result.get('type', 'unknown')
        data = analysis_result.get('data', {})
        
        if image_type == 'chart':
            return data.get('render_format', {})
        
        # 默认渲染格式
        return {
            "background": "light",
            "style": "minimal",
            "data": {
                "summary": analysis_result.get('text_description', ''),
                "key_metrics": [],
                "visual_insights": []
            }
        }


# 便捷函数
async def analyze_image(image_data: Union[bytes, str, Image.Image]) -> Dict[str, Any]:
    """
    便捷函数：分析图像
    
    Args:
        image_data: 图像数据
        
    Returns:
        分析结果
    """
    gateway = VisualGateway()
    return await gateway.analyze_image(image_data)
