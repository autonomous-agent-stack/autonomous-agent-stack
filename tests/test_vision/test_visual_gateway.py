"""
Tests for Visual Gateway
测试视觉网关功能
"""

import pytest
import asyncio
import numpy as np
from PIL import Image
import io
import base64

from src.vision.visual_gateway import VisualGateway, analyze_image
from src.vision.texture_analyzer import TextureAnalyzer
from src.vision.chart_parser import ChartParser


class TestVisualGateway:
    """测试视觉网关"""
    
    @pytest.fixture
    def gateway(self):
        """创建网关实例"""
        return VisualGateway()
    
    @pytest.fixture
    def sample_image(self):
        """创建示例图像"""
        # 创建一个简单的 RGB 图像
        img_array = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        return Image.fromarray(img_array)
    
    @pytest.fixture
    def chart_image(self):
        """创建模拟柱状图"""
        # 创建白色背景
        img_array = np.ones((200, 300, 3), dtype=np.uint8) * 255
        
        # 添加几个彩色柱子
        img_array[50:150, 20:50] = [255, 0, 0]  # 红色柱子
        img_array[30:150, 80:110] = [0, 255, 0]  # 绿色柱子
        img_array[70:150, 140:170] = [0, 0, 255]  # 蓝色柱子
        img_array[20:150, 200:230] = [255, 255, 0]  # 黄色柱子
        
        return Image.fromarray(img_array)
    
    @pytest.fixture
    def texture_image(self):
        """创建纹理图像"""
        # 创建渐变纹理
        img_array = np.zeros((200, 200, 3), dtype=np.uint8)
        for i in range(200):
            img_array[i, :] = [i % 256, (i * 2) % 256, (255 - i) % 256]
        
        return Image.fromarray(img_array)
    
    @pytest.mark.asyncio
    async def test_analyze_image_with_pil(self, gateway, sample_image):
        """测试 1: 使用 PIL Image 分析图像"""
        result = await gateway.analyze_image(sample_image)
        
        assert 'type' in result
        assert 'data' in result
        assert 'text_description' in result
        assert 'metadata' in result
        assert result['metadata']['dimensions'] == (100, 100)
    
    @pytest.mark.asyncio
    async def test_analyze_image_with_bytes(self, gateway, sample_image):
        """测试 2: 使用字节数据分析图像"""
        # 转换为 bytes
        img_bytes = io.BytesIO()
        sample_image.save(img_bytes, format='PNG')
        img_bytes = img_bytes.getvalue()
        
        result = await gateway.analyze_image(img_bytes)
        
        assert 'type' in result
        assert result['metadata']['dimensions'] == (100, 100)
    
    @pytest.mark.asyncio
    async def test_analyze_image_with_base64(self, gateway, sample_image):
        """测试 3: 使用 base64 字符串分析图像"""
        # 转换为 base64
        img_bytes = io.BytesIO()
        sample_image.save(img_bytes, format='PNG')
        base64_str = base64.b64encode(img_bytes.getvalue()).decode('utf-8')
        
        result = await gateway.analyze_image(base64_str)
        
        assert 'type' in result
        assert result['metadata']['dimensions'] == (100, 100)
    
    @pytest.mark.asyncio
    async def test_analyze_chart_image(self, gateway, chart_image):
        """测试 4: 分析图表图像"""
        result = await gateway.analyze_image(chart_image)
        
        assert result['type'] in ['chart', 'screenshot']
        if result['type'] == 'chart':
            assert 'chart_data' in result['data']
    
    @pytest.mark.asyncio
    async def test_analyze_texture_image(self, gateway, texture_image):
        """测试 5: 分析纹理图像"""
        result = await gateway.analyze_image(texture_image)
        
        assert 'type' in result
        assert 'data' in result
    
    @pytest.mark.asyncio
    async def test_texture_to_text(self, gateway, texture_image):
        """测试 6: 质感转文案"""
        result = await gateway.texture_to_text(texture_image)
        
        assert 'quality' in result
        assert 'features' in result
        assert 'copywriting' in result
        
        quality = result['quality']
        assert 'sharpness' in quality
        assert 'contrast' in quality
        assert 'color_harmony' in quality
        assert 'overall_score' in quality
    
    @pytest.mark.asyncio
    async def test_chart_to_structured_data(self, gateway, chart_image):
        """测试 7: 图表转结构化数据"""
        result = await gateway.chart_to_structured_data(chart_image)
        
        assert 'chart_data' in result
        assert 'render_format' in result
        
        chart_data = result['chart_data']
        assert 'chart_type' in chart_data
        assert 'data_points' in chart_data
        assert 'labels' in chart_data
    
    def test_to_render_format(self, gateway, sample_image):
        """测试 8: 转换为渲染格式"""
        # 创建模拟分析结果
        analysis_result = {
            'type': 'photo',
            'data': {},
            'text_description': 'Test image'
        }
        
        render_format = gateway.to_render_format(analysis_result)
        
        assert 'background' in render_format
        assert 'style' in render_format
        assert 'data' in render_format
        assert render_format['background'] in ['light', 'dark']


class TestTextureAnalyzer:
    """测试质感分析器"""
    
    @pytest.fixture
    def analyzer(self):
        """创建分析器实例"""
        return TextureAnalyzer()
    
    @pytest.fixture
    def sample_image(self):
        """创建示例图像"""
        img_array = np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8)
        return Image.fromarray(img_array)
    
    def test_analyze_quality(self, analyzer, sample_image):
        """测试 9: 质量分析"""
        result = analyzer.analyze_quality(sample_image)
        
        assert 'sharpness' in result
        assert 'contrast' in result
        assert 'color_harmony' in result
        assert 'overall_score' in result
        
        # 验证值在 0-1 范围内
        assert 0 <= result['sharpness'] <= 1
        assert 0 <= result['contrast'] <= 1
        assert 0 <= result['color_harmony'] <= 1
        assert 0 <= result['overall_score'] <= 1
    
    def test_analyze_texture_features(self, analyzer, sample_image):
        """测试 10: 纹理特征分析"""
        result = analyzer.analyze_texture_features(sample_image)
        
        assert 'dominant_colors' in result
        assert 'brightness' in result
        assert 'saturation' in result
        assert 'quality' in result
        
        # 验证亮度统计
        brightness = result['brightness']
        assert 'mean' in brightness
        assert 'std' in brightness
        assert 'min' in brightness
        assert 'max' in brightness


class TestChartParser:
    """测试图表解析器"""
    
    @pytest.fixture
    def parser(self):
        """创建解析器实例"""
        return ChartParser()
    
    @pytest.fixture
    def bar_chart_image(self):
        """创建柱状图图像"""
        img_array = np.ones((200, 300, 3), dtype=np.uint8) * 255
        img_array[50:150, 20:50] = [255, 0, 0]
        img_array[30:150, 80:110] = [0, 255, 0]
        img_array[70:150, 140:170] = [0, 0, 255]
        
        return Image.fromarray(img_array)
    
    @pytest.fixture
    def pie_chart_image(self):
        """创建饼图图像"""
        img_array = np.ones((200, 200, 3), dtype=np.uint8) * 255
        
        # 创建简单的饼图（扇形）
        center = (100, 100)
        for y in range(200):
            for x in range(200):
                dx = x - center[0]
                dy = y - center[1]
                angle = np.arctan2(dy, dx)
                
                if dx*dx + dy*dy < 80*80:  # 圆内
                    if angle < 0:
                        img_array[y, x] = [255, 0, 0]
                    else:
                        img_array[y, x] = [0, 255, 0]
        
        return Image.fromarray(img_array)
    
    def test_extract_bar_data(self, parser, bar_chart_image):
        """测试 11: 提取柱状图数据"""
        result = parser.extract_data(bar_chart_image)
        
        assert result['chart_type'] in ['bar', 'line', 'pie']
        assert 'data_points' in result
        assert 'labels' in result
    
    def test_extract_pie_data(self, parser, pie_chart_image):
        """测试 12: 提取饼图数据"""
        result = parser.extract_data(pie_chart_image)
        
        assert 'chart_type' in result
        assert 'data_points' in result
    
    def test_to_render_format(self, parser, bar_chart_image):
        """测试 13: 转换为渲染格式"""
        data = parser.extract_data(bar_chart_image)
        render_format = parser.to_render_format(data)
        
        assert 'background' in render_format
        assert 'style' in render_format
        assert 'data' in render_format
        assert 'summary' in render_format['data']


class TestConvenienceFunction:
    """测试便捷函数"""
    
    @pytest.fixture
    def sample_image(self):
        """创建示例图像"""
        img_array = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        return Image.fromarray(img_array)
    
    @pytest.mark.asyncio
    async def test_analyze_image_function(self, sample_image):
        """测试 14: 便捷函数 analyze_image"""
        result = await analyze_image(sample_image)
        
        assert 'type' in result
        assert 'data' in result
        assert 'text_description' in result


class TestEdgeCases:
    """测试边界情况"""
    
    @pytest.fixture
    def gateway(self):
        """创建网关实例"""
        return VisualGateway()
    
    @pytest.mark.asyncio
    async def test_grayscale_image(self, gateway):
        """测试 15: 灰度图像"""
        # 创建灰度图像
        img_array = np.random.randint(0, 255, (100, 100), dtype=np.uint8)
        image = Image.fromarray(img_array, mode='L')
        
        result = await gateway.analyze_image(image)
        
        assert 'type' in result
        assert 'metadata' in result
    
    @pytest.mark.asyncio
    async def test_small_image(self, gateway):
        """测试 16: 小尺寸图像"""
        # 创建 10x10 的小图像
        img_array = np.random.randint(0, 255, (10, 10, 3), dtype=np.uint8)
        image = Image.fromarray(img_array)
        
        result = await gateway.analyze_image(image)
        
        assert result['metadata']['dimensions'] == (10, 10)
    
    @pytest.mark.asyncio
    async def test_large_image(self, gateway):
        """测试 17: 大尺寸图像"""
        # 创建 1000x1000 的大图像
        img_array = np.random.randint(0, 255, (1000, 1000, 3), dtype=np.uint8)
        image = Image.fromarray(img_array)
        
        result = await gateway.analyze_image(image)
        
        assert result['metadata']['dimensions'] == (1000, 1000)
    
    @pytest.mark.asyncio
    async def test_invalid_image_data(self, gateway):
        """测试 18: 无效图像数据"""
        with pytest.raises(Exception):
            await gateway.analyze_image(b"invalid data")


class TestIntegration:
    """集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_pipeline(self):
        """测试 19: 完整流程测试"""
        # 创建图像
        img_array = np.random.randint(0, 255, (200, 300, 3), dtype=np.uint8)
        image = Image.fromarray(img_array)
        
        # 分析图像
        gateway = VisualGateway()
        result = await gateway.analyze_image(image)
        
        # 验证结果结构
        assert 'type' in result
        assert 'data' in result
        assert 'text_description' in result
        assert 'metadata' in result
        
        # 转换为渲染格式
        render_format = gateway.to_render_format(result)
        assert 'background' in render_format
        assert 'style' in render_format


# 运行测试的入口
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
