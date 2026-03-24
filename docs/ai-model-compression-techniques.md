# AI 模型压缩技术完全指南

**版本:** 1.0  
**创建时间:** 2026-03-25  
**目标:** 全面介绍 AI 模型压缩技术，包括剪枝、量化、知识蒸馏和神经网络架构搜索

---

## 目录

1. [概述](#1-概述)
2. [剪枝（Pruning）](#2-剪枝pruning)
3. [量化（Quantization）](#3-量化quantization)
4. [知识蒸馏（Knowledge Distillation）](#4-知识蒸馏knowledge-distillation)
5. [神经网络架构搜索（NAS）](#5-神经网络架构搜索neural-architecture-search)
6. [混合压缩策略](#6-混合压缩策略)
7. [实战应用](#7-实战应用)
8. [工具与框架](#8-工具与框架)
9. [性能评估](#9-性能评估)

---

## 1. 概述

### 1.1 为什么需要模型压缩？

**挑战：**
- **存储限制：** 大型 LLM（如 GPT-3）需要数百 GB 存储空间
- **内存限制：** 推理时需要大量 RAM/VRAM
- **计算成本：** 推理延迟高，能耗大
- **部署困难：** 难以在边缘设备（手机、IoT）上运行

**目标：**
- 减少模型大小（存储和内存占用）
- 降低推理延迟
- 减少能耗
- 保持模型精度

### 1.2 压缩技术对比

| 技术 | 压缩率 | 精度损失 | 实现难度 | 计算开销 |
|------|--------|----------|----------|----------|
| 剪枝 | 2-10x | 小-中 | 中 | 低 |
| 量化 | 2-4x | 小 | 低 | 低 |
| 知识蒸馏 | 2-4x | 小-中 | 高 | 高 |
| NAS | 2-5x | 小 | 很高 | 很高 |
| 混合策略 | 4-20x | 中 | 高 | 中 |

### 1.3 压缩流程

```
原始模型
    ↓
[分析] 评估模型冗余
    ↓
[选择] 选择压缩策略
    ↓
[压缩] 应用压缩技术
    ↓
[微调] 恢复精度
    ↓
[验证] 评估压缩效果
    ↓
压缩模型
```

---

## 2. 剪枝（Pruning）

### 2.1 基本原理

**核心思想：** 移除神经网络中不重要的参数（权重），减少模型大小和计算量。

**类比：** 就像修剪树木，剪掉不重要的枝叶，让树更精干。

### 2.2 剪枝类型

#### 2.2.1 非结构化剪枝（Unstructured Pruning）

**特点：**
- 随机移除单个权重
- 压缩率高，但需要专用硬件支持
- 难以实现实际加速

```python
import torch
import torch.nn as nn
import numpy as np

def unstructured_prune(model, sparsity=0.5):
    """
    非结构化剪枝
    :param model: 要剪枝的模型
    :param sparsity: 稀疏度（0-1），0.5 表示移除 50% 的权重
    """
    for name, param in model.named_parameters():
        if 'weight' in name:
            # 计算阈值
            weight_data = param.data.cpu().abs().numpy()
            threshold = np.percentile(weight_data, sparsity * 100)
            
            # 创建掩码
            mask = param.data.abs() > threshold
            
            # 应用剪枝
            param.data.mul_(mask.float())
            
            print(f"{name}: 剪枝率 {sparsity*100}%, 阈值 {threshold:.6f}")
    
    return model

# 使用示例
model = YourModel()
pruned_model = unstructured_prune(model, sparsity=0.7)  # 剪枝 70%
```

#### 2.2.2 结构化剪枝（Structured Pruning）

**特点：**
- 移除整个通道、滤波器或层
- 易于在标准硬件上加速
- 压缩率相对较低

```python
def structured_prune_conv(model, layer_name, prune_ratio=0.3):
    """
    卷积层通道剪枝
    :param layer_name: 要剪枝的层名
    :param prune_ratio: 剪枝比例
    """
    # 获取目标层
    target_layer = dict(model.named_modules())[layer_name]
    
    # 计算每个输出通道的重要性（L1 范数）
    weight = target_layer.weight.data  # [out_channels, in_channels, h, w]
    importance = torch.abs(weight).sum(dim=(1, 2, 3))  # [out_channels]
    
    # 确定要保留的通道
    num_channels = weight.shape[0]
    num_pruned = int(num_channels * prune_ratio)
    
    # 选择重要性最低的通道
    _, indices_to_prune = torch.topk(importance, num_pruned, largest=False)
    
    # 创建掩码
    mask = torch.ones(num_channels, dtype=torch.bool)
    mask[indices_to_prune] = False
    
    # 应用剪枝
    target_layer.weight.data = target_layer.weight.data[mask]
    target_layer.bias.data = target_layer.bias.data[mask]
    
    print(f"剪枝 {layer_name}: 保留 {mask.sum()}/{num_channels} 通道")
    
    return model, mask

# 使用示例
model, mask = structured_prune_conv(model, 'layer3.0.conv1', prune_ratio=0.3)
```

#### 2.2.3 迭代剪枝（Iterative Pruning）

**策略：** 逐步增加剪枝率，每次剪枝后微调模型。

```python
def iterative_pruning(model, train_loader, test_loader, 
                     target_sparsity=0.9, 
                     iterations=10):
    """
    迭代剪枝流程
    """
    current_sparsity = 0.0
    
    for iteration in range(iterations):
        # 计算本次剪枝率
        iteration_sparsity = target_sparsity * (iteration + 1) / iterations
        
        print(f"\n=== 迭代 {iteration + 1}/{iterations} ===")
        print(f"目标稀疏度: {iteration_sparsity:.2%}")
        
        # 剪枝
        model = unstructured_prune(model, sparsity=iteration_sparsity)
        
        # 微调
        print("微调模型...")
        fine_tune(model, train_loader, epochs=5)
        
        # 评估
        accuracy = evaluate(model, test_loader)
        print(f"精度: {accuracy:.2%}")
        
        current_sparsity = iteration_sparsity
    
    return model
```

### 2.3 剪枝标准

#### 2.3.1 基于幅度（Magnitude-based）

```python
def magnitude_based_pruning(weight, sparsity):
    """基于权重幅度的剪枝"""
    threshold = np.percentile(np.abs(weight), sparsity * 100)
    return np.abs(weight) > threshold
```

#### 2.3.2 基于梯度（Gradient-based）

```python
def gradient_based_pruning(model, data, sparsity):
    """基于梯度的一阶泰勒展开"""
    gradients = compute_gradients(model, data)
    importance = torch.abs(model.weight * gradients)
    threshold = np.percentile(importance, sparsity * 100)
    return importance > threshold
```

#### 2.3.3 基于二阶导数（Hessian-based）

```python
def hessian_based_pruning(model, data):
    """基于 Hessian 矩阵的剪枝（更准确但计算成本高）"""
    # 计算 Hessian 矩阵（近似）
    hessian = compute_hessian_approximation(model, data)
    importance = 0.5 * (model.weight ** 2) * hessian
    return importance
```

### 2.4 Lottery Ticket Hypothesis

**发现：** 在随机初始化的神经网络中，存在一个子网络（中奖彩票），单独训练这个子网络可以达到与完整网络相当甚至更好的性能。

```python
def find_lottery_ticket(model, train_loader, prune_ratio=0.8):
    """
    寻找中奖彩票
    """
    # 1. 保存初始权重
    init_state = {k: v.clone() for k, v in model.state_dict().items()}
    
    # 2. 训练完整模型
    train(model, train_loader, epochs=100)
    trained_state = {k: v.clone() for k, v in model.state_dict().items()}
    
    # 3. 确定剪枝掩码
    masks = {}
    for name, param in model.named_parameters():
        if 'weight' in name:
            threshold = np.percentile(
                np.abs(param.data.cpu()), 
                prune_ratio * 100
            )
            mask = np.abs(param.data.cpu()) > threshold
            masks[name] = mask
    
    # 4. 重置到初始权重
    model.load_state_dict(init_state)
    
    # 5. 应用掩码
    for name, param in model.named_parameters():
        if name in masks:
            param.data *= torch.tensor(masks[name]).to(param.device)
    
    # 6. 只训练掩码内的参数
    train_with_mask(model, train_loader, masks, epochs=100)
    
    return model, masks
```

---

## 3. 量化（Quantization）

### 3.1 基本原理

**核心思想：** 降低参数的数值精度，从 FP32（32 位浮点）降到 INT8（8 位整数）甚至更低。

**收益：**
- 模型大小减少 4 倍（FP32 → INT8）
- 推理速度提升 2-4 倍
- 内存占用减少
- 能耗降低

### 3.2 量化类型

#### 3.2.1 训练后量化（Post-Training Quantization, PTQ）

**优点：** 无需重新训练，快速应用
**缺点：** 精度损失较大

```python
import torch
import torch.quantization

def post_training_quantization(model, calibration_loader):
    """
    训练后动态量化
    """
    # 1. 设置量化配置
    model.qconfig = torch.quantization.get_default_qconfig('fbgemm')
    
    # 2. 准备量化
    prepared_model = torch.quantization.prepare(model)
    
    # 3. 校准（使用代表性数据）
    with torch.no_grad():
        for data, _ in calibration_loader:
            prepared_model(data)
    
    # 4. 转换为量化模型
    quantized_model = torch.quantization.convert(prepared_model)
    
    print(f"模型大小: {get_model_size(model):.2f} MB → "
          f"{get_model_size(quantized_model):.2f} MB")
    
    return quantized_model
```

#### 3.2.2 量化感知训练（Quantization-Aware Training, QAT）

**优点：** 精度损失更小
**缺点：** 需要重新训练

```python
def quantization_aware_training(model, train_loader, test_loader, epochs=10):
    """
    量化感知训练
    """
    # 1. 设置量化配置
    model.qconfig = torch.quantization.get_default_qat_qconfig('fbgemm')
    
    # 2. 准备 QAT
    prepared_model = torch.quantization.prepare_qat(model, inplace=True)
    
    # 3. 训练（模拟量化效果）
    for epoch in range(epochs):
        train_one_epoch(prepared_model, train_loader, epoch)
        accuracy = evaluate(prepared_model, test_loader)
        print(f"Epoch {epoch}, Accuracy: {accuracy:.2%}")
    
    # 4. 转换为真正的量化模型
    quantized_model = torch.quantization.convert(prepared_model.eval())
    
    return quantized_model
```

### 3.3 量化方案

#### 3.3.1 对称量化

```python
def symmetric_quantize(tensor, n_bits=8):
    """
    对称量化
    公式: Q(x) = clamp(round(x / s), -2^(n-1), 2^(n-1)-1)
    """
    # 计算缩放因子
    max_val = torch.max(torch.abs(tensor))
    scale = max_val / (2 ** (n_bits - 1) - 1)
    
    # 量化
    quantized = torch.round(tensor / scale)
    quantized = torch.clamp(
        quantized, 
        -2 ** (n_bits - 1), 
        2 ** (n_bits - 1) - 1
    )
    
    # 反量化（用于验证）
    dequantized = quantized * scale
    
    return quantized, scale, dequantized
```

#### 3.3.2 非对称量化

```python
def asymmetric_quantize(tensor, n_bits=8):
    """
    非对称量化
    公式: Q(x) = clamp(round((x - z) / s), 0, 2^n - 1)
    """
    # 计算缩放因子和零点
    min_val = torch.min(tensor)
    max_val = torch.max(tensor)
    
    q_min = 0
    q_max = 2 ** n_bits - 1
    
    scale = (max_val - min_val) / (q_max - q_min)
    zero_point = q_min - min_val / scale
    
    # 量化
    quantized = torch.round((tensor - zero_point) / scale)
    quantized = torch.clamp(quantized, q_min, q_max)
    
    # 反量化
    dequantized = quantized * scale + zero_point
    
    return quantized, scale, zero_point, dequantized
```

### 3.4 混合精度量化

**策略：** 不同层使用不同精度

```python
def mixed_precision_quantization(model):
    """
    混合精度量化
    - 敏感层：FP16 或 INT16
    - 普通层：INT8
    - 不重要层：INT4
    """
    # 分析每层的重要性
    layer_importance = analyze_layer_importance(model)
    
    # 配置量化方案
    quantization_config = {}
    for name, importance in layer_importance.items():
        if importance > 0.8:
            quantization_config[name] = 'fp16'  # 高重要性
        elif importance > 0.5:
            quantization_config[name] = 'int8'   # 中等重要性
        else:
            quantization_config[name] = 'int4'   # 低重要性
    
    # 应用混合精度量化
    return apply_mixed_precision(model, quantization_config)
```

### 3.5 极端量化（INT4、二值化）

```python
def binary_quantization(weight):
    """
    二值化（1 bit）
    weight = sign(weight) * mean(|weight|)
    """
    scale = torch.mean(torch.abs(weight))
    binary_weight = torch.sign(weight) * scale
    return binary_weight

def ternary_quantization(weight, threshold=0.05):
    """
    三值化（-1, 0, +1）
    """
    # 计算阈值
    delta = threshold * torch.max(torch.abs(weight))
    
    # 量化
    quantized = torch.sign(weight)
    quantized[torch.abs(weight) < delta] = 0
    
    return quantized
```

---

## 4. 知识蒸馏（Knowledge Distillation）

### 4.1 基本原理

**核心思想：** 使用一个大模型（教师模型）训练一个小模型（学生模型），让小模型学习大模型的知识。

**关键：**
- 教师模型：大而强，性能好
- 学生模型：小而快，参数少
- 蒸馏损失：让学生模仿教师的输出

### 4.2 蒸馏方法

#### 4.2.1 响应式蒸馏（Response-based Distillation）

**最简单：** 让学生模仿教师的最终输出

```python
import torch
import torch.nn as nn
import torch.nn.functional as F

class DistillationLoss(nn.Module):
    """
    蒸馏损失
    """
    def __init__(self, temperature=3.0, alpha=0.5):
        super().__init__()
        self.temperature = temperature
        self.alpha = alpha
    
    def forward(self, student_logits, teacher_logits, labels):
        """
        :param student_logits: 学生模型的输出
        :param teacher_logits: 教师模型的输出
        :param labels: 真实标签
        """
        # 软标签损失（蒸馏）
        soft_loss = F.kl_div(
            F.log_softmax(student_logits / self.temperature, dim=1),
            F.softmax(teacher_logits / self.temperature, dim=1),
            reduction='batchmean'
        ) * (self.temperature ** 2)
        
        # 硬标签损失（真实标签）
        hard_loss = F.cross_entropy(student_logits, labels)
        
        # 组合损失
        loss = self.alpha * soft_loss + (1 - self.alpha) * hard_loss
        
        return loss

# 训练循环
def distillation_train(student_model, teacher_model, train_loader, 
                       temperature=3.0, alpha=0.5, epochs=10):
    teacher_model.eval()  # 教师模型不训练
    criterion = DistillationLoss(temperature=temperature, alpha=alpha)
    optimizer = torch.optim.Adam(student_model.parameters())
    
    for epoch in range(epochs):
        for data, labels in train_loader:
            # 教师模型前向传播
            with torch.no_grad():
                teacher_outputs = teacher_model(data)
            
            # 学生模型前向传播
            student_outputs = student_model(data)
            
            # 计算蒸馏损失
            loss = criterion(student_outputs, teacher_outputs, labels)
            
            # 反向传播
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
        
        print(f"Epoch {epoch}, Loss: {loss.item():.4f}")
    
    return student_model
```

#### 4.2.2 特征式蒸馏（Feature-based Distillation）

**进阶：** 让学生模仿教师中间层的特征

```python
class FeatureDistillationLoss(nn.Module):
    """
    特征蒸馏损失
    """
    def __init__(self, loss_type='mse'):
        super().__init__()
        self.loss_type = loss_type
    
    def forward(self, student_features, teacher_features):
        """
        :param student_features: 学生模型的中间特征
        :param teacher_features: 教师模型的中间特征
        """
        if self.loss_type == 'mse':
            loss = F.mse_loss(student_features, teacher_features)
        elif self.loss_type == 'cosine':
            loss = 1 - F.cosine_similarity(
                student_features.flatten(1),
                teacher_features.flatten(1)
            ).mean()
        else:
            raise ValueError(f"Unknown loss type: {self.loss_type}")
        
        return loss

# 多层特征蒸馏
def multi_layer_feature_distillation(student, teacher, inputs):
    """
    同时蒸馏多个中间层
    """
    # 提取教师特征
    with torch.no_grad():
        teacher_features = teacher.extract_features(inputs)
    
    # 提取学生特征
    student_features = student.extract_features(inputs)
    
    # 计算每层的蒸馏损失
    total_loss = 0
    for s_feat, t_feat in zip(student_features, teacher_features):
        # 如果维度不匹配，使用适配器
        if s_feat.shape != t_feat.shape:
            s_feat = student.adapter(s_feat)
        
        loss = F.mse_loss(s_feat, t_feat)
        total_loss += loss
    
    return total_loss / len(student_features)
```

#### 4.2.3 关系式蒸馏（Relation-based Distillation）

**高级：** 学习样本之间的关系

```python
class RelationDistillationLoss(nn.Module):
    """
    关系蒸馏损失
    学习样本之间的相似性关系
    """
    def __init__(self):
        super().__init__()
    
    def forward(self, student_features, teacher_features):
        """
        计算特征之间的相似性矩阵
        """
        # 计算相似性矩阵
        student_sim = self.compute_similarity(student_features)
        teacher_sim = self.compute_similarity(teacher_features)
        
        # 最小化差异
        loss = F.mse_loss(student_sim, teacher_sim)
        
        return loss
    
    def compute_similarity(self, features):
        """
        计算特征之间的余弦相似性
        """
        features = F.normalize(features, p=2, dim=1)
        similarity = torch.mm(features, features.t())
        return similarity
```

### 4.3 自蒸馏（Self-Distillation）

**创新：** 模型自己教自己

```python
def self_distillation(model, train_loader, epochs=10):
    """
    自蒸馏：使用模型自身的过去版本作为教师
    """
    # 保存初始模型作为教师
    teacher = copy.deepcopy(model)
    
    for epoch in range(epochs):
        # 训练学生
        for data, labels in train_loader:
            with torch.no_grad():
                teacher_outputs = teacher(data)
            
            student_outputs = model(data)
            loss = distillation_loss(student_outputs, teacher_outputs, labels)
            
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
        
        # 更新教师（指数移动平均）
        with torch.no_grad():
            for teacher_param, student_param in zip(
                teacher.parameters(), model.parameters()
            ):
                teacher_param.data = (
                    0.99 * teacher_param.data + 
                    0.01 * student_param.data
                )
    
    return model
```

---

## 5. 神经网络架构搜索（NAS）

### 5.1 基本概念

**目标：** 自动设计最优的网络架构

**搜索空间：**
- 操作：卷积、池化、跳跃连接等
- 层数：深度
- 通道数：宽度
- 连接模式：拓扑结构

### 5.2 NAS 方法

#### 5.2.1 强化学习（RL-based NAS）

```python
class ControllerRNN(nn.Module):
    """
    控制器 RNN，用于生成网络架构
    """
    def __init__(self, search_space, hidden_size=64):
        super().__init__()
        self.search_space = search_space
        self.hidden_size = hidden_size
        
        self.rnn = nn.RNN(
            input_size=len(search_space),
            hidden_size=hidden_size,
            num_layers=1
        )
        self.fc = nn.Linear(hidden_size, len(search_space))
    
    def forward(self, num_layers):
        """
        生成网络架构
        """
        h = torch.zeros(1, 1, self.hidden_size)
        architecture = []
        
        for _ in range(num_layers):
            output, h = self.rnn(torch.zeros(1, 1, len(self.search_space)), h)
            probs = F.softmax(self.fc(output.squeeze(1)), dim=0)
            operation = torch.multinomial(probs, 1)
            architecture.append(operation.item())
        
        return architecture

# NAS 训练循环
def train_nas(controller, train_loader, val_loader, episodes=100):
    """
    使用强化学习搜索架构
    """
    optimizer = torch.optim.Adam(controller.parameters())
    baseline = None
    
    for episode in range(episodes):
        # 1. 采样架构
        architecture = controller(num_layers=10)
        
        # 2. 构建并训练子网络
        child_net = build_network(architecture)
        train_child_network(child_net, train_loader, epochs=5)
        
        # 3. 评估
        reward = evaluate(child_net, val_loader)
        
        # 4. 更新基线（移动平均）
        if baseline is None:
            baseline = reward
        else:
            baseline = 0.9 * baseline + 0.1 * reward
        
        # 5. 计算策略梯度
        policy_loss = -(reward - baseline) * compute_log_prob(
            controller, architecture
        )
        
        # 6. 更新控制器
        optimizer.zero_grad()
        policy_loss.backward()
        optimizer.step()
        
        print(f"Episode {episode}, Reward: {reward:.2%}, "
              f"Best: {baseline:.2%}")
```

#### 5.2.2 可微分架构搜索（DARTS）

```python
class DARTSCell(nn.Module):
    """
    DARTS 可微分单元
    """
    def __init__(self, C, num_ops):
        super().__init__()
        self.ops = nn.ModuleList()
        for op in range(num_ops):
            self.ops.append(get_operation(op, C))
        
        # 架构参数（可微分）
        self.arch_parameters = nn.Parameter(
            torch.randn(num_ops)
        )
    
    def forward(self, x):
        """
        混合操作：所有操作的加权和
        """
        # Softmax 归一化权重
        weights = F.softmax(self.arch_parameters, dim=0)
        
        # 加权求和所有操作
        output = sum(w * op(x) for w, op in zip(weights, self.ops))
        
        return output

# DARTS 训练
def train_darts(model, train_loader, val_loader, epochs=50):
    """
    DARTS 双层优化
    """
    # 两类参数
    net_weights = [p for n, p in model.named_parameters() 
                   if 'arch' not in n]
    arch_parameters = [p for n, p in model.named_parameters() 
                      if 'arch' in n]
    
    optimizer_w = torch.optim.SGD(net_weights, lr=0.025, momentum=0.9)
    optimizer_a = torch.optim.Adam(arch_parameters, lr=3e-4)
    
    for epoch in range(epochs):
        # 训练网络权重
        model.train()
        for data, labels in train_loader:
            optimizer_w.zero_grad()
            loss = model.loss(data, labels)
            loss.backward()
            optimizer_w.step()
        
        # 更新架构参数
        model.eval()
        for data, labels in val_loader:
            optimizer_a.zero_grad()
            val_loss = model.loss(data, labels)
            val_loss.backward()
            optimizer_a.step()
        
        print(f"Epoch {epoch}, Loss: {loss.item():.4f}, "
              f"Val Loss: {val_loss.item():.4f}")
    
    # 提取最终架构
    final_architecture = model.extract_architecture()
    return final_architecture
```

#### 5.2.3 One-Shot NAS

```python
class SuperNet(nn.Module):
    """
    超网络：包含所有可能的架构
    """
    def __init__(self, search_space):
        super().__init__()
        self.search_space = search_space
        self.blocks = nn.ModuleList()
        
        for block_id in range(10):  # 10 层
            block = MixedOp(search_space)
            self.blocks.append(block)
    
    def forward(self, x, architecture=None):
        """
        :param architecture: 指定架构，None 则采样
        """
        for block in self.blocks:
            if architecture is None:
                # 随机采样操作
                op = block.sample_random()
            else:
                # 使用指定架构
                op = block.select_op(architecture)
            x = op(x)
        
        return x

# 进化算法搜索
def evolutionary_search(supernet, val_loader, population_size=50, 
                       generations=100):
    """
    使用进化算法搜索架构
    """
    # 1. 初始化种群
    population = [random_architecture() for _ in range(population_size)]
    
    for generation in range(generations):
        # 2. 评估所有个体
        fitness = []
        for arch in population:
            accuracy = evaluate_architecture(supernet, arch, val_loader)
            fitness.append(accuracy)
        
        # 3. 选择（锦标赛选择）
        parents = tournament_selection(population, fitness)
        
        # 4. 交叉
        offspring = crossover(parents)
        
        # 5. 变异
        offspring = mutate(offspring, mutation_rate=0.1)
        
        # 6. 更新种群
        population = parents + offspring
        population = sorted(population, key=lambda x: fitness[population.index(x)])
        population = population[:population_size]
        
        best_fitness = max(fitness)
        print(f"Generation {generation}, Best: {best_fitness:.2%}")
    
    return population[0]  # 返回最佳架构
```

### 5.3 效率提升策略

#### 5.3.1 权重共享

```python
class WeightSharingSuperNet(nn.Module):
    """
    权重共享：所有子网络共享权重
    """
    def __init__(self):
        super().__init__()
        # 共享的权重
        self.shared_weights = nn.ParameterDict()
        
        # 定义搜索空间
        self.search_space = {
            'conv3x3': nn.Conv2d(32, 32, 3),
            'conv5x5': nn.Conv2d(32, 32, 5),
            'maxpool': nn.MaxPool2d(2),
            'avgpool': nn.AvgPool2d(2),
            'skip': nn.Identity(),
        }
        
        for name, op in self.search_space.items():
            self.shared_weights[name] = op.parameters
    
    def forward(self, x, selected_ops):
        """
        :param selected_ops: 选择的操作列表
        """
        for op_name in selected_ops:
            op = self.search_space[op_name]
            x = op(x)
        return x
```

#### 5.3.2 早停策略

```python
def early_stop_nas(supernet, train_loader, val_loader, 
                  max_epochs=100, patience=10):
    """
    带早停的 NAS
    """
    best_val_acc = 0
    patience_counter = 0
    
    for epoch in range(max_epochs):
        # 训练
        train_epoch(supernet, train_loader)
        
        # 验证
        val_acc = validate(supernet, val_loader)
        
        # 检查是否提升
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            patience_counter = 0
            save_checkpoint(supernet, 'best_model.pth')
        else:
            patience_counter += 1
        
        # 早停
        if patience_counter >= patience:
            print(f"Early stopping at epoch {epoch}")
            break
        
        print(f"Epoch {epoch}, Val Acc: {val_acc:.2%}")
    
    return load_checkpoint('best_model.pth')
```

---

## 6. 混合压缩策略

### 6.1 组合策略

**最佳实践：** 结合多种技术

```python
def hybrid_compression(model, train_loader, val_loader):
    """
    混合压缩流程
    1. 知识蒸馏：训练小模型
    2. 量化：降低精度
    3. 剪枝：移除冗余参数
    4. 微调：恢复精度
    """
    print("=== 阶段 1: 知识蒸馏 ===")
    # 创建学生模型（宽度减半）
    student_model = create_student_model(model, width_ratio=0.5)
    
    # 蒸馏训练
    student_model = distillation_train(
        student_model, model, train_loader, epochs=20
    )
    
    print("\n=== 阶段 2: 量化感知训练 ===")
    # 量化
    student_model.qconfig = torch.quantization.get_default_qat_qconfig('fbgemm')
    prepared_model = torch.quantization.prepare_qat(student_model)
    
    # 继续训练
    for epoch in range(10):
        train_one_epoch(prepared_model, train_loader, epoch)
    
    print("\n=== 阶段 3: 结构化剪枝 ===")
    # 剪枝
    pruned_model, masks = structured_prune_conv(
        prepared_model, 'layer3.0.conv1', prune_ratio=0.3
    )
    
    print("\n=== 阶段 4: 微调 ===")
    # 微调恢复精度
    fine_tune(pruned_model, train_loader, epochs=15)
    
    print("\n=== 阶段 5: 转换为量化模型 ===")
    # 最终转换
    quantized_model = torch.quantization.convert(pruned_model)
    
    # 评估
    final_acc = evaluate(quantized_model, val_loader)
    print(f"\n最终精度: {final_acc:.2%}")
    print(f"压缩比: {compute_compression_ratio(model, quantized_model):.2f}x")
    
    return quantized_model
```

### 6.2 逐步压缩策略

```python
def progressive_compression(model, train_loader, val_loader):
    """
    逐步压缩：每步压缩后都微调
    """
    compression_schedule = [
        {'method': 'prune', 'ratio': 0.2, 'epochs': 5},
        {'method': 'prune', 'ratio': 0.3, 'epochs': 5},
        {'method': 'quantize', 'bits': 8, 'epochs': 10},
        {'method': 'prune', 'ratio': 0.4, 'epochs': 5},
        {'method': 'quantize', 'bits': 4, 'epochs': 10},
    ]
    
    current_model = model
    
    for step, schedule in enumerate(compression_schedule):
        print(f"\n=== 压缩步骤 {step + 1} ===")
        print(f"方法: {schedule['method']}, "
              f"参数: {schedule.get('ratio') or schedule.get('bits')}")
        
        if schedule['method'] == 'prune':
            current_model = structured_prune_conv(
                current_model, 
                schedule['layer'], 
                schedule['ratio']
            )
        elif schedule['method'] == 'quantize':
            current_model = quantize_model(
                current_model, 
                schedule['bits']
            )
        
        # 微调
        fine_tune(current_model, train_loader, schedule['epochs'])
        
        # 评估
        acc = evaluate(current_model, val_loader)
        print(f"当前精度: {acc:.2%}")
    
    return current_model
```

### 6.3 AutoML 压缩

```python
def automl_compression_search(model, train_loader, val_loader):
    """
    自动搜索最佳压缩策略
    """
    # 定义搜索空间
    search_space = {
        'prune_ratio': [0.3, 0.5, 0.7],
        'quant_bits': [8, 4],
        'distill_temp': [2.0, 3.0, 5.0],
        'ft_epochs': [5, 10, 15],
    }
    
    best_config = None
    best_score = 0
    
    # 网格搜索（也可以用贝叶斯优化）
    for prune_ratio in search_space['prune_ratio']:
        for quant_bits in search_space['quant_bits']:
            for distill_temp in search_space['distill_temp']:
                # 尝试配置
                config = {
                    'prune_ratio': prune_ratio,
                    'quant_bits': quant_bits,
                    'distill_temp': distill_temp,
                }
                
                # 应用压缩
                compressed_model = apply_compression(
                    model, train_loader, config
                )
                
                # 评估
                acc = evaluate(compressed_model, val_loader)
                size = get_model_size(compressed_model)
                
                # 综合评分
                score = acc / (size / get_model_size(model))
                
                print(f"配置: {config}, 精度: {acc:.2%}, "
                      f"大小: {size:.2f}MB, 评分: {score:.3f}")
                
                if score > best_score:
                    best_score = score
                    best_config = config
    
    print(f"\n最佳配置: {best_config}, 评分: {best_score:.3f}")
    return best_config
```

---

## 7. 实战应用

### 7.1 压缩 Transformer 模型

```python
def compress_transformer(model, train_loader, val_loader):
    """
    专门针对 Transformer 的压缩
    """
    # 1. 注意力头剪枝
    def prune_attention_heads(model, heads_to_prune):
        """
        剪枝不重要的注意力头
        :param heads_to_prune: 每层要剪枝的头数
        """
        for layer_idx, num_prune in enumerate(heads_to_prune):
            attention = model.transformer.layers[layer_idx].attention
            
            # 计算每个头的重要性
            head_importance = []
            for head_idx in range(attention.num_heads):
                head_weight = attention.out_proj.weight[
                    head_idx * attention.head_dim : 
                    (head_idx + 1) * attention.head_dim
                ]
                importance = torch.abs(head_weight).sum().item()
                head_importance.append((importance, head_idx))
            
            # 选择重要性最低的头进行剪枝
            head_importance.sort()
            heads_to_remove = [h for _, h in head_importance[:num_prune]]
            
            # 修改注意力层配置
            attention.num_heads -= num_prune
            # 重新初始化权重（保留重要头）
            prune_heads(attention, heads_to_remove)
        
        return model
    
    # 2. 隐藏层维度压缩
    def compress_hidden_dim(model, compression_ratio=0.5):
        """
        压缩隐藏层维度
        """
        original_dim = model.config.hidden_size
        new_dim = int(original_dim * compression_ratio)
        
        # 使用 SVD 分解压缩线性层
        for name, module in model.named_modules():
            if isinstance(module, nn.Linear):
                weight = module.weight.data
                U, S, V = torch.svd(weight)
                
                # 保留前 new_dim 个奇异值
                compressed_weight = U[:, :new_dim] @ torch.diag(S[:new_dim]) @ V.t()[:, :new_dim].t()
                
                # 替换权重
                module.weight = nn.Parameter(compressed_weight)
                module.in_features = new_dim
                module.out_features = new_dim
        
        model.config.hidden_size = new_dim
        return model
    
    # 3. 层剪枝（移除整个 Transformer 层）
    def prune_layers(model, num_layers_to_remove):
        """
        移除中间的 Transformer 层
        """
        original_layers = model.transformer.layers
        total_layers = len(original_layers)
        
        # 移除中间层（保留首尾）
        keep_indices = list(range(
            (total_layers - num_layers_to_remove) // 2
        )) + list(range(
            total_layers - (total_layers - num_layers_to_remove) // 2,
            total_layers
        ))
        
        model.transformer.layers = nn.ModuleList([
            original_layers[i] for i in keep_indices
        ])
        model.config.num_hidden_layers -= num_layers_to_remove
        
        return model
    
    # 应用压缩
    print("步骤 1: 注意力头剪枝")
    model = prune_attention_heads(model, heads_to_prune=[2, 2, 2, 2])
    
    print("步骤 2: 隐藏层维度压缩")
    model = compress_hidden_dim(model, compression_ratio=0.7)
    
    print("步骤 3: Transformer 层剪枝")
    model = prune_layers(model, num_layers_to_remove=2)
    
    print("步骤 4: 微调")
    fine_tune(model, train_loader, epochs=20)
    
    return model
```

### 7.2 压缩 CNN 模型

```python
def compress_cnn(model, train_loader, val_loader):
    """
    专门针对 CNN 的压缩
    """
    # 1. 深度可分离卷积替换
    def replace_with_depthwise(model):
        """
        将标准卷积替换为深度可分离卷积
        """
        for name, module in list(model.named_children()):
            if isinstance(module, nn.Conv2d):
                if module.groups == 1:  # 标准卷积
                    # 深度卷积
                    depthwise = nn.Conv2d(
                        module.in_channels,
                        module.in_channels,
                        kernel_size=module.kernel_size,
                        stride=module.stride,
                        padding=module.padding,
                        groups=module.in_channels,
                        bias=False
                    )
                    
                    # 逐点卷积
                    pointwise = nn.Conv2d(
                        module.in_channels,
                        module.out_channels,
                        kernel_size=1,
                        bias=module.bias is not None
                    )
                    
                    # 组合
                    sequential = nn.Sequential(depthwise, pointwise)
                    setattr(model, name, sequential)
        
        return model
    
    # 2. 瓶颈层替换（MobileNet 风格）
    def replace_with_bottleneck(model):
        """
        使用瓶颈结构减少计算量
        """
        bottleneck = nn.Sequential(
            # 1x1 降维
            nn.Conv2d(in_channels, in_channels // 4, 1),
            nn.BatchNorm2d(in_channels // 4),
            nn.ReLU6(inplace=True),
            
            # 3x3 深度卷积
            nn.Conv2d(in_channels // 4, in_channels // 4, 3, 
                     padding=1, groups=in_channels // 4),
            nn.BatchNorm2d(in_channels // 4),
            nn.ReLU6(inplace=True),
            
            # 1x1 升维
            nn.Conv2d(in_channels // 4, out_channels, 1),
            nn.BatchNorm2d(out_channels)
        )
        
        return bottleneck
    
    # 3. 空间分离卷积
    def spatially_separable_convolution(in_channels, out_channels, kernel_size):
        """
        将 k×k 卷积分解为 k×1 和 1×k 卷积
        """
        return nn.Sequential(
            nn.Conv2d(in_channels, in_channels, 
                     kernel_size=(kernel_size, 1), 
                     padding=(kernel_size // 2, 0)),
            nn.Conv2d(in_channels, out_channels, 
                     kernel_size=(1, kernel_size), 
                     padding=(0, kernel_size // 2))
        )
    
    # 应用压缩
    print("步骤 1: 替换为深度可分离卷积")
    model = replace_with_depthwise(model)
    
    print("步骤 2: 剪枝通道")
    for name, module in model.named_modules():
        if isinstance(module, nn.Conv2d):
            prune_conv_channels(module, ratio=0.3)
    
    print("步骤 3: 微调")
    fine_tune(model, train_loader, epochs=15)
    
    return model
```

### 7.3 压缩 BERT 类模型

```python
def compress_bert(model, train_loader, val_loader):
    """
    专门针对 BERT 的压缩
    """
    # 1. DistilBERT 风格蒸馏
    def distill_bert(teacher_model, student_model, train_loader):
        """
        BERT 蒸馏训练
        """
        # 损失函数组合
        def distillation_loss(
            student_logits, teacher_logits, 
            student_hidden, teacher_hidden,
            labels, alpha=0.5, temperature=2.0
        ):
            # 软标签损失
            soft_loss = F.kl_div(
                F.log_softmax(student_logits / temperature, dim=-1),
                F.softmax(teacher_logits / temperature, dim=-1),
                reduction='batchmean'
            ) * (temperature ** 2)
            
            # 隐藏状态损失
            hidden_loss = F.mse_loss(
                student_hidden[:, 0],  # [CLS] token
                teacher_hidden[:, 0]
            )
            
            # 硬标签损失
            hard_loss = F.cross_entropy(
                student_logits.view(-1, student_logits.size(-1)),
                labels.view(-1)
            )
            
            return alpha * soft_loss + (1 - alpha) * hard_loss + 0.1 * hidden_loss
        
        # 训练
        optimizer = torch.optim.Adam(student_model.parameters())
        teacher_model.eval()
        
        for epoch in range(10):
            for batch in train_loader:
                # 教师前向传播
                with torch.no_grad():
                    teacher_outputs = teacher_model(**batch)
                    teacher_logits = teacher_outputs.logits
                    teacher_hidden = teacher_outputs.hidden_states[-1]
                
                # 学生前向传播
                student_outputs = student_model(**batch)
                student_logits = student_outputs.logits
                student_hidden = student_outputs.hidden_states[-1]
                
                # 计算损失
                loss = distillation_loss(
                    student_logits, teacher_logits,
                    student_hidden, teacher_hidden,
                    batch['labels']
                )
                
                # 反向传播
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
        
        return student_model
    
    # 2. 层初始化策略
    def initialize_student_from_teacher(teacher, student):
        """
        从教师模型初始化学生模型
        - 学生每 2 层对应教师的 1 层
        """
        teacher_layers = teacher.bert.encoder.layer
        student_layers = student.bert.encoder.layer
        
        for i in range(len(student_layers)):
            # 选择对应的教师层
            teacher_idx = i * 2
            if teacher_idx < len(teacher_layers):
                # 复制权重
                student_layers[i].load_state_dict(
                    teacher_layers[teacher_idx].state_dict()
                )
        
        return student
    
    # 应用压缩
    print("步骤 1: 创建学生模型（6 层）")
    student_model = create_distil_bert(num_layers=6)
    
    print("步骤 2: 从教师初始化")
    student_model = initialize_student_from_teacher(model, student_model)
    
    print("步骤 3: 蒸馏训练")
    student_model = distill_bert(model, student_model, train_loader)
    
    print("步骤 4: 量化")
    student_model = torch.quantization.quantize_dynamic(
        student_model, {nn.Linear}, dtype=torch.qint8
    )
    
    return student_model
```

---

## 8. 工具与框架

### 8.1 PyTorch 量化工具

```python
import torch.quantization as quant

# 动态量化
dynamic_quantized_model = quant.quantize_dynamic(
    model, 
    {nn.Linear, nn.LSTM, nn.GRU},  # 要量化的层类型
    dtype=torch.qint8              # 目标数据类型
)

# 静态量化
model.qconfig = quant.get_default_qconfig('fbgemm')
prepared_model = quant.prepare(model)

# 校准
with torch.no_grad():
    for data in calibration_data:
        prepared_model(data)

# 转换
quantized_model = quant.convert(prepared_model)

# QAT
model.qconfig = quant.get_default_qat_qconfig('fbgemm')
prepared_model = quant.prepare_qat(model)
# 训练...
quantized_model = quant.convert(prepared_model.eval())
```

### 8.2 TensorFlow Lite

```python
import tensorflow as tf

# 转换为 TFLite
converter = tf.lite.TFLiteConverter.from_keras_model(model)

# 量化配置
converter.optimizations = [tf.lite.Optimize.DEFAULT]
converter.target_spec.supported_types = [tf.float16]  # FP16 量化

# 整数量化
def representative_dataset():
    for data in calibration_data.take(100):
        yield [data]

converter.optimizations = [tf.lite.Optimize.DEFAULT]
converter.representative_dataset = representative_dataset
converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
converter.inference_input_type = tf.int8
converter.inference_output_type = tf.int8

# 转换
tflite_model = converter.convert()

# 保存
with open('quantized_model.tflite', 'wb') as f:
    f.write(tflite_model)
```

### 8.3 ONNX Runtime

```python
import onnxruntime as ort
from onnxruntime.quantization import quantize_dynamic, QuantType

# 动态量化
quantized_model = 'quantized_model.onnx'
quantize_dynamic(
    'model.onnx',
    quantized_model,
    weight_type=QuantType.QUInt8  # 或 QInt8
)

# 静态量化
from onnxruntime.quantization import quantize_static, CalibrationDataReader

class MyCalibrationDataReader(CalibrationDataReader):
    def __init__(self, data_loader):
        self.data_loader = data_loader
    
    def get_next(self):
        for data in self.data_loader:
            yield {'input': data.numpy()}

quantize_static(
    'model.onnx',
    'static_quantized.onnx',
    MyCalibrationDataReader(calibration_loader)
)

# 推理
session = ort.InferenceSession(quantized_model)
outputs = session.run(None, {'input': input_data})
```

### 8.4 专用框架

#### 8.4.1 Torch pruning

```python
import torch.nn.utils.prune as prune

# 全局非结构化剪枝
parameters_to_prune = [
    (model.conv1, 'weight'),
    (model.conv2, 'weight'),
    (model.fc1, 'weight'),
]

prune.global_unstructured(
    parameters_to_prune,
    pruning_method=prune.L1Unstructured,
    amount=0.5  # 剪枝 50%
)

# 移除掩码（永久剪枝）
for module, name in parameters_to_prune:
    prune.remove(module, name)
```

#### 8.4.2 Distiller

```python
# 来自 NLP-Microsoft 的 Distiller 框架
from distiller import model_deployer

# 配置压缩
compression_scheduler = model_deployer.CompressionScheduler([
    {
        'type': 'magnitude_pruner',
        'params': {'sparsity': 0.8}
    },
    {
        'type': 'quantizer',
        'params': {'bits': 8}
    }
])

# 应用压缩
model_deployer.compress_model(
    model,
    compression_scheduler,
    train_loader=train_loader,
    eval_loader=val_loader
)
```

---

## 9. 性能评估

### 9.1 评估指标

```python
def evaluate_compression(original_model, compressed_model, 
                        test_loader, device='cuda'):
    """
    全面评估压缩效果
    """
    results = {}
    
    # 1. 精度评估
    original_acc = evaluate_accuracy(original_model, test_loader, device)
    compressed_acc = evaluate_accuracy(compressed_model, test_loader, device)
    
    results['accuracy'] = {
        'original': original_acc,
        'compressed': compressed_acc,
        'drop': original_acc - compressed_acc,
        'drop_percentage': (original_acc - compressed_acc) / original_acc * 100
    }
    
    # 2. 模型大小
    original_size = get_model_size(original_model)
    compressed_size = get_model_size(compressed_model)
    
    results['size'] = {
        'original_mb': original_size,
        'compressed_mb': compressed_size,
        'compression_ratio': original_size / compressed_size,
        'reduction_percentage': (1 - compressed_size / original_size) * 100
    }
    
    # 3. 推理速度
    original_time = measure_inference_time(original_model, test_loader, device)
    compressed_time = measure_inference_time(compressed_model, test_loader, device)
    
    results['inference'] = {
        'original_ms': original_time,
        'compressed_ms': compressed_time,
        'speedup': original_time / compressed_time
    }
    
    # 4. 内存占用
    original_memory = get_memory_usage(original_model, device)
    compressed_memory = get_memory_usage(compressed_model, device)
    
    results['memory'] = {
        'original_mb': original_memory,
        'compressed_mb': compressed_memory,
        'reduction': (1 - compressed_memory / original_memory) * 100
    }
    
    # 5. 能耗估算
    original_energy = estimate_energy(original_model, test_loader, device)
    compressed_energy = estimate_energy(compressed_model, test_loader, device)
    
    results['energy'] = {
        'original_joules': original_energy,
        'compressed_joules': compressed_energy,
        'savings': (1 - compressed_energy / original_energy) * 100
    }
    
    return results

def print_evaluation_report(results):
    """
    打印评估报告
    """
    print("=" * 60)
    print("模型压缩评估报告")
    print("=" * 60)
    
    print("\n📊 精度:")
    print(f"  原始模型: {results['accuracy']['original']:.2%}")
    print(f"  压缩模型: {results['accuracy']['compressed']:.2%}")
    print(f"  精度下降: {results['accuracy']['drop_percentage']:.2f}%")
    
    print("\n💾 模型大小:")
    print(f"  原始模型: {results['size']['original_mb']:.2f} MB")
    print(f"  压缩模型: {results['size']['compressed_mb']:.2f} MB")
    print(f"  压缩比: {results['size']['compression_ratio']:.2f}x")
    print(f"  大小减少: {results['size']['reduction_percentage']:.1f}%")
    
    print("\n⚡ 推理速度:")
    print(f"  原始模型: {results['inference']['original_ms']:.2f} ms")
    print(f"  压缩模型: {results['inference']['compressed_ms']:.2f} ms")
    print(f"  加速比: {results['inference']['speedup']:.2f}x")
    
    print("\n🧠 内存占用:")
    print(f"  原始模型: {results['memory']['original_mb']:.2f} MB")
    print(f"  压缩模型: {results['memory']['compressed_mb']:.2f} MB")
    print(f"  内存节省: {results['memory']['reduction']:.1f}%")
    
    print("\n🔋 能耗:")
    print(f"  原始模型: {results['energy']['original_joules']:.2f} J")
    print(f"  压缩模型: {results['energy']['compressed_joules']:.2f} J")
    print(f"  节能: {results['energy']['savings']:.1f}%")
    
    print("\n" + "=" * 60)
```

### 9.2 权衡分析

```python
def plot_pareto_frontier(results_list):
    """
    绘制帕累托前沿（精度 vs 大小）
    """
    import matplotlib.pyplot as plt
    
    sizes = [r['size']['compressed_mb'] for r in results_list]
    accuracies = [r['accuracy']['compressed'] for r in results_list]
    
    plt.figure(figsize=(10, 6))
    plt.scatter(sizes, accuracies, c='blue', alpha=0.6)
    
    # 标注 Pareto 最优点
    pareto_points = find_pareto_optimal(sizes, accuracies)
    plt.scatter(
        [sizes[i] for i in pareto_points],
        [accuracies[i] for i in pareto_points],
        c='red', s=100, marker='*'
    )
    
    plt.xlabel('模型大小 (MB)')
    plt.ylabel('精度 (%)')
    plt.title('精度-大小权衡')
    plt.grid(True)
    plt.show()

def find_pareto_optimal(sizes, accuracies):
    """
    找到帕累托最优点
    """
    pareto = []
    for i, (s, a) in enumerate(zip(sizes, accuracies)):
        is_dominated = False
        for j, (s_other, a_other) in enumerate(zip(sizes, accuracies)):
            if i != j:
                if s_other <= s and a_other >= a:
                    is_dominated = True
                    break
        if not is_dominated:
            pareto.append(i)
    return pareto
```

### 9.3 实际部署测试

```python
def real_world_benchmark(model, test_cases):
    """
    真实场景性能测试
    """
    benchmarks = {
        'mobile': {
            'device': 'iPhone 14',
            'framework': 'Core ML',
            'batch_size': 1
        },
        'edge': {
            'device': 'Raspberry Pi 4',
            'framework': 'TFLite',
            'batch_size': 1
        },
        'server': {
            'device': 'NVIDIA T4',
            'framework': 'TensorRT',
            'batch_size': 32
        }
    }
    
    results = {}
    
    for platform, config in benchmarks.items():
        print(f"测试平台: {platform} ({config['device']})")
        
        # 转换模型
        converted_model = convert_model_for_platform(
            model, 
            config['framework']
        )
        
        # 运行基准测试
        latencies = []
        throughputs = []
        
        for i in range(100):
            start = time.time()
            output = converted_model.run(test_cases[i])
            end = time.time()
            
            latencies.append((end - start) * 1000)  # ms
            throughputs.append(1 / (end - start))    # QPS
        
        results[platform] = {
            'avg_latency_ms': np.mean(latencies),
            'p99_latency_ms': np.percentile(latencies, 99),
            'throughput_qps': np.mean(throughputs),
            'memory_mb': get_memory_footprint(converted_model)
        }
    
    return results
```

---

## 总结

### 核心技术对比

| 技术 | 适用场景 | 压缩比 | 实现难度 | 精度影响 |
|------|----------|--------|----------|----------|
| **剪枝** | 有冗余参数的模型 | 2-10x | ⭐⭐⭐ | 小-中 |
| **量化** | 部署到边缘设备 | 2-4x | ⭐⭐ | 小 |
| **知识蒸馏** | 训练新模型 | 2-4x | ⭐⭐⭐⭐ | 小-中 |
| **NAS** | 设计新架构 | 2-5x | ⭐⭐⭐⭐⭐ | 小 |
| **混合策略** | 最大化压缩 | 4-20x | ⭐⭐⭐⭐ | 中 |

### 选择建议

**1. 追求快速部署：**
- 训练后量化（PTQ）
- 简单结构化剪枝

**2. 追求最大化压缩：**
- 混合策略（剪枝 + 量化 + 蒸馏）
- 极端量化（INT4）

**3. 从零开始设计：**
- 神经网络架构搜索（NAS）
- 知识蒸馏 + 蒸馏

**4. 特定模型：**
- BERT → DistilBERT、TinyBERT
- ResNet → MobileNet、EfficientNet
- Transformer → Linformer、Performer

### 最佳实践

1. **逐步压缩**：不要一次性过度压缩
2. **持续微调**：每次压缩后都恢复精度
3. **全面评估**：不只看精度，还要看速度、能耗
4. **真实测试**：在实际设备上验证性能
5. **迭代优化**：根据反馈调整策略

---

**文档结束**

本文档提供了 AI 模型压缩的全面指南，涵盖了从理论基础到实战应用的各个方面。根据具体需求选择合适的压缩策略，并持续优化以达到最佳的性能-精度权衡。