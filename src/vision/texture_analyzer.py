"""
Texture Analyzer
分析图像质感、清晰度、对比度、色彩和谐度等视觉特征
"""

import logging
from typing import Dict, Any
import numpy as np
from PIL import Image
import colorsys

logger = logging.getLogger(__name__)


class TextureAnalyzer:
    """图像质感分析器"""
    
    def __init__(self):
        self.logger = logger
    
    def analyze_quality(self, image: Image.Image) -> Dict[str, float]:
        """
        分析图像质感
        
        Args:
            image: PIL Image 对象
            
        Returns:
            {
                "sharpness": 0.85,      # 清晰度 (0-1)
                "contrast": 0.72,       # 对比度 (0-1)
                "color_harmony": 0.90,  # 色彩和谐度 (0-1)
                "overall_score": 0.82   # 综合评分 (0-1)
            }
        """
        logger.info("[Agent-Stack-Bridge] Texture analysis started")
        
        # 转换为 RGB 模式
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # 转换为 numpy 数组
        img_array = np.array(image)
        
        # 计算各项指标
        sharpness = self._calculate_sharpness(img_array)
        contrast = self._calculate_contrast(img_array)
        color_harmony = self._calculate_color_harmony(img_array)
        
        # 综合评分 (加权平均)
        overall_score = (sharpness * 0.3 + contrast * 0.3 + color_harmony * 0.4)
        
        result = {
            "sharpness": round(float(sharpness), 2),
            "contrast": round(float(contrast), 2),
            "color_harmony": round(float(color_harmony), 2),
            "overall_score": round(float(overall_score), 2)
        }
        
        logger.info(f"[Agent-Stack-Bridge] Texture analysis complete: {result}")
        return result
    
    def _calculate_sharpness(self, img_array: np.ndarray) -> float:
        """
        计算图像清晰度
        使用 Laplacian 算子的方差来衡量
        
        Args:
            img_array: 图像数组
            
        Returns:
            清晰度评分 (0-1)
        """
        # 转换为灰度图
        if len(img_array.shape) == 3:
            gray = np.mean(img_array, axis=2)
        else:
            gray = img_array
        
        # Laplacian 算子
        laplacian_kernel = np.array([
            [0, 1, 0],
            [1, -4, 1],
            [0, 1, 0]
        ])
        
        # 应用卷积（简化版）
        h, w = gray.shape
        laplacian = np.zeros_like(gray)
        for i in range(1, h-1):
            for j in range(1, w-1):
                laplacian[i, j] = np.sum(gray[i-1:i+2, j-1:j+2] * laplacian_kernel)
        
        # 计算方差
        variance = np.var(laplacian)
        
        # 归一化到 0-1 (经验值)
        sharpness = min(variance / 1000.0, 1.0)
        
        return float(sharpness)
    
    def _calculate_contrast(self, img_array: np.ndarray) -> float:
        """
        计算图像对比度
        使用标准差来衡量
        
        Args:
            img_array: 图像数组
            
        Returns:
            对比度评分 (0-1)
        """
        # 转换为灰度图
        if len(img_array.shape) == 3:
            gray = np.mean(img_array, axis=2)
        else:
            gray = img_array
        
        # 计算标准差
        std = np.std(gray)
        
        # 归一化到 0-1 (经验值)
        contrast = min(std / 128.0, 1.0)
        
        return float(contrast)
    
    def _calculate_color_harmony(self, img_array: np.ndarray) -> float:
        """
        计算色彩和谐度
        基于色彩分布的均匀性和互补性
        
        Args:
            img_array: 图像数组 (RGB)
            
        Returns:
            色彩和谐度评分 (0-1)
        """
        if len(img_array.shape) != 3:
            return 1.0  # 灰度图默认和谐
        
        # 采样像素点以提高性能
        h, w, _ = img_array.shape
        sample_rate = max(1, (h * w) // 10000)
        sampled = img_array[::sample_rate, ::sample_rate, :]
        
        # 转换为 HSV
        hsv_colors = []
        for pixel in sampled.reshape(-1, 3):
            r, g, b = pixel / 255.0
            h_val, s_val, v_val = colorsys.rgb_to_hsv(r, g, b)
            hsv_colors.append((h_val, s_val, v_val))
        
        hsv_colors = np.array(hsv_colors)
        
        # 计算色相分布
        hues = hsv_colors[:, 0]
        
        # 计算色相的聚类程度（越集中越和谐）
        hue_variance = np.var(hues)
        
        # 低方差表示色彩和谐（色相接近）
        harmony = max(0.0, 1.0 - hue_variance * 2)
        
        return float(harmony)
    
    def analyze_texture_features(self, image: Image.Image) -> Dict[str, Any]:
        """
        分析图像纹理特征
        
        Args:
            image: PIL Image 对象
            
        Returns:
            纹理特征字典
        """
        logger.info("[Agent-Stack-Bridge] Texture feature analysis started")
        
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        img_array = np.array(image)
        
        # 提取主要颜色
        dominant_colors = self._extract_dominant_colors(img_array)
        
        # 分析亮度分布
        brightness = self._analyze_brightness(img_array)
        
        # 分析饱和度
        saturation = self._analyze_saturation(img_array)
        
        features = {
            "dominant_colors": dominant_colors,
            "brightness": brightness,
            "saturation": saturation,
            "quality": self.analyze_quality(image)
        }
        
        logger.info("[Agent-Stack-Bridge] Texture feature analysis complete")
        return features
    
    def _extract_dominant_colors(self, img_array: np.ndarray, n_colors: int = 5) -> list:
        """
        提取主要颜色
        
        Args:
            img_array: 图像数组
            n_colors: 提取的颜色数量
            
        Returns:
            主要颜色列表 (RGB)
        """
        # 简化版：采样并聚类
        h, w, _ = img_array.shape
        sample_rate = max(1, (h * w) // 1000)
        sampled = img_array[::sample_rate, ::sample_rate, :].reshape(-1, 3)
        
        # 使用简单的直方图方法
        unique, counts = np.unique(sampled, axis=0, return_counts=True)
        top_indices = np.argsort(counts)[-n_colors:][::-1]
        
        dominant = [tuple(unique[i]) for i in top_indices]
        
        return dominant
    
    def _analyze_brightness(self, img_array: np.ndarray) -> Dict[str, float]:
        """
        分析亮度分布
        
        Args:
            img_array: 图像数组
            
        Returns:
            亮度统计信息
        """
        if len(img_array.shape) == 3:
            gray = np.mean(img_array, axis=2)
        else:
            gray = img_array
        
        return {
            "mean": round(float(np.mean(gray)), 2),
            "std": round(float(np.std(gray)), 2),
            "min": float(np.min(gray)),
            "max": float(np.max(gray))
        }
    
    def _analyze_saturation(self, img_array: np.ndarray) -> Dict[str, float]:
        """
        分析饱和度分布
        
        Args:
            img_array: 图像数组 (RGB)
            
        Returns:
            饱和度统计信息
        """
        if len(img_array.shape) != 3:
            return {"mean": 0.0, "std": 0.0}
        
        # 转换为 HSV 并提取饱和度
        saturations = []
        for pixel in img_array.reshape(-1, 3):
            r, g, b = pixel / 255.0
            _, s, _ = colorsys.rgb_to_hsv(r, g, b)
            saturations.append(s)
        
        saturations = np.array(saturations)
        
        return {
            "mean": round(float(np.mean(saturations)), 2),
            "std": round(float(np.std(saturations)), 2)
        }
