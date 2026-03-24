# AI 模型压缩技术 - 快速参考

**版本:** 1.0  
**更新时间:** 2026-03-25

---

## 🚀 快速决策树

```
是否需要训练新模型?
├─ 是 → 知识蒸馏 + NAS
└─ 否 → 剪枝 + 量化

    目标是什么?
    ├─ 减少存储 → 量化、剪枝
    ├─ 加速推理 → 结构化剪枝、量化
    ├─ 降低能耗 → 量化、知识蒸馏
    └─ 部署到边缘 → 量化 + 剪枝

        可接受的精度损失?
        ├─ < 1% → 混合策略
        ├─ 1-3% → 剪枝或量化
        └─ > 3% → 极端压缩
```

---

## 📊 压缩技术速查表

| 技术 | 压缩比 | 速度提升 | 精度损失 | 实现时间 | 适用场景 |
|------|--------|----------|----------|----------|----------|
| **PTQ (INT8)** | 4x | 2-4x | 0.5-2% | ⚡ 1小时 | 快速部署 |
| **QAT (INT8)** | 4x | 2-4x | 0.1-1% | 🕐 1天 | 高质量部署 |
| **非结构化剪枝** | 2-10x | 0-2x | 0.5-3% | 🕐 1天 | 存储受限 |
| **结构化剪枝** | 2-5x | 1.5-3x | 1-5% | 🕐 2-3天 | 推理加速 |
| **知识蒸馏** | 2-4x | 1.5-2x | 0.5-2% | 🕐 3-5天 | 训练新模型 |
| **NAS** | 2-5x | 2-4x | 0-2% | 🕐 1-2周 | 架构搜索 |
| **混合策略** | 4-20x | 3-10x | 1-5% | 🕐 1-2周 | 最大化压缩 |

---

## 🛠️ PyTorch 快速实现

### 1. 动态量化（最简单）

```python
import torch.quantization as quant

# 一行代码完成量化
quantized_model = quant.quantize_dynamic(
    model,
    {nn.Linear, nn.LSTM},  # 要量化的层
    dtype=torch.qint8
)

# 评估
acc = evaluate(quantized_model, test_loader)
size = get_model_size(quantized_model)
print(f"精度: {acc:.2%}, 大小: {size:.2f} MB")
```

### 2. 静态量化（推荐）

```python
# 步骤 1: 准备
model.qconfig = quant.get_default_qconfig('fbgemm')
prepared_model = quant.prepare(model)

# 步骤 2: 校准（100-1000 个样本）
with torch.no_grad():
    for i, (data, _) in enumerate(calibration_loader):
        prepared_model(data)
        if i >= 500:  # 500 个样本足够
            break

# 步骤 3: 转换
quantized_model = quant.convert(prepared_model)
```

### 3. 量化感知训练（最佳精度）

```python
# 步骤 1: 准备 QAT
model.qconfig = quant.get_default_qat_qconfig('fbgemm')
prepared_model = quant.prepare_qat(model)

# 步骤 2: 训练（模拟量化）
for epoch in range(10):
    train_one_epoch(prepared_model, train_loader, epoch)

# 步骤 3: 转换
quantized_model = quant.convert(prepared_model.eval())
```

### 4. 简单剪枝

```python
import torch.nn.utils.prune as prune

# 剪枝单个层
prune.l1_unstructured(model.conv1, name='weight', amount=0.5)

# 全局剪枝
parameters_to_prune = [
    (model.conv1, 'weight'),
    (model.conv2, 'weight'),
    (model.fc1, 'weight'),
]
prune.global_unstructured(
    parameters_to_prune,
    pruning_method=prune.L1Unstructured,
    amount=0.5
)

# 永久应用
for module, name in parameters_to_prune:
    prune.remove(module, name)
```

### 5. 知识蒸馏

```python
# 蒸馏损失
def distillation_loss(student_logits, teacher_logits, labels, 
                     temperature=3.0, alpha=0.5):
    # 软标签
    soft_loss = F.kl_div(
        F.log_softmax(student_logits / temperature, dim=1),
        F.softmax(teacher_logits / temperature, dim=1),
        reduction='batchmean'
    ) * (temperature ** 2)
    
    # 硬标签
    hard_loss = F.cross_entropy(student_logits, labels)
    
    return alpha * soft_loss + (1 - alpha) * hard_loss

# 训练循环
teacher_model.eval()
for data, labels in train_loader:
    with torch.no_grad():
        teacher_outputs = teacher_model(data)
    
    student_outputs = student_model(data)
    loss = distillation_loss(
        student_outputs, teacher_outputs, labels
    )
    
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()
```

---

## 📱 TensorFlow Lite 快速实现

### 动态量化

```python
import tensorflow as tf

converter = tf.lite.TFLiteConverter.from_keras_model(model)
converter.optimizations = [tf.lite.Optimize.DEFAULT]
tflite_model = converter.convert()

with open('quantized.tflite', 'wb') as f:
    f.write(tflite_model)
```

### 整数量化（需要校准数据）

```python
def representative_dataset():
    for data in calibration_data.take(100):
        yield [data]

converter.optimizations = [tf.lite.Optimize.DEFAULT]
converter.representative_dataset = representative_dataset
converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
converter.inference_input_type = tf.int8
converter.inference_output_type = tf.int8

tflite_model = converter.convert()
```

---

## 🎯 常见模型压缩方案

### BERT 类模型

| 模型 | 压缩比 | 相对精度 | 推荐场景 |
|------|--------|----------|----------|
| **DistilBERT** | 40% 参数 | 97% | 通用蒸馏 |
| **TinyBERT** | 20% 参数 | 96% | 极限压缩 |
| **MobileBERT** | 25% 参数 | 98% | 移动部署 |
| **BERT-INT8** | 25% 内存 | 99% | 边缘设备 |

### Transformer 类模型

| 技术 | 压缩方法 | 效果 |
|------|----------|------|
| **头剪枝** | 移除不重要的注意力头 | 20-30% 减少 |
| **层剪枝** | 移除中间层 | 30-50% 减少 |
| **隐藏层压缩** | SVD 降维 | 40-60% 减少 |

### CNN 模型

| 技术 | 适用模型 | 效果 |
|------|----------|------|
| **深度可分离卷积** | MobileNet、Xception | 8-9x 加速 |
| **瓶颈层** | ResNet、EfficientNet | 2-4x 压缩 |
| **通道剪枝** | ResNet、VGG | 2-5x 压缩 |

---

## 📈 性能评估模板

```python
def quick_evaluation(model, test_loader):
    """快速评估脚本"""
    import time
    import torch
    
    model.eval()
    device = next(model.parameters()).device
    
    # 1. 精度
    correct = total = 0
    with torch.no_grad():
        for data, labels in test_loader:
            data, labels = data.to(device), labels.to(device)
            outputs = model(data)
            _, predicted = torch.max(outputs.data, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
    
    accuracy = 100 * correct / total
    
    # 2. 推理时间
    data, _ = next(iter(test_loader))
    data = data.to(device)
    
    # 预热
    with torch.no_grad():
        _ = model(data[:1])
    
    # 计时
    start = time.time()
    with torch.no_grad():
        for _ in range(100):
            _ = model(data[:1])
    end = time.time()
    
    avg_time = (end - start) / 100 * 1000  # ms
    
    # 3. 模型大小
    size_mb = sum(p.numel() * p.element_size() 
                  for p in model.parameters()) / (1024 ** 2)
    
    print(f"✅ 精度: {accuracy:.2f}%")
    print(f"⚡ 推理时间: {avg_time:.2f} ms")
    print(f"💾 模型大小: {size_mb:.2f} MB")
    
    return {
        'accuracy': accuracy,
        'inference_time_ms': avg_time,
        'size_mb': size_mb
    }
```

---

## 🎬 典型工作流

### 场景 1: 快速量化（1 小时）

```bash
# 1. 准备校准数据（500-1000 样本）
python prepare_calibration_data.py --num-samples 500

# 2. 静态量化
python quantize_static.py \
    --model checkpoints/model.pth \
    --calibration-data calib_data.pkl \
    --output quantized_model.pth

# 3. 评估
python evaluate.py --model quantized_model.pth

# 预期结果:
# - 模型大小减少 75%
# - 精度下降 0.5-1%
# - 推理速度提升 2-3x
```

### 场景 2: 剪枝 + 量化（1 天）

```bash
# 1. 迭代剪枝
python iterative_pruning.py \
    --model model.pth \
    --target-sparsity 0.7 \
    --iterations 10 \
    --epochs 5

# 2. 微调
python fine_tune.py \
    --model pruned_model.pth \
    --epochs 20

# 3. 量化
python quantize_aware_training.py \
    --model pruned_model.pth \
    --epochs 10

# 预期结果:
# - 模型大小减少 80-90%
# - 精度下降 1-2%
# - 推理速度提升 3-4x
```

### 场景 3: 知识蒸馏（3 天）

```bash
# 1. 训练学生模型
python distillation_train.py \
    --teacher teacher_model.pth \
    --student-arch resnet18 \
    --temperature 3.0 \
    --alpha 0.5 \
    --epochs 100

# 2. 量化
python quantize_aware_training.py \
    --model student_model.pth \
    --epochs 10

# 预期结果:
# - 模型大小减少 70-80%
# - 精度接近教师模型
# - 推理速度提升 2-3x
```

---

## ⚠️ 常见陷阱

### 1. 过度压缩

**问题：** 一次性剪枝 90%+，导致精度崩溃

**解决：** 
- 逐步压缩（每次 10-20%）
- 每次压缩后充分微调

### 2. 忘记微调

**问题：** 压缩后直接使用，精度下降严重

**解决：**
```python
# 压缩后必须微调
for epoch in range(20):  # 至少 10-20 轮
    train_one_epoch(model, train_loader)
    acc = evaluate(model, val_loader)
    print(f"Epoch {epoch}, Acc: {acc:.2%}")
```

### 3. 校准数据不足

**问题：** PTQ 只用 10 个样本校准，精度很差

**解决：**
- 使用 500-1000 个代表性样本
- 确保校准数据覆盖实际使用场景

### 4. 硬件不支持

**问题：** 非结构化剪枝无法加速

**解决：**
- 优先使用结构化剪枝
- 检查硬件是否支持稀疏计算

### 5. 精度评估不全面

**问题：** 只看总体精度，忽略关键类别

**解决：**
```python
# 详细的精度分析
from sklearn.metrics import classification_report

y_pred = model.predict(X_test)
print(classification_report(y_test, y_pred))

# 检查每个类别的精度
```

---

## 📚 推荐阅读顺序

### 初学者（1-2 周）
1. ✅ 量化（PTQ）
2. ✅ 简单剪枝
3. ✅ 快速评估

### 进阶（2-4 周）
1. ✅ 量化感知训练（QAT）
2. ✅ 结构化剪枝
3. ✅ 知识蒸馏基础

### 高级（1-2 月）
1. ✅ 神经网络架构搜索（NAS）
2. ✅ 混合压缩策略
3. ✅ 自定义优化

---

## 🔗 有用的资源

### 论文
- "Deep Compression" (ICLR 2016)
- "Distilling the Knowledge in a Neural Network" (NIPS 2015)
- "Learning Transferable Architectures for Scalable Image Recognition" (CVPR 2019)
- "Quantization and Training of Neural Networks for Efficient Integer-Arithmetic-Only Inference" (CVPR 2018)

### 工具
- **PyTorch:** torch.quantization, torch.nn.utils.prune
- **TensorFlow:** TFLite, Model Optimization Toolkit
- **ONNX:** ONNX Runtime Quantization
- **专用:** Distiller, NVIDIA TensorRT

### 代码示例
- PyTorch 官方教程: [量化](https://pytorch.org/tutorials/advanced/quantization.html)
- Hugging Face: [模型优化](https://huggingface.co/docs/transformers/quantization)

---

## 💡 快速决策指南

**我有 1 小时，想快速减小模型**
→ 动态量化（PTQ）

**我有 1 天，想要好的结果**
→ 静态量化 + 简单剪枝

**我有 1 周，追求最佳质量**
→ QAT + 结构化剪枝 + 微调

**我有 1 月，要设计新模型**
→ 知识蒸馏 + NAS

**我要部署到手机**
→ TFLite INT8 量化

**我要部署到服务器**
→ TensorRT FP16/INT8

**我要最小化存储**
→ 非结构化剪枝 + INT4 量化

---

**快速参考结束**

完整技术细节请参考：`ai-model-compression-techniques.md`
