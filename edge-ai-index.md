# 边缘AI部署 - 快速索引

## 📚 完整指南

详细的边缘AI部署指南已创建在 **[edge-ai-deployment-guide.md](./edge-ai-deployment-guide.md)**

## 🎯 快速导航

### 核心框架
1. **[ONNX Runtime](#onnx-runtime)** - 跨平台推理引擎
2. **[TensorRT](#tensorrt)** - NVIDIA GPU高性能推理
3. **[Core ML](#core-ml)** - Apple生态系统
4. **[TFLite](#tflite)** - Android和嵌入式设备
5. **[OpenVINO](#openvino)** - Intel硬件优化

### 关键主题
- [框架对比](#框架对比) - 性能、优缺点、适用场景
- [最佳实践](#最佳实践) - 模型优化、批处理、内存管理
- [实战案例](#实战案例) - 移动端、工业、iOS应用

## 📊 框架选择决策树

```
需要部署边缘AI模型?
    |
    ├─ 目标平台?
    |   ├─ iOS/macOS → Core ML
    |   ├─ Android → TFLite
    |   ├─ NVIDIA GPU → TensorRT
    |   ├─ Intel CPU/GPU → OpenVINO
    |   └─ 未知/多平台 → ONNX Runtime
    |
    ├─ 性能要求?
    |   ├─ 极致性能 → TensorRT (GPU), OpenVINO (CPU)
    |   ├─ 平衡性能 → ONNX Runtime
    |   └─ 快速集成 → TFLite, Core ML
    |
    └─ 开发经验?
        ├─ TensorFlow → TFLite
        ├─ PyTorch → ONNX Runtime / TensorRT
        ├─ Apple生态 → Core ML
        └─ 通用 → ONNX Runtime
```

## 🚀 快速开始

### ONNX Runtime (推荐新手)

```python
# 安装
pip install onnxruntime

# 转换模型
import torch
torch.onnx.export(model, dummy_input, "model.onnx")

# 推理
import onnxruntime as ort
session = ort.InferenceSession("model.onnx")
output = session.run(None, {'input': input_data})
```

### TensorRT (NVIDIA GPU)

```python
# 转换
import tensorrt as trt
converter = TensorRTConverter("model.onnx")
engine = converter.build_engine(fp16=True)

# 推理
inferencer = TensorRTInference("model.trt")
output = inferencer.infer(input_data)
```

### TFLite (Android)

```python
# 转换
import tensorflow as tf
converter = tf.lite.TFLiteConverter.from_saved_model(model)
converter.optimizations = [tf.lite.Optimize.DEFAULT]
tflite_model = converter.convert()

# 推理
interpreter = tf.lite.Interpreter(model_path="model.tflite")
interpreter.invoke()
```

## 📖 实战案例

### 案例1: 移动端图像分类
- **框架**: TFLite
- **模型**: MobileNetV2
- **目标**: Android应用
- **性能**: < 50ms 推理时间

### 案例2: 工业视觉检测
- **框架**: OpenVINO
- **模型**: YOLOv8
- **目标**: Intel NUC
- **性能**: 30 FPS 实时检测

### 案例3: iOS情感分析
- **框架**: Core ML
- **模型**: DistilBERT
- **目标**: iOS应用
- **性能**: < 100ms 响应时间

### 案例4: 跨平台部署
- 一键部署到 ONNX、TFLite、Core ML、TensorRT、OpenVINO

## 🎓 学习资源

- [ONNX Runtime 文档](https://onnxruntime.ai/docs/)
- [TensorRT 开发者指南](https://developer.nvidia.com/tensorrt)
- [Core ML 文档](https://developer.apple.com/documentation/coreml)
- [TFLite 指南](https://www.tensorflow.org/lite)
- [OpenVINO 文档](https://docs.openvino.ai/)

## 💡 最佳实践

1. **始终从ONNX开始** - 最通用的中间格式
2. **量化是关键** - INT8减少75%大小,提升3-4倍性能
3. **测试精度** - 量化后务必验证精度下降
4. **在目标设备上测试** - 不要依赖CPU测试结果
5. **监控资源** - 内存和功耗在边缘设备上很关键

## 📈 性能对比

### 推理延迟 (ResNet50, 单张图像)

| 硬件 | ONNX RT | TensorRT | TFLite | OpenVINO |
|------|---------|----------|--------|----------|
| CPU  | 15.2 ms | -        | 18.5 ms| 12.8 ms  |
| GPU  | 2.1 ms  | 1.3 ms   | -      | 2.8 ms   |

### 模型大小 (ResNet50)

| 格式 | 原始 | FP16 | INT8 |
|------|------|------|------|
| 大小 | 98 MB | 49 MB | 25 MB |

---

**完整文档**: [edge-ai-deployment-guide.md](./edge-ai-deployment-guide.md) (2202 行, ~100KB)

包含完整的代码示例、性能优化技巧、最佳实践和实战案例。
