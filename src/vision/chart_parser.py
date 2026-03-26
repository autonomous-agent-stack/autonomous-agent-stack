"""
Chart Parser
从图表图像中提取数据，支持柱状图、折线图、饼图等常见图表类型
"""

import logging
from typing import Dict, Any, List, Tuple, Optional
import numpy as np
from PIL import Image
import colorsys
from collections import defaultdict

logger = logging.getLogger(__name__)


class ChartParser:
    """图表解析器"""
    
    def __init__(self):
        self.logger = logger
        self.chart_types = ['bar', 'line', 'pie', 'scatter', 'area']
    
    def extract_data(self, image: Image.Image) -> Dict[str, Any]:
        """
        从图表中提取数据
        
        Args:
            image: PIL Image 对象
            
        Returns:
            {
                "chart_type": "bar|line|pie",
                "data_points": [...],
                "labels": [...],
                "title": "...",
                "axes": {...}
            }
        """
        logger.info("[Agent-Stack-Bridge] Chart parsing started")
        
        # 转换为 RGB
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        img_array = np.array(image)
        
        # 识别图表类型
        chart_type = self._detect_chart_type(img_array)
        logger.info(f"[Agent-Stack-Bridge] Detected chart type: {chart_type}")
        
        # 根据类型提取数据
        if chart_type == 'bar':
            result = self._extract_bar_data(img_array)
        elif chart_type == 'line':
            result = self._extract_line_data(img_array)
        elif chart_type == 'pie':
            result = self._extract_pie_data(img_array)
        else:
            result = self._extract_generic_data(img_array)
        
        result['chart_type'] = chart_type
        
        logger.info("[Agent-Stack-Bridge] Chart data extracted")
        return result
    
    def _detect_chart_type(self, img_array: np.ndarray) -> str:
        """
        检测图表类型
        
        Args:
            img_array: 图像数组
            
        Returns:
            图表类型字符串
        """
        h, w, _ = img_array.shape
        
        # 简化版类型检测
        # 检测垂直色块（柱状图）
        if self._has_vertical_bars(img_array):
            return 'bar'
        
        # 检测连续线条（折线图）
        if self._has_continuous_lines(img_array):
            return 'line'
        
        # 检测圆形分布（饼图）
        if self._has_circular_pattern(img_array):
            return 'pie'
        
        return 'bar'  # 默认为柱状图
    
    def _has_vertical_bars(self, img_array: np.ndarray) -> bool:
        """检测是否有垂直柱状条"""
        h, w, _ = img_array.shape
        
        # 采样中心区域
        center_region = img_array[h//3:2*h//3, :, :]
        
        # 检测颜色分布
        unique_colors = len(np.unique(center_region.reshape(-1, 3), axis=0))
        
        # 柱状图通常有明显的颜色分区
        return unique_colors < 50
    
    def _has_continuous_lines(self, img_array: np.ndarray) -> bool:
        """检测是否有连续线条"""
        # 简化版：检测边缘连续性
        gray = np.mean(img_array, axis=2)
        
        # 检测边缘
        edges = np.abs(np.diff(gray, axis=0)) + np.abs(np.diff(gray, axis=1))
        
        # 如果边缘连续性高，可能是折线图
        return np.mean(edges) > 20
    
    def _has_circular_pattern(self, img_array: np.ndarray) -> bool:
        """检测是否有圆形图案"""
        h, w, _ = img_array.shape
        center = (h // 2, w // 2)
        
        # 简化版：检查从中心向外辐射的颜色变化
        radius = min(h, w) // 2
        angles = np.linspace(0, 2*np.pi, 36)
        
        color_changes = 0
        prev_color = None
        
        for angle in angles:
            y = int(center[0] + radius * 0.7 * np.sin(angle))
            x = int(center[1] + radius * 0.7 * np.cos(angle))
            
            if 0 <= y < h and 0 <= x < w:
                color = tuple(img_array[y, x])
                if prev_color is not None and color != prev_color:
                    color_changes += 1
                prev_color = color
        
        # 饼图通常有多个颜色变化
        return color_changes > 3
    
    def _extract_bar_data(self, img_array: np.ndarray) -> Dict[str, Any]:
        """
        提取柱状图数据
        
        Args:
            img_array: 图像数组
            
        Returns:
            柱状图数据
        """
        h, w, _ = img_array.shape
        
        # 检测柱状区域
        bars = self._detect_bars(img_array)
        
        # 提取数据点
        data_points = []
        labels = []
        
        for i, bar in enumerate(bars):
            height = bar['height']
            # 归一化高度
            normalized_height = height / h
            data_points.append(round(normalized_height * 100, 2))
            labels.append(f"Bar {i+1}")
        
        # 检测标题区域（顶部）
        title = self._extract_title(img_array)
        
        return {
            "data_points": data_points,
            "labels": labels,
            "title": title,
            "axes": {
                "x_label": "Category",
                "y_label": "Value"
            }
        }
    
    def _detect_bars(self, img_array: np.ndarray) -> List[Dict]:
        """检测柱状图的柱子"""
        h, w, _ = img_array.shape
        
        # 背景色（假设为白色或浅色）
        background = np.array([255, 255, 255])
        
        # 扫描列
        bars = []
        in_bar = False
        bar_start = 0
        
        for x in range(w):
            column = img_array[:, x, :]
            
            # 检测是否为柱状区域
            is_bar = not np.allclose(column, background, atol=50)
            
            if is_bar and not in_bar:
                in_bar = True
                bar_start = x
            elif not is_bar and in_bar:
                in_bar = False
                # 计算柱子高度
                bar_region = img_array[:, bar_start:x, :]
                height = self._calculate_bar_height(bar_region)
                bars.append({
                    "x_start": bar_start,
                    "x_end": x,
                    "height": height
                })
        
        return bars
    
    def _calculate_bar_height(self, bar_region: np.ndarray) -> int:
        """计算柱子高度"""
        # 找到非背景色的最高点
        h, _, _ = bar_region.shape
        
        for y in range(h):
            row = bar_region[y, :, :]
            if not np.allclose(row, [255, 255, 255], atol=50):
                return h - y
        
        return 0
    
    def _extract_line_data(self, img_array: np.ndarray) -> Dict[str, Any]:
        """
        提取折线图数据
        
        Args:
            img_array: 图像数组
            
        Returns:
            折线图数据
        """
        h, w, _ = img_array.shape
        
        # 检测线条
        points = self._detect_line_points(img_array)
        
        # 归一化数据点
        data_points = []
        for x, y in points:
            normalized_y = 1.0 - (y / h)
            data_points.append(round(normalized_y * 100, 2))
        
        labels = [f"Point {i+1}" for i in range(len(points))]
        
        return {
            "data_points": data_points,
            "labels": labels,
            "title": self._extract_title(img_array),
            "axes": {
                "x_label": "Time",
                "y_label": "Value"
            }
        }
    
    def _detect_line_points(self, img_array: np.ndarray) -> List[Tuple[int, int]]:
        """检测折线图的数据点"""
        h, w, _ = img_array.shape
        
        # 采样 x 轴
        sample_x = np.linspace(0, w-1, 20, dtype=int)
        
        points = []
        for x in sample_x:
            column = img_array[:, x, :]
            # 找到线条位置（非背景色）
            for y in range(h):
                if not np.allclose(column[y], [255, 255, 255], atol=50):
                    points.append((int(x), y))
                    break
        
        return points
    
    def _extract_pie_data(self, img_array: np.ndarray) -> Dict[str, Any]:
        """
        提取饼图数据
        
        Args:
            img_array: 图像数组
            
        Returns:
            饼图数据
        """
        h, w, _ = img_array.shape
        center = (h // 2, w // 2)
        radius = min(h, w) // 2
        
        # 检测扇区
        sectors = self._detect_pie_sectors(img_array, center, radius)
        
        # 计算每个扇区的角度
        total_angle = 360
        data_points = []
        labels = []
        
        for i, sector in enumerate(sectors):
            angle = sector['angle']
            percentage = round((angle / total_angle) * 100, 2)
            data_points.append(percentage)
            labels.append(f"Sector {i+1}")
        
        return {
            "data_points": data_points,
            "labels": labels,
            "title": self._extract_title(img_array),
            "total": sum(data_points)
        }
    
    def _detect_pie_sectors(self, img_array: np.ndarray, center: Tuple[int, int], radius: int) -> List[Dict]:
        """检测饼图的扇区"""
        h, w, _ = img_array.shape
        
        # 从中心向外扫描
        angles = np.linspace(0, 2*np.pi, 360)
        
        sectors = []
        current_color = None
        sector_start = 0
        
        for i, angle in enumerate(angles):
            y = int(center[0] + radius * 0.7 * np.sin(angle))
            x = int(center[1] + radius * 0.7 * np.cos(angle))
            
            if 0 <= y < h and 0 <= x < w:
                color = tuple(img_array[y, x])
                
                if current_color is None:
                    current_color = color
                elif color != current_color:
                    # 新扇区开始
                    sector_angle = (i - sector_start)
                    sectors.append({
                        "angle": sector_angle,
                        "color": current_color
                    })
                    current_color = color
                    sector_start = i
        
        # 最后一个扇区
        if sector_start < len(angles):
            sectors.append({
                "angle": len(angles) - sector_start,
                "color": current_color
            })
        
        return sectors
    
    def _extract_generic_data(self, img_array: np.ndarray) -> Dict[str, Any]:
        """提取通用图表数据"""
        h, w, _ = img_array.shape
        
        return {
            "data_points": [],
            "labels": [],
            "title": self._extract_title(img_array),
            "dimensions": {
                "width": w,
                "height": h
            }
        }
    
    def _extract_title(self, img_array: np.ndarray) -> str:
        """提取图表标题（简化版）"""
        # 实际实现需要 OCR
        # 这里返回占位符
        return "Chart Title"
    
    def to_render_format(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        将提取的数据转换为渲染格式
        
        Args:
            data: 提取的图表数据
            
        Returns:
            极简看板渲染需求格式
        """
        return {
            "background": "light",
            "style": "minimal",
            "data": {
                "summary": f"{data.get('chart_type', 'chart').title()} chart with {len(data.get('data_points', []))} data points",
                "key_metrics": data.get("data_points", [])[:5],
                "visual_insights": [
                    f"Max value: {max(data.get('data_points', [0]))}",
                    f"Min value: {min(data.get('data_points', [0]))}"
                ]
            }
        }
