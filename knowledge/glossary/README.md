# AI Glossary - AI 术语表

> **最后更新**: 2026-03-30

---

## 📚 核心术语

### A
**AGI (Artificial General Intelligence)** - 通用人工智能
- 定义：具备人类水平智能的 AI
- 特征：跨领域学习、推理、问题解决
- 现状：尚未实现，长期目标

**Attention Mechanism** - 注意力机制
- 定义：模拟人类注意力的加权机制
- 应用：Transformer、机器翻译
- 优势：长距离依赖建模

**Agent** - 智能体
- 定义：能自主感知、决策、行动的系统
- 组成：感知器、决策器、执行器
- 例子：ChatGPT、AutoGPT

### B
**Batch Size** - 批次大小
- 定义：一次训练处理的样本数
- 权衡：大批次稳定但慢，小批次快但噪声大
- 典型值：32, 64, 128

**Backpropagation** - 反向传播
- 定义：基于梯度的神经网络训练算法
- 核心：链式法则
- 重要性：深度学习基础

**Bias** - 偏差/偏置
- 定义 1：模型对训练数据的系统性错误
- 定义 2：神经网络的偏置项
- 目标：低偏差 + 低方差

### C
**CNN (Convolutional Neural Network)** - 卷积神经网络
- 用途：图像处理、计算机视觉
- 层：卷积层、池化层、全连接层
- 代表：ResNet, VGG, YOLO

**Checkpoint** - 检查点
- 定义：训练过程中的模型快照
- 用途：恢复训练、模型选择
- 格式：.pth, .ckpt, .safetensors

**Context Window** - 上下文窗口
- 定义：模型能处理的最大 Token 数
- 发展：4K → 8K → 32K → 128K → 1M+
- 例子：GPT-4 (128K), Claude 3 (200K)

### D
**Diffusion Model** - 扩散模型
- 原理：逐步去噪生成图像
- 应用：图像生成（Stable Diffusion, DALL-E）
- 优势：生成质量高、多样性好

**Data Augmentation** - 数据增强
- 定义：通过变换增加训练数据
- 方法：旋转、翻转、裁剪、颜色抖动
- 目标：提高泛化能力

**Deep Learning** - 深度学习
- 定义：基于深度神经网络的机器学习
- 特点：自动特征提取
- 应用：CV, NLP, 语音

### E
**Embedding** - 嵌入
- 定义：将离散对象映射到连续向量空间
- 应用：Word2Vec, BERT, 图嵌入
- 优势：捕获语义相似性

**Epoch** - 训练轮次
- 定义：完整遍历训练集一次
- 典型值：10-100
- 关系：Epoch = Batch × Iteration

**Ensemble** - 集成
- 定义：组合多个模型提高性能
- 方法：Bagging, Boosting, Stacking
- 效果：通常比单模型好

### F
**Fine-tuning** - 微调
- 定义：在预训练模型上继续训练
- 优势：减少数据需求、加速收敛
- 步骤：预训练 → 微调 → 部署

**Few-shot Learning** - 少样本学习
- 定义：只用少量样本学习新任务
- 类型：Zero-shot, One-shot, Few-shot
- 代表：GPT-3, Claude

**Forward Pass** - 前向传播
- 定义：数据从输入到输出的计算过程
- 对比：反向传播
- 目的：计算预测值

### G
**GAN (Generative Adversarial Network)** - 生成对抗网络
- 组成：生成器 + 判别器
- 原理：对抗训练
- 应用：图像生成、风格迁移

**Gradient Descent** - 梯度下降
- 定义：基于梯度优化参数的算法
- 变体：SGD, Adam, RMSprop
- 目标：最小化损失函数

**Ground Truth** - 真值
- 定义：数据的真实标签
- 用途：评估模型性能
- 来源：人工标注、传感器

### H
**Hyperparameter** - 超参数
- 定义：训练前设置的参数
- 例子：学习率、批次大小、网络层数
- 优化：网格搜索、贝叶斯优化

**Hidden Layer** - 隐藏层
- 定义：输入层和输出层之间的层
- 深度学习核心
- 功能：特征提取和变换

**Hallucination** - 幻觉
- 定义：AI 生成虚假或无意义的内容
- 问题：LLM 常见缺陷
- 对策：RAG、温度调节

### I
**Inference** - 推理
- 定义：用训练好的模型进行预测
- 阶段：训练 → 推理 → 部署
- 优化：量化、剪枝、蒸馏

**Iteration** - 迭代
- 定义：更新一次参数
- 关系：1 Epoch = N Iterations
- 目的：逐步优化模型

**In-context Learning** - 上下文学习
- 定义：从提示词示例中学习
- 无需梯度更新
- 代表：GPT-3, Claude

### J
**Joint Training** - 联合训练
- 定义：同时训练多个任务或模块
- 优势：共享知识、提高泛化
- 例子：多任务学习

**Jailbreak** - 越狱
- 定义：绕过 AI 安全限制
- 风险：滥用 AI、有害内容
- 对策：RLHF、红队测试

### K
**Knowledge Distillation** - 知识蒸馏
- 定义：大模型教小模型
- 目的：模型压缩、加速推理
- 角色：教师模型 → 学生模型

**Kernel** - 核函数
- 定义：计算相似度的函数
- 应用：SVM、高斯过程
- 常用：RBF, 多项式核

**KL Divergence** - KL 散度
- 定义：衡量两个概率分布的差异
- 用途：VAE、强化学习
- 性质：非负、不对称

### L
**LLM (Large Language Model)** - 大语言模型
- 定义：参数量巨大的语言模型
- 规模：10B+ 参数
- 代表：GPT-4, Claude 3, GLM-5

**Learning Rate** - 学习率
- 定义：参数更新步长
- 权衡：太大发散、太小收敛慢
- 范围：0.0001 - 0.01

**Logits** - 对数几率
- 定义：未归一化的预测值
- 用途：Softmax 前的输出
- 范围：(-∞, +∞)

### M
**Model** - 模型
- 定义：从数据中学习到的函数
- 类型：判别式、生成式
- 评估：准确率、F1、AUC

**MLOps** - 机器学习运维
- 定义：ML 系统的工程化实践
- 流程：开发 → 部署 → 监控
- 工具：MLflow, Kubeflow

**Multimodal** - 多模态
- 定义：处理多种数据类型（文本、图像、音频）
- 例子：GPT-4V, Gemini
- 优势：更丰富的交互

### N
**Neural Network** - 神经网络
- 定义：受人脑启发的计算模型
- 组成：神经元、层、连接
- 学习：调整权重

**NLP (Natural Language Processing)** - 自然语言处理
- 定义：让计算机理解人类语言
- 任务：翻译、摘要、问答
- 工具：BERT, GPT, T5

**Normalization** - 归一化
- 定义：将数据缩放到标准范围
- 方法：Min-Max, Z-score, Batch Norm
- 目的：加速训练、提高稳定性

### O
**Overfitting** - 过拟合
- 定义：模型在训练集表现好但泛化差
- 原因：模型太复杂、数据太少
- 对策：正则化、Dropout、早停

**Optimizer** - 优化器
- 定义：更新参数的算法
- 代表：SGD, Adam, AdamW
- 目标：最小化损失函数

**Out-of-Distribution** - 分布外
- 定义：与训练数据分布不同的数据
- 挑战：模型性能下降
- 对策：OOD 检测

### P
**Parameter** - 参数
- 定义：模型学习到的权重
- 数量：从 K 到 B 级别
- 存储：FP32, FP16, INT8

**Pre-training** - 预训练
- 定义：在大规模数据上训练基础模型
- 优势：通用能力强
- 后续：Fine-tuning

**Prompt** - 提示词
- 定义：给 AI 的输入指令
- 工程：Prompt Engineering
- 优化：Few-shot, Chain-of-Thought

### Q
**Quantization** - 量化
- 定义：降低参数精度
- 目的：减少内存、加速推理
- 级别：FP32 → FP16 → INT8 → INT4

**Query** - 查询
- 定义 1：数据库查询（SQL）
- 定义 2：Attention 机制中的 Q
- 对应：Q (Query), K (Key), V (Value)

### R
**RAG (Retrieval-Augmented Generation)** - 检索增强生成
- 组成：检索器 + 生成器
- 优势：减少幻觉、实时知识
- 应用：知识库问答、文档分析

**ReLU** - 修正线性单元
- 定义：f(x) = max(0, x)
- 优势：缓解梯度消失、计算快
- 变体：Leaky ReLU, GELU

**RLHF (Reinforcement Learning from Human Feedback)** - 基于人类反馈的强化学习
- 流程：预训练 → SFT → RLHF
- 目的：对齐人类偏好
- 应用：ChatGPT, Claude

### S
**Self-Attention** - 自注意力机制
- 定义：序列内部的注意力
- 优势：并行计算、长距离依赖
- 应用：Transformer, GPT

**Softmax** - 归一化指数
- 定义：将 Logits 转为概率
- 公式：exp(x) / Σexp(x)
- 用途：多分类输出

**Sampling** - 采样
- 定义：从概率分布中生成输出
- 方法：Temperature, Top-K, Top-P
- 影响：创造性 vs 确定性

### T
**Transformer** - Transformer 模型
- 定义：基于 Self-Attention 的架构
- 组成：Encoder-Decoder
- 影响：NLP 领域革命

**Token** - 词元
- 定义：文本的最小单位
- 分词：WordPiece, BPE
- 例子："Hello" → ["He", "llo"]

**Transfer Learning** - 迁移学习
- 定义：将学到的知识迁移到新任务
- 优势：减少数据需求、加速收敛
- 例子：ImageNet 预训练

### V
**Validation Set** - 验证集
- 定义：用于调参和早停的数据集
- 比例：10-20%
- 区别：训练集 vs 验证集 vs 测试集

**Vector Database** - 向量数据库
- 定义：存储和检索向量相似度
- 应用：RAG、推荐系统
- 代表：Pinecone, Weaviate, Chroma

**Vision Transformer (ViT)** - 视觉 Transformer
- 定义：将 Transformer 用于图像
- 原理：图像分块 → Token 化
- 优势：全局感受野

### W
**Weight Decay** - 权重衰减
- 定义：L2 正则化
- 目的：防止过拟合
- 参数：λ（通常 0.0001）

**Word Embedding** - 词嵌入
- 定义：将词映射为向量
- 代表：Word2Vec, GloVe
- 优势：捕获语义关系

**Whisper** - OpenAI 语音模型
- 功能：语音识别、翻译
- 语言：多语言支持
- 开源：可商用

---

## 🔗 相关主题

- [[AI Research]] - 前沿研究
- [[Deep Learning]] - 深度学习
- [[NLP]] - 自然语言处理
- [[Computer Vision]] - 计算机视觉

---

**维护者**: OpenClaw Memory Team
**最后更新**: 2026-03-30
