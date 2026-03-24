# 多模态 AI 应用深度指南（第二阶段）

## 目录
1. [高级图像理解](#高级图像理解)
2. [深度视频分析](#深度视频分析)
3. [高级语音处理](#高级语音处理)
4. [跨模态检索优化](#跨模态检索优化)
5. [内容生成高级技术](#内容生成高级技术)
6. [多模态推理与决策](#多模态推理与决策)
7. [实时处理系统](#实时处理系统)
8. [模型部署与优化](#模型部署与优化)
9. [前沿研究方向](#前沿研究方向)
10. [实际项目案例](#实际项目案例)

---

## 高级图像理解

### 1. 细粒度图像识别

#### 核心概念
细粒度图像识别（Fine-grained Image Recognition）是指在大类中识别子类别的任务，例如：
- 鸟类品种识别
- 汽车型号识别
- 花卉种类识别
- 狗品种识别

#### 技术挑战
- 类间差异小（同一大类下的子类别非常相似）
- 类内差异大（同一子类别受姿态、光照、背景等影响大）
- 标注数据稀缺

#### 关键技术

##### 1. 注意力机制
```python
import torch
import torch.nn as nn
import torch.nn.functional as F

class AttentionModule(nn.Module):
    """
    注意力模块
    """
    def __init__(self, in_channels, reduction_ratio=16):
        super(AttentionModule, self).__init__()
        
        # Channel Attention
        self.channel_attention = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Conv2d(in_channels, in_channels // reduction_ratio, 1, bias=False),
            nn.ReLU(inplace=True),
            nn.Conv2d(in_channels // reduction_ratio, in_channels, 1, bias=False),
            nn.Sigmoid()
        )
        
        # Spatial Attention
        self.spatial_attention = nn.Sequential(
            nn.Conv2d(2, 1, 7, padding=3, bias=False),
            nn.Sigmoid()
        )
    
    def forward(self, x):
        # Channel Attention
        ca = self.channel_attention(x)
        x = x * ca
        
        # Spatial Attention
        max_pool = torch.max(x, dim=1, keepdim=True)[0]
        avg_pool = torch.mean(x, dim=1, keepdim=True)
        sa_input = torch.cat([max_pool, avg_pool], dim=1)
        sa = self.spatial_attention(sa_input)
        x = x * sa
        
        return x


class FineGrainedClassifier(nn.Module):
    """
    细粒度分类器
    """
    def __init__(self, num_classes, backbone='resnet50'):
        super(FineGrainedClassifier, self).__init__()
        
        # Backbone
        if backbone == 'resnet50':
            from torchvision.models import resnet50
            self.backbone = nn.Sequential(*list(resnet50(pretrained=True).children())[:-2])
            in_channels = 2048
        elif backbone == 'efficientnet':
            from torchvision.models import efficientnet_b4
            self.backbone = nn.Sequential(*list(efficientnet_b4(pretrained=True).children())[:-2])
            in_channels = 1792
        
        # 注意力模块
        self.attention = AttentionModule(in_channels)
        
        # 分类器
        self.classifier = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Dropout(0.5),
            nn.Linear(in_channels, 512),
            nn.ReLU(inplace=True),
            nn.Dropout(0.5),
            nn.Linear(512, num_classes)
        )
    
    def forward(self, x):
        # 特征提取
        features = self.backbone(x)
        
        # 注意力
        features = self.attention(features)
        
        # 分类
        logits = self.classifier(features)
        
        return logits, features


# 使用示例
if __name__ == "__main__":
    import torch
    from torchvision import transforms
    from PIL import Image
    
    # 模型
    model = FineGrainedClassifier(num_classes=200)
    model.eval()
    
    # 预处理
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    # 推理
    # image = Image.open("bird.jpg")
    # input_tensor = transform(image).unsqueeze(0)
    # logits, features = model(input_tensor)
    # probs = F.softmax(logits, dim=1)
    
    print("细粒度分类器已初始化")
```

##### 2. 区域建议网络（RPN）
```python
class RegionProposalNetwork(nn.Module):
    """
    区域建议网络
    """
    def __init__(self, in_channels, num_anchors=9):
        super(RegionProposalNetwork, self).__init__()
        
        # Anchor 生成器
        self.anchor_generator = AnchorGenerator()
        
        # 分类子网络
        self.cls_conv = nn.Sequential(
            nn.Conv2d(in_channels, 256, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(256, num_anchors * 2, 1)  # 2: objectness (fg/bg)
        )
        
        # 回归子网络
        self.reg_conv = nn.Sequential(
            nn.Conv2d(in_channels, 256, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(256, num_anchors * 4, 1)  # 4: bbox (x, y, w, h)
        )
    
    def forward(self, features, image_size):
        batch_size = features.size(0)
        
        # 生成 anchors
        anchors = self.anchor_generator.generate(features, image_size)
        
        # 分类
        cls_logits = self.cls_conv(features).permute(0, 2, 3, 1).contiguous()
        cls_logits = cls_logits.view(batch_size, -1, 2)
        
        # 回归
        bbox_pred = self.reg_conv(features).permute(0, 2, 3, 1).contiguous()
        bbox_pred = bbox_pred.view(batch_size, -1, 4)
        
        # 应用边界框回归
        proposals = self.apply_bbox_regression(anchors, bbox_pred)
        
        return proposals, cls_logits
    
    def apply_bbox_regression(self, anchors, bbox_pred):
        """
        应用边界框回归
        """
        # anchors: [N, 4] (x1, y1, x2, y2)
        # bbox_pred: [N, 4] (dx, dy, dw, dh)
        
        # 计算中心点和宽高
        anchor_widths = anchors[:, 2] - anchors[:, 0]
        anchor_heights = anchors[:, 3] - anchors[:, 1]
        anchor_ctr_x = anchors[:, 0] + 0.5 * anchor_widths
        anchor_ctr_y = anchors[:, 1] + 0.5 * anchor_heights
        
        # 应用回归
        dx = bbox_pred[:, 0]
        dy = bbox_pred[:, 1]
        dw = bbox_pred[:, 2]
        dh = bbox_pred[:, 3]
        
        pred_ctr_x = dx * anchor_widths + anchor_ctr_x
        pred_ctr_y = dy * anchor_heights + anchor_ctr_y
        pred_w = torch.exp(dw) * anchor_widths
        pred_h = torch.exp(dh) * anchor_heights
        
        # 转换回 (x1, y1, x2, y2)
        pred_boxes = torch.zeros_like(anchors)
        pred_boxes[:, 0] = pred_ctr_x - 0.5 * pred_w
        pred_boxes[:, 1] = pred_ctr_y - 0.5 * pred_h
        pred_boxes[:, 2] = pred_ctr_x + 0.5 * pred_w
        pred_boxes[:, 3] = pred_ctr_y + 0.5 * pred_h
        
        return pred_boxes


class AnchorGenerator:
    """
    Anchor 生成器
    """
    def __init__(self, scales=[8, 16, 32], aspect_ratios=[0.5, 1.0, 2.0]):
        self.scales = scales
        self.aspect_ratios = aspect_ratios
        
        # 生成所有 anchor 组合
        self.anchors = self._generate_anchors()
    
    def _generate_anchors(self):
        """
        生成所有 anchor 基础形状
        """
        anchors = []
        for scale in self.scales:
            for aspect_ratio in self.aspect_ratios:
                h = scale * torch.sqrt(torch.tensor(aspect_ratio))
                w = scale / torch.sqrt(torch.tensor(aspect_ratio))
                anchors.append([-w / 2, -h / 2, w / 2, h / 2])
        return torch.tensor(anchors)
    
    def generate(self, feature_map, image_size):
        """
        在特征图上生成 anchors
        """
        # feature_map: [B, C, H, W]
        batch_size, _, h, w = feature_map.shape
        
        # 计算特征图每个像素对应原图的位置
        stride_h = image_size[0] / h
        stride_w = image_size[1] / w
        
        # 生成网格
        grid_x = torch.arange(w) * stride_w + stride_w / 2
        grid_y = torch.arange(h) * stride_h + stride_h / 2
        grid_y, grid_x = torch.meshgrid(grid_y, grid_x)
        
        # 为每个位置生成所有 anchor
        num_anchors = len(self.anchors)
        all_anchors = []
        
        for i in range(h):
            for j in range(w):
                center_x = grid_x[i, j]
                center_y = grid_y[i, j]
                
                for anchor in self.anchors:
                    # 平移 anchor
                    anchor_shifted = anchor + torch.tensor([center_x, center_y, center_x, center_y])
                    all_anchors.append(anchor_shifted)
        
        all_anchors = torch.stack(all_anchors)
        
        # 复制到批次维度
        all_anchors = all_anchors.unsqueeze(0).repeat(batch_size, 1, 1)
        
        return all_anchors


print("区域建议网络已定义")
```

##### 3. 多尺度特征融合
```python
class FeaturePyramidNetwork(nn.Module):
    """
    特征金字塔网络（FPN）
    """
    def __init__(self, in_channels_list, out_channels=256):
        super(FeaturePyramidNetwork, self).__init__()
        
        # 侧向连接（1x1 卷积）
        self.lateral_convs = nn.ModuleList([
            nn.Conv2d(in_channels, out_channels, 1)
            for in_channels in in_channels_list
        ])
        
        # 输出卷积（3x3 卷积）
        self.fpn_convs = nn.ModuleList([
            nn.Conv2d(out_channels, out_channels, 3, padding=1)
            for _ in in in_channels_list
        ])
    
    def forward(self, features):
        """
        features: list of tensors, from high-resolution to low-resolution
        """
        # 侧向连接
        laterals = [
            lateral_conv(features[i])
            for i, lateral_conv in enumerate(self.lateral_convs)
        ]
        
        # 自顶向下路径
        for i in range(len(laterals) - 2, -1, -1):
            # 上采样
            upsampled = F.interpolate(
                laterals[i + 1],
                size=laterals[i].shape[-2:],
                mode='nearest'
            )
            # 逐元素相加
            laterals[i] = laterals[i] + upsampled
        
        # 输出卷积
        outputs = [
            fpn_conv(laterals[i])
            for i, fpn_conv in enumerate(self.fpn_convs)
        ]
        
        return outputs


class MultiScaleFeatureExtractor(nn.Module):
    """
    多尺度特征提取器
    """
    def __init__(self, backbone='resnet50'):
        super(MultiScaleFeatureExtractor, self).__init__()
        
        # ResNet backbone
        if backbone == 'resnet50':
            from torchvision.models import resnet50
            resnet = resnet50(pretrained=True)
            
            # 提取多尺度特征
            self.conv1 = resnet.conv1
            self.bn1 = resnet.bn1
            self.relu = resnet.relu
            self.maxpool = resnet.maxpool
            
            self.layer1 = resnet.layer1  # 1/4
            self.layer2 = resnet.layer2  # 1/8
            self.layer3 = resnet.layer3  # 1/16
            self.layer4 = resnet.layer4  # 1/32
            
            # FPN
            self.fpn = FeaturePyramidNetwork(
                in_channels_list=[256, 512, 1024, 2048],
                out_channels=256
            )
    
    def forward(self, x):
        # 浅层特征
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)
        
        # 深层特征
        c2 = self.layer1(x)  # 1/4
        c3 = self.layer2(c2)  # 1/8
        c4 = self.layer3(c3)  # 1/16
        c5 = self.layer4(c4)  # 1/32
        
        # FPN 特征融合
        fpn_features = self.fpn([c2, c3, c4, c5])
        
        return fpn_features


print("多尺度特征融合已定义")
```

### 2. 零样本和少样本学习

#### 零样本学习
```python
import torch
import torch.nn as nn
import torch.nn.functional as F
from transformers import CLIPProcessor, CLIPModel

class ZeroShotClassifier:
    """
    零样本分类器（基于 CLIP）
    """
    def __init__(self, model_name="openai/clip-vit-base-patch32"):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # 加载 CLIP 模型
        self.processor = CLIPProcessor.from_pretrained(model_name)
        self.model = CLIPModel.from_pretrained(model_name).to(self.device)
        self.model.eval()
        
        # 缓存类别嵌入
        self.class_embeddings = None
        self.class_names = None
    
    def encode_text(self, class_names):
        """
        编码类别名称
        """
        # 使用 prompt 模板
        prompts = [f"a photo of a {name}" for name in class_names]
        
        # 编码
        inputs = self.processor(text=prompts, return_tensors="pt", padding=True).to(self.device)
        
        with torch.no_grad():
            text_embeddings = self.model.get_text_features(**inputs)
            text_embeddings = text_embeddings / text_embeddings.norm(dim=-1, keepdim=True)
        
        self.class_embeddings = text_embeddings
        self.class_names = class_names
        
        return text_embeddings
    
    def classify(self, image, top_k=5):
        """
        零样本分类
        """
        if self.class_embeddings is None:
            raise ValueError("Please call encode_text first")
        
        # 编码图像
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)
        
        with torch.no_grad():
            image_embedding = self.model.get_image_features(**inputs)
            image_embedding = image_embedding / image_embedding.norm(dim=-1, keepdim=True)
        
        # 计算相似度
        similarity = (100.0 * image_embedding @ self.class_embeddings.T).softmax(dim=-1)
        
        # 获取 top-k
        values, indices = similarity[0].topk(top_k)
        
        results = [
            {
                "class": self.class_names[idx],
                "probability": val.item()
            }
            for val, idx in zip(values, indices)
        ]
        
        return results
    
    def batch_classify(self, images, top_k=5):
        """
        批量分类
        """
        results = []
        
        for image in images:
            result = self.classify(image, top_k)
            results.append(result)
        
        return results


# 使用示例
if __name__ == "__main__":
    from PIL import Image
    
    classifier = ZeroShotClassifier()
    
    # 定义类别
    class_names = [
        "dog", "cat", "bird", "fish", "horse",
        "car", "bicycle", "airplane", "boat", "train",
        "tree", "flower", "building", "mountain", "beach"
    ]
    
    # 编码类别
    classifier.encode_text(class_names)
    
    # 分类
    # image = Image.open("example.jpg")
    # results = classifier.classify(image, top_k=3)
    # for result in results:
    #     print(f"{result['class']}: {result['probability']:.3f}")
    
    print("零样本分类器已初始化")
```

#### 少样本学习（Prototypical Networks）
```python
class PrototypicalNetwork(nn.Module):
    """
    原型网络（少样本学习）
    """
    def __init__(self, encoder, embedding_dim=64):
        super(PrototypicalNetwork, self).__init__()
        
        self.encoder = encoder
        self.embedding_dim = embedding_dim
    
    def forward(self, support_images, support_labels, query_images):
        """
        Args:
            support_images: [num_classes * num_shots, C, H, W]
            support_labels: [num_classes * num_shots]
            query_images: [num_queries, C, H, W]
        
        Returns:
            logits: [num_queries, num_classes]
        """
        # 提取支持集嵌入
        support_embeddings = self.encoder(support_images)
        
        # 提取查询集嵌入
        query_embeddings = self.encoder(query_images)
        
        # 计算原型（每个类别的平均嵌入）
        num_classes = support_labels.max().item() + 1
        prototypes = torch.zeros(num_classes, self.embedding_dim).to(support_embeddings.device)
        
        for c in range(num_classes):
            mask = (support_labels == c)
            prototypes[c] = support_embeddings[mask].mean(dim=0)
        
        # 计算距离
        distances = torch.cdist(query_embeddings, prototypes)
        
        # 转换为 logits（距离越小，logits 越大）
        logits = -distances
        
        return logits
    
    def predict(self, support_images, support_labels, query_images):
        """
        预测
        """
        logits = self.forward(support_images, support_labels, query_images)
        probs = F.softmax(logits, dim=1)
        preds = logits.argmax(dim=1)
        
        return preds, probs


class SimpleEncoder(nn.Module):
    """
    简单的编码器
    """
    def __init__(self, in_channels=3, embedding_dim=64):
        super(SimpleEncoder, self).__init__()
        
        self.encoder = nn.Sequential(
            nn.Conv2d(in_channels, 32, 3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            
            nn.Conv2d(32, 64, 3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            
            nn.Conv2d(64, 128, 3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Linear(128, embedding_dim)
        )
    
    def forward(self, x):
        return self.encoder(x)


# 使用示例
if __name__ == "__main__":
    import torch
    
    # 创建模型
    encoder = SimpleEncoder(in_channels=3, embedding_dim=64)
    model = PrototypicalNetwork(encoder, embedding_dim=64)
    model.eval()
    
    # 5-way 5-shot
    num_classes = 5
    num_shots = 5
    num_queries = 10
    
    # 模拟数据
    support_images = torch.randn(num_classes * num_shots, 3, 84, 84)
    support_labels = torch.tensor([i for i in range(num_classes) for _ in range(num_shots)])
    query_images = torch.randn(num_queries, 3, 84, 84)
    
    # 预测
    preds, probs = model.predict(support_images, support_labels, query_images)
    
    print(f"预测结果: {preds}")
    print(f"概率: {probs[0]}")
    
    print("原型网络已定义")
```

### 3. 图像分割与理解

#### 语义分割
```python
class SemanticSegmentationNet(nn.Module):
    """
    语义分割网络（DeepLabV3+ 风格）
    """
    def __init__(self, num_classes, backbone='resnet50'):
        super(SemanticSegmentationNet, self).__init__()
        
        # Backbone
        if backbone == 'resnet50':
            from torchvision.models import resnet50
            resnet = resnet50(pretrained=True)
            
            self.conv1 = resnet.conv1
            self.bn1 = resnet.bn1
            self.relu = resnet.relu
            self.maxpool = resnet.maxpool
            
            self.layer1 = resnet.layer1  # 1/4
            self.layer2 = resnet.layer2  # 1/8
            self.layer3 = resnet.layer3  # 1/16
            self.layer4 = resnet.layer4  # 1/32
            
            low_level_channels = 256
            high_level_channels = 2048
        
        # ASPP（Atrous Spatial Pyramid Pooling）
        self.aspp = ASPP(high_level_channels, 256)
        
        # 解码器
        self.decoder = Decoder(low_level_channels, 256)
        
        # 分类器
        self.classifier = nn.Sequential(
            nn.Conv2d(256, 256, 3, padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            nn.Dropout(0.5),
            nn.Conv2d(256, num_classes, 1)
        )
    
    def forward(self, x):
        input_size = x.shape[-2:]
        
        # 编码器
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)
        
        low_level_feat = self.layer1(x)  # 1/4
        x = self.layer2(low_level_feat)  # 1/8
        x = self.layer3(x)  # 1/16
        x = self.layer4(x)  # 1/32
        
        # ASPP
        high_level_feat = self.aspp(x)
        
        # 解码器
        x = self.decoder(low_level_feat, high_level_feat)
        
        # 分类
        x = self.classifier(x)
        
        # 上采样到输入尺寸
        x = F.interpolate(x, size=input_size, mode='bilinear', align_corners=True)
        
        return x


class ASPP(nn.Module):
    """
    空洞空间金字塔池化
    """
    def __init__(self, in_channels, out_channels):
        super(ASPP, self).__init__()
        
        # 不同空洞率的卷积
        self.conv_1x1 = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, 1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        )
        
        self.conv_3x3_1 = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, 3, padding=6, dilation=6, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        )
        
        self.conv_3x3_2 = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, 3, padding=12, dilation=12, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        )
        
        self.conv_3x3_3 = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, 3, padding=18, dilation=18, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        )
        
        # 全局平均池化
        self.global_pool = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Conv2d(in_channels, out_channels, 1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        )
        
        # 融合
        self.fusion = nn.Sequential(
            nn.Conv2d(out_channels * 5, out_channels, 1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Dropout(0.5)
        )
    
    def forward(self, x):
        input_size = x.shape[-2:]
        
        # 多尺度特征
        feat_1x1 = self.conv_1x1(x)
        feat_3x3_1 = self.conv_3x3_1(x)
        feat_3x3_2 = self.conv_3x3_2(x)
        feat_3x3_3 = self.conv_3x3_3(x)
        
        # 全局特征
        feat_global = self.global_pool(x)
        feat_global = F.interpolate(feat_global, size=input_size, mode='bilinear', align_corners=True)
        
        # 拼接
        feat = torch.cat([feat_1x1, feat_3x3_1, feat_3x3_2, feat_3x3_3, feat_global], dim=1)
        
        # 融合
        out = self.fusion(feat)
        
        return out


class Decoder(nn.Module):
    """
    解码器
    """
    def __init__(self, low_level_channels, out_channels):
        super(Decoder, self).__init__()
        
        # 低层特征处理
        self.low_level_conv = nn.Sequential(
            nn.Conv2d(low_level_channels, 48, 1, bias=False),
            nn.BatchNorm2d(48),
            nn.ReLU(inplace=True)
        )
        
        # 融合
        self.fusion = nn.Sequential(
            nn.Conv2d(48 + out_channels, 256, 3, padding=1, bias=False),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            nn.Dropout(0.5),
            nn.Conv2d(256, 256, 3, padding=1, bias=False),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            nn.Dropout(0.1)
        )
    
    def forward(self, low_level_feat, high_level_feat):
        # 上采样高层特征
        input_size = low_level_feat.shape[-2:]
        high_level_feat = F.interpolate(
            high_level_feat,
            size=input_size,
            mode='bilinear',
            align_corners=True
        )
        
        # 处理低层特征
        low_level_feat = self.low_level_conv(low_level_feat)
        
        # 拼接
        feat = torch.cat([low_level_feat, high_level_feat], dim=1)
        
        # 融合
        out = self.fusion(feat)
        
        return out


print("语义分割网络已定义")
```

#### 实例分割
```python
class InstanceSegmentationNet(nn.Module):
    """
    实例分割网络（Mask R-CNN 风格）
    """
    def __init__(self, num_classes, backbone='resnet50'):
        super(InstanceSegmentationNet, self).__init__()
        
        # Backbone
        if backbone == 'resnet50':
            from torchvision.models import resnet50
            resnet = resnet50(pretrained=True)
            self.backbone = nn.Sequential(*list(resnet.children())[:-2])
            in_channels = 2048
        
        # RPN
        self.rpn = RegionProposalNetwork(in_channels)
        
        # ROI Pooling
        self.roi_pool = ROIPool(output_size=(7, 7), spatial_scale=1/16)
        
        # 分类头
        self.classifier = nn.Sequential(
            nn.Linear(2048 * 7 * 7, 1024),
            nn.ReLU(inplace=True),
            nn.Dropout(0.5),
            nn.Linear(1024, num_classes)
        )
        
        # 边界框回归头
        self.bbox_regressor = nn.Sequential(
            nn.Linear(2048 * 7 * 7, 1024),
            nn.ReLU(inplace=True),
            nn.Dropout(0.5),
            nn.Linear(1024, num_classes * 4)
        )
        
        # Mask 头
        self.mask_head = nn.Sequential(
            nn.Conv2d(256, 256, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(256, 256, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(256, 256, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(256, 256, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(256, num_classes * 256, 3, padding=1)
        )
        
        # Mask 特征提取
        self.mask_feature_extractor = nn.Sequential(
            nn.Conv2d(2048, 256, 1),
            nn.ReLU(inplace=True)
        )
    
    def forward(self, x):
        # Backbone 特征
        features = self.backbone(x)  # [B, 2048, H/16, W/16]
        
        # RPN
        proposals, rpn_cls_logits = self.rpn(features, x.shape[-2:])
        
        # ROI Pooling
        roi_features = self.roi_pool(features, proposals)
        
        # 展平
        roi_features = roi_features.flatten(1)
        
        # 分类
        cls_logits = self.classifier(roi_features)
        
        # 边界框回归
        bbox_pred = self.bbox_regressor(roi_features)
        
        # Mask 预测
        mask_features = self.mask_feature_extractor(features)
        roi_masks = self.roi_pool(mask_features, proposals)
        mask_pred = self.mask_head(roi_masks)
        
        return {
            "proposals": proposals,
            "cls_logits": cls_logits,
            "bbox_pred": bbox_pred,
            "mask_pred": mask_pred
        }


class ROIPool(nn.Module):
    """
    ROI Pooling
    """
    def __init__(self, output_size=(7, 7), spatial_scale=1.0):
        super(ROIPool, self).__init__()
        self.output_size = output_size
        self.spatial_scale = spatial_scale
        self.adaptive_max_pool = nn.AdaptiveMaxPool2d(output_size)
    
    def forward(self, feature_map, rois):
        """
        Args:
            feature_map: [B, C, H, W]
            rois: [N, 4] (batch_idx, x1, y1, x2, y2)
        """
        pooled_features = []
        
        for roi in rois:
            batch_idx = int(roi[0].item())
            x1, y1, x2, y2 = roi[1:] * self.spatial_scale
            
            # 裁剪 ROI
            roi_feature = feature_map[batch_idx:batch_idx+1, :, int(y1):int(y2), int(x1):int(x2)]
            
            # Max Pooling
            pooled = self.adaptive_max_pool(roi_feature)
            pooled_features.append(pooled)
        
        # 拼接
        pooled_features = torch.cat(pooled_features, dim=0)
        
        return pooled_features


print("实例分割网络已定义")
```

---

## 深度视频分析

### 1. 动作识别

#### 3D CNN（I3D）
```python
class I3D(nn.Module):
    """
    Inflated 3D ConvNet（I3D）
    """
    def __init__(self, num_classes=400, dropout_prob=0.5):
        super(I3D, self).__init__()
        
        # 3D 卷积层
        self.conv3d_1a_7x7 = nn.Conv3d(3, 64, kernel_size=(7, 7, 7), stride=(2, 2, 2), padding=(3, 3, 3))
        self.maxpool3d_2a_3x3 = nn.MaxPool3d(kernel_size=(1, 3, 3), stride=(1, 2, 2), padding=(0, 1, 1))
        
        self.conv3d_2b_1x1 = nn.Conv3d(64, 64, kernel_size=(1, 1, 1))
        self.conv3d_2c_3x3 = nn.Conv3d(64, 192, kernel_size=(3, 3, 3), padding=(1, 1, 1))
        self.maxpool3d_3a_3x3 = nn.MaxPool3d(kernel_size=(1, 3, 3), stride=(1, 2, 2), padding=(0, 1, 1))
        
        # Mixed_3b
        self.mixed_3b = nn.ModuleDict({
            'branch0': nn.Sequential(
                nn.Conv3d(192, 64, kernel_size=(1, 1, 1)),
                nn.BatchNorm3d(64),
                nn.ReLU(inplace=True)
            ),
            'branch1': nn.Sequential(
                nn.Conv3d(192, 96, kernel_size=(1, 1, 1)),
                nn.BatchNorm3d(96),
                nn.ReLU(inplace=True),
                nn.Conv3d(96, 128, kernel_size=(3, 3, 3), padding=(1, 1, 1)),
                nn.BatchNorm3d(128),
                nn.ReLU(inplace=True)
            ),
            'branch2': nn.Sequential(
                nn.Conv3d(192, 16, kernel_size=(1, 1, 1)),
                nn.BatchNorm3d(16),
                nn.ReLU(inplace=True),
                nn.Conv3d(16, 32, kernel_size=(3, 3, 3), padding=(1, 1, 1)),
                nn.BatchNorm3d(32),
                nn.ReLU(inplace=True)
            ),
            'branch3': nn.Sequential(
                nn.MaxPool3d(kernel_size=(3, 3, 3), stride=(1, 1, 1), padding=(1, 1, 1)),
                nn.Conv3d(192, 32, kernel_size=(1, 1, 1)),
                nn.BatchNorm3d(32),
                nn.ReLU(inplace=True)
            )
        })
        
        # Mixed_4b - Mixed_5b (简化版)
        self.mixed_4b = self._make_mixed_block(480, [192, 128, 96, 128], [192, 96, 16, 64], [192, 192, 32, 64])
        self.mixed_5b = self._make_mixed_block(832, [192, 192, 128, 192], [192, 192, 32, 96], [192, 192, 32, 96])
        
        # Average pooling
        self.avgpool = nn.AdaptiveAvgPool3d((1, 1, 1))
        
        # 分类器
        self.classifier = nn.Sequential(
            nn.Dropout(dropout_prob),
            nn.Linear(832, num_classes)
        )
    
    def _make_mixed_block(self, in_channels, branch0, branch1, branch2):
        return nn.ModuleDict({
            'branch0': nn.Sequential(
                nn.Conv3d(in_channels, branch0[0], kernel_size=(1, 1, 1)),
                nn.BatchNorm3d(branch0[0]),
                nn.ReLU(inplace=True)
            ),
            'branch1': nn.Sequential(
                nn.Conv3d(in_channels, branch1[0], kernel_size=(1, 1, 1)),
                nn.BatchNorm3d(branch1[0]),
                nn.ReLU(inplace=True),
                nn.Conv3d(branch1[0], branch1[1], kernel_size=(3, 3, 3), padding=(1, 1, 1)),
                nn.BatchNorm3d(branch1[1]),
                nn.ReLU(inplace=True)
            ),
            'branch2': nn.Sequential(
                nn.Conv3d(in_channels, branch2[0], kernel_size=(1, 1, 1)),
                nn.BatchNorm3d(branch2[0]),
                nn.ReLU(inplace=True),
                nn.Conv3d(branch2[0], branch2[1], kernel_size=(3, 3, 3), padding=(1, 1, 1)),
                nn.BatchNorm3d(branch2[1]),
                nn.ReLU(inplace=True)
            ),
            'branch3': nn.Sequential(
                nn.MaxPool3d(kernel_size=(3, 3, 3), stride=(1, 1, 1), padding=(1, 1, 1)),
                nn.Conv3d(in_channels, branch2[2], kernel_size=(1, 1, 1)),
                nn.BatchNorm3d(branch2[2]),
                nn.ReLU(inplace=True)
            )
        })
    
    def forward(self, x):
        # x: [B, C, T, H, W]
        x = self.conv3d_1a_7x7(x)
        x = F.relu(x, inplace=True)
        x = self.maxpool3d_2a_3x3(x)
        
        x = self.conv3d_2b_1x1(x)
        x = F.relu(x, inplace=True)
        x = self.conv3d_2c_3x3(x)
        x = F.relu(x, inplace=True)
        x = self.maxpool3d_3a_3x3(x)
        
        x = self._mixed_forward(x, self.mixed_3b)
        x = self._mixed_forward(x, self.mixed_4b)
        x = self._mixed_forward(x, self.mixed_5b)
        
        x = self.avgpool(x)
        x = x.view(x.size(0), -1)
        x = self.classifier(x)
        
        return x
    
    def _mixed_forward(self, x, mixed_block):
        outputs = [branch(x) for branch in mixed_block.values()]
        return torch.cat(outputs, dim=1)


print("I3D 模型已定义")
```

#### 双流网络（Two-Stream Network）
```python
class TwoStreamNetwork(nn.Module):
    """
    双流网络（RGB + 光流）
    """
    def __init__(self, num_classes, backbone='resnet50'):
        super(TwoStreamNetwork, self).__init__()
        
        # RGB 流（空间流）
        if backbone == 'resnet50':
            from torchvision.models import resnet50
            rgb_backbone = resnet50(pretrained=True)
            self.rgb_stream = nn.Sequential(*list(rgb_backbone.children())[:-1])
            rgb_feature_dim = 2048
        
        # 光流流（时间流）
        flow_backbone = resnet50(pretrained=True)
        # 修改第一层接受 2 通道（光流：u, v）
        flow_backbone.conv1 = nn.Conv2d(2, 64, kernel_size=7, stride=2, padding=3, bias=False)
        self.flow_stream = nn.Sequential(*list(flow_backbone.children())[:-1])
        flow_feature_dim = 2048
        
        # 融合层
        self.fusion = nn.Sequential(
            nn.Linear(rgb_feature_dim + flow_feature_dim, 1024),
            nn.ReLU(inplace=True),
            nn.Dropout(0.5),
            nn.Linear(1024, num_classes)
        )
        
        # 可学习的融合权重
        self.alpha = nn.Parameter(torch.ones(1))
    
    def forward(self, rgb_input, flow_input):
        """
        Args:
            rgb_input: [B, T, 3, H, W] 或 [B, 3, H, W]
            flow_input: [B, T, 2, H, W] 或 [B, 2, H, W]
        """
        # 处理 RGB 流
        if rgb_input.dim() == 5:
            # 采样关键帧
            rgb_input = rgb_input[:, rgb_input.shape[1] // 2, :, :, :]
        
        rgb_features = self.rgb_stream(rgb_input)
        rgb_features = rgb_features.flatten(1)
        
        # 处理光流流
        if flow_input.dim() == 5:
            # 堆叠所有帧的光流
            flow_input = flow_input.mean(dim=1)
        
        flow_features = self.flow_stream(flow_input)
        flow_features = flow_features.flatten(1)
        
        # 融合
        combined_features = torch.cat([rgb_features, flow_features], dim=1)
        
        # 加权融合
        weighted_rgb = rgb_features * F.softmax(self.alpha, dim=0)[0]
        weighted_flow = flow_features * F.softmax(-self.alpha, dim=0)[0]
        combined_weighted = torch.cat([weighted_rgb, weighted_flow], dim=1)
        
        # 分类
        logits = self.fusion(combined_weighted)
        
        return logits


class OpticalFlowExtractor:
    """
    光流提取器
    """
    def __init__(self, method='farneback'):
        self.method = method
    
    def extract_flow(self, prev_frame, next_frame):
        """
        提取光流
        """
        # 转换为灰度
        prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
        next_gray = cv2.cvtColor(next_frame, cv2.COLOR_BGR2GRAY)
        
        if self.method == 'farneback':
            # Farneback 算法
            flow = cv2.calcOpticalFlowFarneback(
                prev_gray, next_gray, None,
                pyr_scale=0.5,
                levels=3,
                winsize=15,
                iterations=3,
                poly_n=5,
                poly_sigma=1.2,
                flags=0
            )
        elif self.method == 'dis':
            # DIS 光流
            import cv2
            dis = cv2.DISOpticalFlow_create(cv2.DIS_OPTICAL_FLOW_PRESET_MEDIUM)
            flow = dis.calc(prev_gray, next_gray, None)
        
        # 归一化
        flow = self.normalize_flow(flow)
        
        return flow
    
    def normalize_flow(self, flow):
        """
        归一化光流
        """
        # 计算幅值
        magnitude = np.sqrt(flow[..., 0] ** 2 + flow[..., 1] ** 2)
        
        # 归一化到 [0, 1]
        max_magnitude = np.percentile(magnitude, 99)
        flow[..., 0] /= (max_magnitude + 1e-8)
        flow[..., 1] /= (max_magnitude + 1e-8)
        
        # Clip
        flow = np.clip(flow, -1, 1)
        
        return flow
    
    def extract_video_flow(self, video_path, output_path=None, num_frames=64):
        """
        提取视频光流
        """
        cap = cv2.VideoCapture(video_path)
        
        # 获取视频信息
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # 计算采样间隔
        if num_frames < total_frames:
            interval = max(1, total_frames // num_frames)
        else:
            interval = 1
        
        # 提取帧
        frames = []
        frame_count = 0
        prev_frame = None
        
        flows = []
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_count % interval == 0:
                if prev_frame is not None:
                    # 计算光流
                    flow = self.extract_flow(prev_frame, frame)
                    flows.append(flow)
                
                prev_frame = frame
            
            frame_count += 1
        
        cap.release()
        
        # 堆叠光流
        if len(flows) > 0:
            flow_tensor = np.stack(flows, axis=0)  # [T, H, W, 2]
            flow_tensor = torch.from_numpy(flow_tensor).permute(3, 0, 1, 2)  # [2, T, H, W]
            flow_tensor = flow_tensor.float()
        else:
            flow_tensor = torch.zeros(2, 1, 224, 224)
        
        if output_path is not None:
            # 保存光流可视化
            self.visualize_flows(flows, output_path)
        
        return flow_tensor
    
    def visualize_flows(self, flows, output_path):
        """
        可视化光流
        """
        h, w = flows[0].shape[:2]
        out = cv2.VideoWriter(
            output_path,
            cv2.VideoWriter_fourcc(*'mp4v'),
            30,
            (w * 2, h)
        )
        
        for flow in flows:
            # HSV 可视化
            hsv = np.zeros((h, w, 3), dtype=np.uint8)
            hsv[..., 1] = 255
            
            # 计算幅值和角度
            magnitude, angle = cv2.cartToPolar(flow[..., 0], flow[..., 1])
            
            # 设置色相和饱和度
            hsv[..., 0] = angle * 180 / np.pi
            hsv[..., 2] = cv2.normalize(magnitude, None, 0, 255, cv2.NORM_MINMAX)
            
            # 转换为 BGR
            bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
            
            out.write(bgr)
        
        out.release()


print("双流网络和光流提取器已定义")
```

### 2. 视频对象跟踪

#### SiameseRPN
```python
class SiameseRPN(nn.Module):
    """
    Siamese 区域建议网络
    """
    def __init__(self, backbone='alexnet', anchor_num=5):
        super(SiameseRPN, self).__init__()
        
        # Backbone
        if backbone == 'alexnet':
            self.features = nn.Sequential(
                nn.Conv2d(3, 96, 11, 2),
                nn.BatchNorm2d(96),
                nn.ReLU(inplace=True),
                nn.MaxPool2d(2),
                
                nn.Conv2d(96, 256, 5, 1, 2),
                nn.BatchNorm2d(256),
                nn.ReLU(inplace=True),
                nn.MaxPool2d(2),
                
                nn.Conv2d(256, 384, 3, 1, 1),
                nn.BatchNorm2d(384),
                nn.ReLU(inplace=True),
                
                nn.Conv2d(384, 256, 3, 1, 1),
                nn.BatchNorm2d(256),
                nn.ReLU(inplace=True),
                
                nn.Conv2d(256, 256, 3, 1, 1),
                nn.BatchNorm2d(256),
            )
            
            self.adjust_channel = nn.Conv2d(256, 256, 1)
        
        # RPN
        self.anchor_num = anchor_num
        self.rpn_conv = nn.Conv2d(256, 256, 3, 1, 1)
        
        self.cls = nn.Conv2d(256, 2 * anchor_num, 1)
        self.loc = nn.Conv2d(256, 4 * anchor_num, 1)
    
    def forward(self, z, x):
        """
        Args:
            z: template image [B, 3, H, W]
            x: search image [B, 3, H, W]
        """
        # 特征提取
        z_feat = self.features(z)
        x_feat = self.features(x)
        
        # 调整通道
        z_feat = self.adjust_channel(z_feat)
        
        # 相关滤波
        corr_feat = self._xcorr_fast(z_feat, x_feat)
        
        # RPN
        rpn_feat = self.rpn_conv(corr_feat)
        
        # 分类和回归
        cls_pred = self.cls(rpn_feat)
        loc_pred = self.loc(rpn_feat)
        
        return cls_pred, loc_pred
    
    def _xcorr_fast(self, z, x):
        """
        快速相关运算
        """
        nz = z.size(0)
        nx, c, h, w = x.size()
        
        # Reshape template
        z = z.view(nz, c, -1)
        z = z.permute(1, 0, 2)  # [c, nz, h*z*w*z]
        
        # Reshape search
        x = x.view(nx, c, -1)
        
        # 相关
        x = x.permute(1, 0, 2)  # [c, nx, h*x*w*x]
        corr = torch.matmul(z, x)  # [c, nz, h*x*w*x]
        corr = corr.permute(1, 2, 0)  # [nz, h*x*w*x, c]
        
        # Reshape back
        corr = corr.view(nx, -1, h, w)
        
        return corr


class SiameseTracker:
    """
    Siamese 跟踪器
    """
    def __init__(self, model_path=None):
        self.model = SiameseRPN()
        
        if model_path is not None:
            self.model.load_state_dict(torch.load(model_path))
        
        self.model.eval()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        
        # Anchor 生成
        self.anchor_boxes = self._generate_anchors()
        
        # 模板特征
        self.z_feat = None
    
    def _generate_anchors(self, stride=8):
        """
        生成 anchors
        """
        ratios = [0.5, 1, 2]
        scales = [8, 16, 32]
        anchor_num = len(ratios) * len(scales)
        
        anchors = []
        for scale in scales:
            for ratio in ratios:
                w = scale * np.sqrt(ratio)
                h = scale / np.sqrt(ratio)
                anchors.append([-w / 2, -h / 2, w / 2, h / 2])
        
        return torch.tensor(anchors).float()
    
    def init(self, img, bbox):
        """
        初始化跟踪
        """
        # 裁剪模板
        z = self._crop_and_resize(img, bbox, 127)
        
        # 转换为 tensor
        z = torch.from_numpy(z).permute(2, 0, 1).unsqueeze(0).float() / 255.0
        z = z.to(self.device)
        
        # 提取模板特征
        with torch.no_grad():
            self.model.features(z)
            self.z_feat = self.model.adjust_channel(self.model.features(z))
    
    def update(self, img):
        """
        更新跟踪
        """
        # 裁剪搜索区域
        # 假设上一个 bbox 在搜索区域中心
        center_x = self.prev_bbox[0] + self.prev_bbox[2] / 2
        center_y = self.prev_bbox[1] + self.prev_bbox[3] / 2
        
        # 搜索区域（模板的 2 倍）
        search_size = 255
        x1 = max(0, int(center_x - search_size / 2))
        y1 = max(0, int(center_y - search_size / 2))
        x2 = min(img.shape[1], x1 + search_size)
        y2 = min(img.shape[0], y1 + search_size)
        
        # 如果超出边界，调整
        if x2 - x1 < search_size:
            x1 = max(0, x2 - search_size)
        if y2 - y1 < search_size:
            y1 = max(0, y2 - search_size)
        
        search_bbox = [x1, y1, x2 - x1, y2 - y1]
        
        # 裁剪搜索图像
        x = self._crop_and_resize(img, search_bbox, 255)
        
        # 转换为 tensor
        x = torch.from_numpy(x).permute(2, 0, 1).unsqueeze(0).float() / 255.0
        x = x.to(self.device)
        
        # 相关和 RPN
        with torch.no_grad():
            cls_pred, loc_pred = self.model(self.z_feat, x)
        
        # Post-process
        bbox = self._post_process(cls_pred, loc_pred, search_bbox)
        
        self.prev_bbox = bbox
        
        return bbox
    
    def _crop_and_resize(self, img, bbox, output_size):
        """
        裁剪和调整大小
        """
        x, y, w, h = bbox
        
        # 裁剪
        crop = img[int(y):int(y+h), int(x):int(x+w)]
        
        # 调整大小
        crop = cv2.resize(crop, (output_size, output_size))
        
        return crop
    
    def _post_process(self, cls_pred, loc_pred, search_bbox):
        """
        后处理
        """
        # 获取最大响应
        cls_pred = cls_pred.squeeze().permute(1, 2, 0).contiguous()
        max_idx = torch.argmax(cls_pred[..., 0])
        
        # 获取对应的回归结果
        h, w = cls_pred.shape[:2]
        y = max_idx // w
        x = max_idx % w
        
        # 获取 anchor
        anchor_idx = x % self.model.anchor_num
        anchor = self.anchor_boxes[anchor_idx]
        
        # 获取回归结果
        dx, dy, dw, dh = loc_pred[0, :, y, x, anchor_idx]
        
        # 转换为 bbox
        cx = anchor[0] + anchor[2] / 2 + dx * anchor[2]
        cy = anchor[1] + anchor[3] / 2 + dy * anchor[3]
        bw = anchor[2] * torch.exp(dw)
        bh = anchor[3] * torch.exp(dh)
        
        # 映射到原始图像
        stride = 8
        x1 = (cx * stride + search_bbox[0]) - bw / 2
        y1 = (cy * stride + search_bbox[1]) - bh / 2
        x2 = x1 + bw
        y2 = y1 + bh
        
        return [x1.item(), y1.item(), (x2 - x1).item(), (y2 - y1).item()]


print("SiameseRPN 跟踪器已定义")
```

### 3. 视频摘要生成

#### 基于注意力的视频摘要
```python
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np

class VideoSummarizer(nn.Module):
    """
    视频摘要生成器（基于注意力机制）
    """
    def __init__(self, feature_dim=512, hidden_dim=256):
        super(VideoSummarizer, self).__init__()
        
        # 特征提取器（简化版，实际使用预训练模型）
        self.feature_extractor = nn.Sequential(
            nn.Conv2d(3, 64, 3, stride=2, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 128, 3, stride=2, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(128, 256, 3, stride=2, padding=1),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Linear(256, feature_dim)
        )
        
        # 双向 LSTM
        self.lstm = nn.LSTM(
            feature_dim,
            hidden_dim,
            num_layers=2,
            batch_first=True,
            bidirectional=True
        )
        
        # 注意力机制
        self.attention = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, 1)
        )
        
        # 分类器（选择/不选择）
        self.selector = nn.Linear(hidden_dim * 2, 1)
    
    def forward(self, frames):
        """
        Args:
            frames: [B, T, 3, H, W]
        """
        batch_size, num_frames = frames.shape[:2]
        
        # 重塑为 [B * T, 3, H, W]
        frames_reshaped = frames.view(batch_size * num_frames, *frames.shape[2:])
        
        # 提取特征
        features = self.feature_extractor(frames_reshaped)
        features = features.view(batch_size, num_frames, -1)
        
        # LSTM
        lstm_out, _ = self.lstm(features)
        
        # 注意力
        attention_scores = self.attention(lstm_out).squeeze(-1)
        attention_weights = F.softmax(attention_scores, dim=1)
        
        # 选择概率
        select_probs = torch.sigmoid(self.selector(lstm_out)).squeeze(-1)
        
        # 加权平均（摘要表示）
        summary = torch.sum(lstm_out * attention_weights.unsqueeze(-1), dim=1)
        
        return {
            'summary': summary,
            'attention_weights': attention_weights,
            'select_probs': select_probs
        }
    
    def generate_summary(self, frames, max_summary_length=None):
        """
        生成视频摘要
        """
        with torch.no_grad():
            output = self.forward(frames)
        
        select_probs = output['select_probs'][0].cpu().numpy()
        
        # 选择帧
        if max_summary_length is not None:
            # 选择概率最高的帧
            selected_indices = np.argsort(select_probs)[-max_summary_length:]
            selected_indices = np.sort(selected_indices)
        else:
            # 使用阈值
            threshold = 0.5
            selected_indices = np.where(select_probs > threshold)[0]
        
        selected_frames = frames[0, selected_indices]
        
        return {
            'selected_frames': selected_frames,
            'selected_indices': selected_indices,
            'select_probs': select_probs
        }


class VideoSummarizationTrainer:
    """
    视频摘要训练器
    """
    def __init__(self, model, lr=1e-4):
        self.model = model
        self.optimizer = torch.optim.Adam(model.parameters(), lr=lr)
        self.criterion = nn.BCELoss()
    
    def train_step(self, frames, labels):
        """
        训练步骤
        Args:
            frames: [B, T, 3, H, W]
            labels: [B, T] (0 或 1)
        """
        self.model.train()
        
        # 前向传播
        output = self.model(frames)
        select_probs = output['select_probs']
        
        # 计算损失
        loss = self.criterion(select_probs, labels.float())
        
        # 反向传播
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        
        return loss.item()
    
    def evaluate(self, frames, labels):
        """
        评估
        """
        self.model.eval()
        
        with torch.no_grad():
            output = self.model(frames)
            select_probs = output['select_probs']
            
            # 计算 F-score
            preds = (select_probs > 0.5).float()
            
            tp = torch.sum(preds * labels).item()
            fp = torch.sum(preds * (1 - labels)).item()
            fn = torch.sum((1 - preds) * labels).item()
            
            precision = tp / (tp + fp + 1e-8)
            recall = tp / (tp + fn + 1e-8)
            f_score = 2 * precision * recall / (precision + recall + 1e-8)
        
        return f_score, precision, recall


print("视频摘要生成器已定义")
```

---

## 高级语音处理

### 1. 语音合成（TTS）

#### Tacotron 2 风格的 TTS
```python
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Tuple

class Encoder(nn.Module):
    """
    文本编码器
    """
    def __init__(self, vocab_size, embedding_dim=512, num_layers=3):
        super(Encoder, self).__init__()
        
        # 字符嵌入
        self.embedding = nn.Embedding(vocab_size, embedding_dim)
        
        # 预卷积层
        self.preconv = nn.Sequential(
            nn.Conv1d(embedding_dim, 512, kernel_size=5, padding=2),
            nn.BatchNorm1d(512),
            nn.ReLU(inplace=True),
            nn.Conv1d(512, 512, kernel_size=5, padding=2),
            nn.BatchNorm1d(512),
            nn.ReLU(inplace=True)
        )
        
        # 双向 LSTM
        self.lstm = nn.LSTM(
            512,
            256,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True
        )
    
    def forward(self, text):
        """
        Args:
            text: [B, T_text]
        """
        # 嵌入
        x = self.embedding(text)  # [B, T_text, embedding_dim]
        
        # 预卷积
        x = x.transpose(1, 2)  # [B, embedding_dim, T_text]
        x = self.preconv(x)  # [B, 512, T_text]
        x = x.transpose(1, 2)  # [B, T_text, 512]
        
        # LSTM
        lstm_out, _ = self.lstm(x)
        
        return lstm_out


class Attention(nn.Module):
    """
    注意力机制
    """
    def __init__(self, query_dim=1024, key_dim=512, attention_dim=128):
        super(Attention, self).__init__()
        
        self.query_proj = nn.Linear(query_dim, attention_dim)
        self.key_proj = nn.Linear(key_dim, attention_dim)
        self.score_proj = nn.Linear(attention_dim, 1, bias=False)
    
    def forward(self, query, keys, values, mask=None):
        """
        Args:
            query: [B, 1, query_dim]
            keys: [B, T_key, key_dim]
            values: [B, T_key, key_dim]
            mask: [B, T_key]
        """
        # 投影
        query = self.query_proj(query)  # [B, 1, attention_dim]
        keys = self.key_proj(keys)  # [B, T_key, attention_dim]
        
        # 计算注意力分数
        scores = self.score_proj(torch.tanh(query + keys))  # [B, T_key, 1]
        scores = scores.squeeze(-1)  # [B, T_key]
        
        # 应用 mask
        if mask is not None:
            scores = scores.masked_fill(mask == 0, -float('inf'))
        
        # Softmax
        attention_weights = F.softmax(scores, dim=-1)  # [B, T_key]
        
        # 加权求和
        context = torch.sum(values * attention_weights.unsqueeze(-1), dim=1)  # [B, key_dim]
        
        return context, attention_weights


class Decoder(nn.Module):
    """
    解码器
    """
    def __init__(self, prenet_dim=80, encoder_dim=512, attention_dim=128, num_layers=2):
        super(Decoder, self).__init__()
        
        # Pre-net
        self.prenet = nn.Sequential(
            nn.Linear(prenet_dim, 256),
            nn.ReLU(inplace=True),
            nn.Dropout(0.5),
            nn.Linear(256, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(0.5)
        )
        
        # 注意力
        self.attention = Attention(
            query_dim=128 + 256,
            key_dim=encoder_dim,
            attention_dim=attention_dim
        )
        
        # LSTM
        self.lstm = nn.LSTM(
            128 + 256 + encoder_dim,
            1024,
            num_layers=num_layers,
            batch_first=True
        )
        
        # 线性投影
        self.linear_proj = nn.Linear(1024, 80)
        
        # 停止预测
        self.stop_proj = nn.Linear(1024, 1)
    
    def forward(self, mel_frame, query_state, encoder_outputs, mask=None):
        """
        Args:
            mel_frame: [B, prenet_dim]
            query_state: [B, query_dim]
            encoder_outputs: [B, T_enc, encoder_dim]
            mask: [B, T_enc]
        """
        # Pre-net
        x = self.prenet(mel_frame)  # [B, 128]
        
        # 拼接
        query = torch.cat([x, query_state], dim=-1).unsqueeze(1)  # [B, 1, query_dim]
        
        # 注意力
        context, attention_weights = self.attention(
            query,
            encoder_outputs,
            encoder_outputs,
            mask
        )
        
        # LSTM 输入
        lstm_input = torch.cat([x, context], dim=-1).unsqueeze(1)  # [B, 1, 128 + encoder_dim]
        
        # LSTM
        lstm_out, hidden_state = self.lstm(lstm_input)
        lstm_out = lstm_out.squeeze(1)  # [B, 1024]
        
        # 输出
        mel_output = self.linear_proj(lstm_out)  # [B, 80]
        stop_token = torch.sigmoid(self.stop_proj(lstm_out))  # [B, 1]
        
        return mel_output, stop_token, lstm_out, hidden_state, attention_weights


class Tacotron2(nn.Module):
    """
    Tacotron 2 TTS 模型
    """
    def __init__(self, vocab_size):
        super(Tacotron2, self).__init__()
        
        self.encoder = Encoder(vocab_size)
        self.decoder = Decoder()
    
    def forward(self, text, mel_targets=None, teacher_forcing_ratio=0.9):
        """
        Args:
            text: [B, T_text]
            mel_targets: [B, T_mel, 80] (训练时使用)
            teacher_forcing_ratio: teacher forcing 比例
        """
        batch_size = text.size(0)
        
        # 编码
        encoder_outputs = self.encoder(text)  # [B, T_text, 512]
        
        # 初始化解码器状态
        query_state = torch.zeros(batch_size, 256).to(text.device)
        hidden_state = None
        
        # 生成 Mel 频谱
        mel_outputs = []
        stop_tokens = []
        attention_weights_list = []
        
        # 初始 mel 帧
        mel_frame = torch.zeros(batch_size, 80).to(text.device)
        
        # 生成循环
        max_len = 1000
        for i in range(max_len):
            # 解码器
            mel_output, stop_token, query_state, hidden_state, attention = self.decoder(
                mel_frame,
                query_state,
                encoder_outputs
            )
            
            mel_outputs.append(mel_output)
            stop_tokens.append(stop_token)
            attention_weights_list.append(attention)
            
            # 检查是否停止
            if torch.all(stop_token > 0.5):
                break
            
            # 更新 mel 帧（teacher forcing）
            if mel_targets is not None and torch.rand(1).item() < teacher_forcing_ratio:
                mel_frame = mel_targets[:, i, :]
            else:
                mel_frame = mel_output
        
        # 堆叠输出
        mel_outputs = torch.stack(mel_outputs, dim=1)  # [B, T_mel, 80]
        stop_tokens = torch.cat(stop_tokens, dim=1)  # [B, T_mel]
        attention_weights = torch.stack(attention_weights_list, dim=1)  # [B, T_mel, T_text]
        
        return {
            'mel_outputs': mel_outputs,
            'stop_tokens': stop_tokens,
            'attention_weights': attention_weights
        }


print("Tacotron 2 TTS 模型已定义")
```

### 2. 语音增强与降噪

#### 基于深度学习的语音增强
```python
class SpeechEnhancer(nn.Module):
    """
    语音增强模型
    """
    def __init__(self, num_layers=6, hidden_dim=256):
        super(SpeechEnhancer, self).__init__()
        
        # 编码器
        self.encoder = nn.Sequential(
            nn.Conv1d(1, 16, kernel_size=7, stride=2, padding=3),
            nn.BatchNorm1d(16),
            nn.ReLU(inplace=True),
            
            nn.Conv1d(16, 32, kernel_size=7, stride=2, padding=3),
            nn.BatchNorm1d(32),
            nn.ReLU(inplace=True),
            
            nn.Conv1d(32, 64, kernel_size=7, stride=2, padding=3),
            nn.BatchNorm1d(64),
            nn.ReLU(inplace=True),
            
            nn.Conv1d(64, 128, kernel_size=7, stride=2, padding=3),
            nn.BatchNorm1d(128),
            nn.ReLU(inplace=True),
            
            nn.Conv1d(128, 256, kernel_size=7, stride=2, padding=3),
            nn.BatchNorm1d(256),
            nn.ReLU(inplace=True),
        )
        
        # TCN（时序卷积网络）
        self.tcn = TCN(256, hidden_dim, num_layers)
        
        # 解码器
        self.decoder = nn.Sequential(
            nn.ConvTranspose1d(256, 128, kernel_size=7, stride=2, padding=3, output_padding=1),
            nn.BatchNorm1d(128),
            nn.ReLU(inplace=True),
            
            nn.ConvTranspose1d(128, 64, kernel_size=7, stride=2, padding=3, output_padding=1),
            nn.BatchNorm1d(64),
            nn.ReLU(inplace=True),
            
            nn.ConvTranspose1d(64, 32, kernel_size=7, stride=2, padding=3, output_padding=1),
            nn.BatchNorm1d(32),
            nn.ReLU(inplace=True),
            
            nn.ConvTranspose1d(32, 16, kernel_size=7, stride=2, padding=3, output_padding=1),
            nn.BatchNorm1d(16),
            nn.ReLU(inplace=True),
            
            nn.ConvTranspose1d(16, 1, kernel_size=7, stride=2, padding=3, output_padding=1),
        )
    
    def forward(self, noisy_audio):
        """
        Args:
            noisy_audio: [B, 1, T]
        """
        # 编码
        encoded = self.encoder(noisy_audio)
        
        # TCN
        enhanced = self.tcn(encoded)
        
        # 解码
        clean_audio = self.decoder(enhanced)
        
        return clean_audio


class TCN(nn.Module):
    """
    时序卷积网络
    """
    def __init__(self, in_channels, out_channels, num_layers, kernel_size=3, dropout=0.2):
        super(TCN, self).__init__()
        
        self.tcn_layers = nn.ModuleList()
        
        for i in range(num_layers):
            dilation = 2 ** i
            padding = dilation * (kernel_size - 1) // 2
            
            self.tcn_layers.append(
                nn.Sequential(
                    nn.Conv1d(
                        in_channels if i == 0 else out_channels,
                        out_channels,
                        kernel_size,
                        padding=padding,
                        dilation=dilation
                    ),
                    nn.BatchNorm1d(out_channels),
                    nn.ReLU(inplace=True),
                    nn.Dropout(dropout)
                )
            )
    
    def forward(self, x):
        """
        Args:
            x: [B, C, T]
        """
        for layer in self.tcn_layers:
            x = layer(x)
        
        return x


class SpeechEnhancementLoss(nn.Module):
    """
    语音增强损失
    """
    def __init__(self, alpha=0.1):
        super(SpeechEnhancementLoss, self).__init__()
        self.alpha = alpha  # 频谱损失的权重
    
    def forward(self, enhanced, clean):
        """
        Args:
            enhanced: [B, 1, T]
            clean: [B, 1, T]
        """
        # 时域损失（MSE）
        time_loss = F.mse_loss(enhanced, clean)
        
        # 频谱损失（STFT）
        enhanced_stft = torch.stft(
            enhanced.squeeze(1),
            n_fft=512,
            hop_length=128,
            win_length=512,
            return_complex=True
        )
        clean_stft = torch.stft(
            clean.squeeze(1),
            n_fft=512,
            hop_length=128,
            win_length=512,
            return_complex=True
        )
        
        # 计算幅度损失
        enhanced_mag = torch.abs(enhanced_stft)
        clean_mag = torch.abs(clean_stft)
        spectral_loss = F.mse_loss(enhanced_mag, clean_mag)
        
        # 总损失
        total_loss = time_loss + self.alpha * spectral_loss
        
        return total_loss


print("语音增强模型已定义")
```

### 3. 说话人识别与验证

#### ECAPA-TDNN 风格的说话人识别
```python
class ECAPA_TDNN(nn.Module):
    """
    ECAPA-TDNN 说话人识别模型
    """
    def __init__(self, input_dim=80, embedding_dim=192):
        super(ECAPA_TDNN, self).__init__()
        
        # TDNN 层
        self.tdnn1 = TDNNBlock(input_dim, 512, kernel_size=5, dilation=1)
        self.tdnn2 = TDNNBlock(1536, 512, kernel_size=3, dilation=2)
        self.tdnn3 = TDNNBlock(1536, 512, kernel_size=3, dilation=3)
        self.tdnn4 = TDNNBlock(1536, 512, kernel_size=3, dilation=4)
        self.tdnn5 = TDNNBlock(1536, 1536, kernel_size=1, dilation=1)
        
        # 注意力统计池化
        self.attention = ASP(1536)
        
        # 嵌入层
        self.embedding = nn.Sequential(
            nn.BatchNorm1d(3072),
            nn.Linear(3072, embedding_dim),
            nn.BatchNorm1d(embedding_dim)
        )
    
    def forward(self, x):
        """
        Args:
            x: [B, T, D] (Mel 频谱)
        """
        # 转置
        x = x.transpose(1, 2)  # [B, D, T]
        
        # TDNN 层
        x1 = self.tdnn1(x)
        x2 = self.tdnn2(torch.cat([x, x1], dim=1))
        x3 = self.tdnn3(torch.cat([x, x1, x2], dim=1))
        x4 = self.tdnn4(torch.cat([x, x1, x2, x3], dim=1))
        x5 = self.tdnn5(torch.cat([x, x1, x2, x3, x4], dim=1))
        
        # 注意力统计池化
        stats = self.attention(x5)
        
        # 嵌入
        embeddings = self.embedding(stats)
        
        return embeddings


class TDNNBlock(nn.Module):
    """
    TDNN 块
    """
    def __init__(self, in_channels, out_channels, kernel_size, dilation):
        super(TDNNBlock, self).__init__()
        
        padding = dilation * (kernel_size - 1) // 2
        
        self.conv1 = nn.Conv1d(
            in_channels,
            out_channels,
            kernel_size,
            padding=padding,
            dilation=dilation
        )
        self.bn1 = nn.BatchNorm1d(out_channels)
        self.relu = nn.ReLU(inplace=True)
        
        self.conv2 = nn.Conv1d(out_channels, out_channels, 1)
        self.bn2 = nn.BatchNorm1d(out_channels)
    
    def forward(self, x):
        """
        Args:
            x: [B, C, T]
        """
        y = self.conv1(x)
        y = self.bn1(y)
        y = self.relu(y)
        
        y = self.conv2(y)
        y = self.bn2(y)
        y = self.relu(y)
        
        return y


class ASP(nn.Module):
    """
    注意力统计池化
    """
    def __init__(self, input_dim):
        super(ASP, self).__init__()
        
        self.attention = nn.Sequential(
            nn.Conv1d(input_dim, 128, kernel_size=1),
            nn.ReLU(inplace=True),
            nn.BatchNorm1d(128),
            nn.Conv1d(128, input_dim, kernel_size=1),
            nn.Softmax(dim=-1)
        )
    
    def forward(self, x):
        """
        Args:
            x: [B, C, T]
        """
        # 计算注意力权重
        w = self.attention(x)  # [B, C, T]
        
        # 加权平均
        mu = torch.sum(x * w, dim=2)  # [B, C]
        
        # 加权标准差
        residual = x - mu.unsqueeze(-1)
        std = torch.sqrt(torch.sum(residual ** 2 * w, dim=2) + 1e-8)  # [B, C]
        
        # 拼接
        stats = torch.cat([mu, std], dim=1)  # [B, 2C]
        
        return stats


class SpeakerVerificationLoss(nn.Module):
    """
    说话人验证损失
    """
    def __init__(self, num_classes, embedding_dim=192, scale=30.0, margin=0.2):
        super(SpeakerVerificationLoss, self).__init__()
        
        self.scale = scale
        self.margin = margin
        
        # 分类器（用于计算损失）
        self.classifier = nn.Linear(embedding_dim, num_classes)
    
    def forward(self, embeddings, labels):
        """
        Args:
            embeddings: [B, embedding_dim]
            labels: [B]
        """
        # 归一化嵌入
        embeddings = F.normalize(embeddings, p=2, dim=1)
        
        # 分类
        logits = self.classifier(embeddings)
        
        # AM-Softmax 损失
        loss = self.am_softmax_loss(logits, labels)
        
        return loss
    
    def am_softmax_loss(self, logits, labels):
        """
        AM-Softmax 损失
        """
        # 归一化权重
        W = F.normalize(self.classifier.weight, p=2, dim=1)
        
        # 计算余弦相似度
        logits = logits / torch.norm(W, dim=1, keepdim=True)
        
        # 应用 margin
        target_logits = logits[torch.arange(logits.size(0)), labels]
        target_logits = target_logits - self.margin
        
        # 替换目标类别的 logits
        logits[torch.arange(logits.size(0)), labels] = target_logits
        
        # 缩放
        logits = logits * self.scale
        
        # 交叉熵损失
        loss = F.cross_entropy(logits, labels)
        
        return loss


class SpeakerVerifier:
    """
    说话人验证器
    """
    def __init__(self, model_path=None, embedding_dim=192):
        self.model = ECAPA_TDNN(embedding_dim=embedding_dim)
        
        if model_path is not None:
            self.model.load_state_dict(torch.load(model_path))
        
        self.model.eval()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        
        # 预注册的说话人
        self.registered_speakers = {}
    
    def enroll(self, speaker_id, audio_features):
        """
        注册说话人
        Args:
            speaker_id: 说话人 ID
            audio_features: [T, D] 或 [B, T, D]
        """
        # 提取嵌入
        if audio_features.dim() == 2:
            audio_features = audio_features.unsqueeze(0)
        
        with torch.no_grad():
            embedding = self.model(audio_features.to(self.device))
            embedding = F.normalize(embedding, p=2, dim=1)
        
        # 存储嵌入（取平均）
        embedding = embedding.mean(dim=0).cpu().numpy()
        self.registered_speakers[speaker_id] = embedding
    
    def verify(self, audio_features, speaker_id, threshold=0.25):
        """
        验证说话人
        Args:
            audio_features: [T, D] 或 [B, T, D]
            speaker_id: 说话人 ID
            threshold: 验证阈值
        """
        if speaker_id not in self.registered_speakers:
            return False, 0.0
        
        # 提取嵌入
        if audio_features.dim() == 2:
            audio_features = audio_features.unsqueeze(0)
        
        with torch.no_grad():
            embedding = self.model(audio_features.to(self.device))
            embedding = F.normalize(embedding, p=2, dim=1)
        
        # 计算相似度
        registered_embedding = torch.from_numpy(
            self.registered_speakers[speaker_id]
        ).to(self.device)
        
        similarity = F.cosine_similarity(embedding, registered_embedding).item()
        
        # 验证
        is_same = similarity > threshold
        
        return is_same, similarity


print("说话人识别模型已定义")
```

---

## 跨模态检索优化

### 1. 高效索引与检索

#### HNSW（Hierarchical Navigable Small World）
```python
import numpy as np
from typing import List, Tuple

class HNSWNode:
    """
    HNSW 节点
    """
    def __init__(self, vector: np.ndarray, level: int):
        self.vector = vector
        self.level = level
        self.connections = [[] for _ in range(level + 1)]


class HNSW:
    """
    层次化可导航小世界图
    """
    def __init__(self, dim: int, max_level: int = 16, ef_construction: int = 200):
        self.dim = dim
        self.max_level = max_level
        self.ef_construction = ef_construction
        
        # 入口点
        self.entry_point = None
        
        # 节点列表
        self.nodes: List[HNSWNode] = []
        
        # 连接参数
        self.M = 32  # 每层最大连接数
        self.Mmax0 = 64  # 第 0 层最大连接数
    
    def add(self, vector: np.ndarray) -> int:
        """
        添加向量
        """
        # 随机分配层级
        level = min(self._get_random_level(), self.max_level)
        
        # 创建节点
        node = HNSWNode(vector, level)
        node_id = len(self.nodes)
        self.nodes.append(node)
        
        # 搜索最近邻
        if self.entry_point is None:
            self.entry_point = node
            return node_id
        
        # 从顶层开始搜索
        curr = self.entry_point
        for l in range(level, -1, -1):
            curr, dist = self._search_layer(curr, vector, l, 1)
        
        # 连接节点
        for l in range(min(level, self.entry_point.level) + 1):
            candidates = self._select_neighbors_heuristic(curr.connections[l], vector, self.M)
            
            # 添加连接
            for candidate in candidates:
                candidate.connections[l].append(node)
                node.connections[l].append(candidate)
                
                # 修剪连接
                if len(node.connections[l]) > self.M if l > 0 else self.Mmax0:
                    node.connections[l] = self._select_neighbors_heuristic(
                        node.connections[l], node.vector, self.M if l > 0 else self.Mmax0
                    )
        
        # 更新入口点
        if level > self.entry_point.level:
            self.entry_point = node
        
        return node_id
    
    def search(self, query: np.ndarray, k: int = 5, ef: int = 50) -> List[Tuple[int, float]]:
        """
        搜索最近邻
        """
        if self.entry_point is None:
            return []
        
        # 从顶层开始搜索
        curr = self.entry_point
        for l in range(self.entry_point.level, 0, -1):
            curr, dist = self._search_layer(curr, query, l, 1)
        
        # 在第 0 层搜索 ef 个最近邻
        curr, dist = self._search_layer(curr, query, 0, ef)
        
        # 收集候选
        candidates = []
        visited = set()
        
        # BFS 搜索
        queue = [(dist, curr)]
        visited.add(curr)
        
        while queue and len(candidates) < ef:
            dist, node = sorted(queue, key=lambda x: x[0])[0]
            queue.remove((dist, node))
            
            candidates.append((dist, node))
            
            for neighbor in node.connections[0]:
                if neighbor not in visited:
                    neighbor_dist = np.linalg.norm(neighbor.vector - query)
                    queue.append((neighbor_dist, neighbor))
                    visited.add(neighbor)
        
        # 排序并返回 top-k
        candidates = sorted(candidates, key=lambda x: x[0])[:k]
        
        # 返回节点 ID 和距离
        results = []
        for dist, node in candidates:
            node_id = self.nodes.index(node)
            results.append((node_id, dist))
        
        return results
    
    def _search_layer(self, entry: HNSWNode, query: np.ndarray, level: int, ef: int):
        """
        在指定层级搜索
        """
        curr = entry
        curr_dist = np.linalg.norm(curr.vector - query)
        
        candidates = [(curr_dist, curr)]
        visited = {curr}
        
        while candidates:
            candidates.sort(key=lambda x: x[0])
            best_dist, best_node = candidates[0]
            
            # 检查是否可以改进
            improved = False
            for neighbor in best_node.connections[level]:
                if neighbor not in visited:
                    dist = np.linalg.norm(neighbor.vector - query)
                    if dist < best_dist:
                        candidates.append((dist, neighbor))
                        visited.add(neighbor)
                        improved = True
            
            if not improved:
                break
        
        return best_node, best_dist
    
    def _select_neighbors_heuristic(self, candidates: List[HNSWNode], query: np.ndarray, M: int) -> List[HNSWNode]:
        """
        启发式选择邻居
        """
        # 计算距离
        dists = [(np.linalg.norm(node.vector - query), node) for node in candidates]
        dists.sort(key=lambda x: x[0])
        
        # 选择最近的 M 个
        return [node for _, node in dists[:M]]
    
    def _get_random_level(self) -> int:
        """
        随机生成层级
        """
        return int(-np.log(np.random.random()) * np.log(self.M))


# 使用示例
if __name__ == "__main__":
    import time
    
    # 创建 HNSW
    hnsw = HNSW(dim=512)
    
    # 生成随机向量
    num_vectors = 10000
    vectors = np.random.randn(num_vectors, 512)
    
    # 添加向量
    start_time = time.time()
    for i, vector in enumerate(vectors):
        hnsw.add(vector)
    print(f"添加 {num_vectors} 个向量耗时: {time.time() - start_time:.2f} 秒")
    
    # 搜索
    query = np.random.randn(512)
    start_time = time.time()
    results = hnsw.search(query, k=5)
    print(f"搜索耗时: {time.time() - start_time:.6f} 秒")
    
    print(f"Top-5 结果: {results}")
    
    print("HNSW 已定义")
```

### 2. 近似最近邻搜索（ANN）

#### Faiss 集成
```python
import numpy as np
import faiss

class ANNIndex:
    """
    近似最近邻索引（基于 Faiss）
    """
    def __init__(self, dim: int, index_type: str = 'IVFPQ'):
        self.dim = dim
        self.index_type = index_type
        self.index = None
        self.is_trained = False
    
    def build_index(self, vectors: np.ndarray, nlist: int = 100):
        """
        构建索引
        Args:
            vectors: [N, D]
            nlist: 聚类中心数量
        """
        if self.index_type == 'IVFPQ':
            # IVF + PQ（倒排文件 + 乘积量化）
            quantizer = faiss.IndexFlatL2(self.dim)
            self.index = faiss.IndexIVFPQ(quantizer, self.dim, nlist, 8, 8)
        elif self.index_type == 'IVF':
            # IVF（倒排文件）
            quantizer = faiss.IndexFlatL2(self.dim)
            self.index = faiss.IndexIVFFlat(quantizer, self.dim, nlist)
        elif self.index_type == 'HNSW':
            # HNSW
            self.index = faiss.IndexHNSWFlat(self.dim, 32)
        elif self.index_type == 'Flat':
            # 精确搜索
            self.index = faiss.IndexFlatL2(self.dim)
        else:
            raise ValueError(f"Unknown index type: {self.index_type}")
        
        # 训练索引
        if not self.index.is_trained:
            self.index.train(vectors)
        
        # 添加向量
        self.index.add(vectors)
        self.is_trained = True
    
    def search(self, query: np.ndarray, k: int = 5, nprobe: int = 10) -> Tuple[np.ndarray, np.ndarray]:
        """
        搜索
        Args:
            query: [Q, D] 或 [D]
            k: 返回 top-k
            nprobe: 搜索的聚类中心数量（仅 IVF 索引）
        Returns:
            distances: [Q, k]
            indices: [Q, k]
        """
        if not self.is_trained:
            raise RuntimeError("Index not trained. Call build_index first.")
        
        # 设置 nprobe（IVF 索引）
        if hasattr(self.index, 'nprobe'):
            self.index.nprobe = nprobe
        
        # 确保是 2D 数组
        if query.ndim == 1:
            query = query.reshape(1, -1)
        
        # 搜索
        distances, indices = self.index.search(query, k)
        
        return distances, indices
    
    def save(self, file_path: str):
        """
        保存索引
        """
        faiss.write_index(self.index, file_path)
    
    def load(self, file_path: str):
        """
        加载索引
        """
        self.index = faiss.read_index(file_path)
        self.is_trained = True


class MultiModalIndex:
    """
    多模态索引
    """
    def __init__(self, dim: int):
        self.dim = dim
        
        # 不同模态的索引
        self.text_index = ANNIndex(dim, index_type='IVFPQ')
        self.image_index = ANNIndex(dim, index_type='IVFPQ')
        self.audio_index = ANNIndex(dim, index_type='IVFPQ')
        self.video_index = ANNIndex(dim, index_type='IVFPQ')
        
        # 元数据
        self.text_metadata = []
        self.image_metadata = []
        self.audio_metadata = []
        self.video_metadata = []
    
    def add_text(self, vectors: np.ndarray, metadata: list):
        """
        添加文本
        """
        if not self.text_index.is_trained:
            self.text_index.build_index(vectors)
        else:
            self.text_index.index.add(vectors)
        
        self.text_metadata.extend(metadata)
    
    def add_image(self, vectors: np.ndarray, metadata: list):
        """
        添加图像
        """
        if not self.image_index.is_trained:
            self.image_index.build_index(vectors)
        else:
            self.image_index.index.add(vectors)
        
        self.image_metadata.extend(metadata)
    
    def add_audio(self, vectors: np.ndarray, metadata: list):
        """
        添加音频
        """
        if not self.audio_index.is_trained:
            self.audio_index.build_index(vectors)
        else:
            self.audio_index.index.add(vectors)
        
        self.audio_metadata.extend(metadata)
    
    def add_video(self, vectors: np.ndarray, metadata: list):
        """
        添加视频
        """
        if not self.video_index.is_trained:
            self.video_index.build_index(vectors)
        else:
            self.video_index.index.add(vectors)
        
        self.video_metadata.extend(metadata)
    
    def search(self, query: np.ndarray, modality: str = 'all', k: int = 5) -> list:
        """
        跨模态搜索
        """
        results = []
        
        # 搜索文本
        if modality in ['all', 'text'] and self.text_index.is_trained:
            distances, indices = self.text_index.search(query, k)
            for dist, idx in zip(distances[0], indices[0]):
                if idx != -1:
                    results.append({
                        'modality': 'text',
                        'distance': float(dist),
                        'metadata': self.text_metadata[idx]
                    })
        
        # 搜索图像
        if modality in ['all', 'image'] and self.image_index.is_trained:
            distances, indices = self.image_index.search(query, k)
            for dist, idx in zip(distances[0], indices[0]):
                if idx != -1:
                    results.append({
                        'modality': 'image',
                        'distance': float(dist),
                        'metadata': self.image_metadata[idx]
                    })
        
        # 搜索音频
        if modality in ['all', 'audio'] and self.audio_index.is_trained:
            distances, indices = self.audio_index.search(query, k)
            for dist, idx in zip(distances[0], indices[0]):
                if idx != -1:
                    results.append({
                        'modality': 'audio',
                        'distance': float(dist),
                        'metadata': self.audio_metadata[idx]
                    })
        
        # 搜索视频
        if modality in ['all', 'video'] and self.video_index.is_trained:
            distances, indices = self.video_index.search(query, k)
            for dist, idx in zip(distances[0], indices[0]):
                if idx != -1:
                    results.append({
                        'modality': 'video',
                        'distance': float(dist),
                        'metadata': self.video_metadata[idx]
                    })
        
        # 排序
        results.sort(key=lambda x: x['distance'])
        
        return results[:k]


# 使用示例
if __name__ == "__main__":
    import time
    
    # 创建多模态索引
    index = MultiModalIndex(dim=512)
    
    # 添加数据
    text_vectors = np.random.randn(1000, 512)
    image_vectors = np.random.randn(2000, 512)
    
    index.add_text(text_vectors, [{"id": i, "type": "text"} for i in range(1000)])
    index.add_image(image_vectors, [{"id": i, "type": "image"} for i in range(2000)])
    
    # 搜索
    query = np.random.randn(512)
    start_time = time.time()
    results = index.search(query, modality='all', k=10)
    print(f"搜索耗时: {time.time() - start_time:.6f} 秒")
    
    for result in results:
        print(f"{result['modality']}: {result['distance']:.4f} - {result['metadata']}")
    
    print("多模态索引已定义")
```

---

## 内容生成高级技术

### 1. 图像生成（Stable Diffusion 风格）

#### U-Net 架构
```python
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional

class ResidualBlock(nn.Module):
    """
    残差块
    """
    def __init__(self, in_channels, out_channels, dropout=0.0):
        super(ResidualBlock, self).__init__()
        
        self.norm1 = nn.GroupNorm(32, in_channels)
        self.conv1 = nn.Conv2d(in_channels, out_channels, 3, padding=1)
        
        self.norm2 = nn.GroupNorm(32, out_channels)
        self.conv2 = nn.Conv2d(out_channels, out_channels, 3, padding=1)
        
        self.dropout = nn.Dropout(dropout) if dropout > 0 else nn.Identity()
        
        # 如果通道数不同，使用 1x1 卷积
        if in_channels != out_channels:
            self.shortcut = nn.Conv2d(in_channels, out_channels, 1)
        else:
            self.shortcut = nn.Identity()
    
    def forward(self, x, time_emb=None):
        """
        Args:
            x: [B, C, H, W]
            time_emb: [B, C]
        """
        # 第一个卷积
        h = self.norm1(x)
        h = F.silu(h)
        h = self.conv1(h)
        
        # 添加时间嵌入
        if time_emb is not None:
            h = h + time_emb[..., None, None]
        
        # 第二个卷积
        h = self.norm2(h)
        h = F.silu(h)
        h = self.dropout(h)
        h = self.conv2(h)
        
        # 残差连接
        return h + self.shortcut(x)


class AttentionBlock(nn.Module):
    """
    注意力块
    """
    def __init__(self, channels, num_heads=4):
        super(AttentionBlock, self).__init__()
        
        self.num_heads = num_heads
        self.channels = channels
        self.head_dim = channels // num_heads
        
        self.norm = nn.GroupNorm(32, channels)
        
        self.qkv = nn.Conv2d(channels, channels * 3, 1)
        self.proj = nn.Conv2d(channels, channels, 1)
    
    def forward(self, x):
        """
        Args:
            x: [B, C, H, W]
        """
        B, C, H, W = x.shape
        
        # 归一化
        h = self.norm(x)
        
        # QKV
        qkv = self.qkv(h)  # [B, 3*C, H, W]
        q, k, v = qkv.chunk(3, dim=1)
        
        # 重塑为多头
        q = q.view(B, self.num_heads, self.head_dim, -1)  # [B, num_heads, head_dim, H*W]
        k = k.view(B, self.num_heads, self.head_dim, -1)
        v = v.view(B, self.num_heads, self.head_dim, -1)
        
        # 注意力
        attn = torch.matmul(q.transpose(-1, -2), k)  # [B, num_heads, H*W, H*W]
        attn = attn / (self.head_dim ** 0.5)
        attn = F.softmax(attn, dim=-1)
        
        # 加权求和
        out = torch.matmul(v, attn.transpose(-1, -2))  # [B, num_heads, head_dim, H*W]
        out = out.view(B, C, H, W)
        
        # 投影
        out = self.proj(out)
        
        return out


class UNet(nn.Module):
    """
    U-Net 扩散模型
    """
    def __init__(
        self,
        in_channels=3,
        out_channels=3,
        base_channels=128,
        channel_mults=[1, 2, 2, 4],
        num_res_blocks=2,
        attention_resolutions=[16, 8],
        num_heads=4,
        dropout=0.1
    ):
        super(UNet, self).__init__()
        
        # 时间嵌入
        self.time_mlp = nn.Sequential(
            nn.Linear(128, base_channels * 4),
            nn.SiLU(),
            nn.Linear(base_channels * 4, base_channels * 4)
        )
        
        # 下采样
        self.down_blocks = nn.ModuleList()
        channels = [base_channels * m for m in channel_mults]
        
        # 输入卷积
        self.input_conv = nn.Conv2d(in_channels, base_channels, 3, padding=1)
        
        # 下采样层
        in_ch = base_channels
        for i, out_ch in enumerate(channels):
            down_block = []
            for _ in range(num_res_blocks):
                down_block.append(ResidualBlock(in_ch, out_ch, dropout))
                in_ch = out_ch
            
            # 注意力层
            if 2 ** i in attention_resolutions:
                down_block.append(AttentionBlock(out_ch, num_heads))
            
            # 下采样
            if i < len(channels) - 1:
                down_block.append(nn.Conv2d(out_ch, out_ch, 3, stride=2, padding=1))
            
            self.down_blocks.append(nn.ModuleList(down_block))
        
        # 中间层
        self.mid_blocks = nn.ModuleList([
            ResidualBlock(channels[-1], channels[-1], dropout),
            AttentionBlock(channels[-1], num_heads),
            ResidualBlock(channels[-1], channels[-1], dropout)
        ])
        
        # 上采样
        self.up_blocks = nn.ModuleList()
        
        for i, out_ch in enumerate(reversed(channels[:-1])):
            up_block = []
            
            # 上采样
            up_block.append(nn.ConvTranspose2d(channels[-1] * 2, out_ch, 3, stride=2, padding=1, output_padding=1))
            
            # 残差块
            for _ in range(num_res_blocks + 1):
                up_block.append(ResidualBlock(out_ch * 2, out_ch, dropout))
            
            # 注意力层
            if 2 ** (len(channels) - 2 - i) in attention_resolutions:
                up_block.append(AttentionBlock(out_ch, num_heads))
            
            channels[-1] = out_ch
            self.up_blocks.append(nn.ModuleList(up_block))
        
        # 输出层
        self.output_conv = nn.Sequential(
            nn.GroupNorm(32, base_channels),
            nn.SiLU(),
            nn.Conv2d(base_channels, out_channels, 3, padding=1)
        )
    
    def forward(self, x, timestep):
        """
        Args:
            x: [B, C, H, W]
            timestep: [B]
        """
        # 时间嵌入
        t_emb = self._get_time_embedding(timestep)
        t_emb = self.time_mlp(t_emb)  # [B, base_channels * 4]
        
        # 输入卷积
        h = self.input_conv(x)
        
        # 下采样
        skips = []
        for down_block in self.down_blocks:
            for layer in down_block:
                if isinstance(layer, ResidualBlock):
                    h = layer(h, t_emb)
                elif isinstance(layer, AttentionBlock):
                    h = layer(h)
                else:
                    h = layer(h)
                skips.append(h)
        
        # 中间层
        for layer in self.mid_blocks:
            if isinstance(layer, ResidualBlock):
                h = layer(h, t_emb)
            else:
                h = layer(h)
        
        # 上采样
        for up_block in self.up_blocks:
            h = up_block[0](h)  # 上采样
            
            # 拼接 skip connection
            h = torch.cat([h, skips.pop()], dim=1)
            
            for layer in up_block[1:]:
                if isinstance(layer, ResidualBlock):
                    h = layer(h, t_emb)
                else:
                    h = layer(h)
        
        # 输出
        return self.output_conv(h)
    
    def _get_time_embedding(self, timestep):
        """
        获取时间嵌入
        Args:
            timestep: [B]
        Returns:
            [B, 128]
        """
        # 正弦位置编码
        half_dim = 64
        embeddings = math.log(10000) / (half_dim - 1)
        embeddings = torch.exp(torch.arange(half_dim) * -embeddings).to(timestep.device)
        embeddings = timestep[:, None] * embeddings[None, :]
        embeddings = torch.cat([torch.sin(embeddings), torch.cos(embeddings)], dim=-1)
        
        return embeddings


import math

print("U-Net 扩散模型已定义")
```

### 2. 文本生成（GPT 风格）

#### Transformer 解码器
```python
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional

class MultiHeadAttention(nn.Module):
    """
    多头注意力
    """
    def __init__(self, d_model, num_heads, dropout=0.1):
        super(MultiHeadAttention, self).__init__()
        
        self.d_model = d_model
        self.num_heads = num_heads
        self.head_dim = d_model // num_heads
        
        assert d_model % num_heads == 0, "d_model must be divisible by num_heads"
        
        self.q_proj = nn.Linear(d_model, d_model)
        self.k_proj = nn.Linear(d_model, d_model)
        self.v_proj = nn.Linear(d_model, d_model)
        self.out_proj = nn.Linear(d_model, d_model)
        
        self.dropout = nn.Dropout(dropout)
    
    def forward(self, query, key, value, mask=None):
        """
        Args:
            query: [B, T_q, D]
            key: [B, T_k, D]
            value: [B, T_k, D]
            mask: [B, T_q, T_k]
        """
        B, T_q, D = query.shape
        T_k = key.shape[1]
        
        # QKV 投影
        Q = self.q_proj(query)  # [B, T_q, D]
        K = self.k_proj(key)    # [B, T_k, D]
        V = self.v_proj(value)  # [B, T_k, D]
        
        # 重塑为多头
        Q = Q.view(B, T_q, self.num_heads, self.head_dim).transpose(1, 2)  # [B, num_heads, T_q, head_dim]
        K = K.view(B, T_k, self.num_heads, self.head_dim).transpose(1, 2)
        V = V.view(B, T_k, self.num_heads, self.head_dim).transpose(1, 2)
        
        # 注意力分数
        scores = torch.matmul(Q, K.transpose(-2, -1)) / (self.head_dim ** 0.5)  # [B, num_heads, T_q, T_k]
        
        # 应用 mask
        if mask is not None:
            scores = scores.masked_fill(mask.unsqueeze(1) == 0, -float('inf'))
        
        # Softmax
        attn_weights = F.softmax(scores, dim=-1)
        attn_weights = self.dropout(attn_weights)
        
        # 加权求和
        context = torch.matmul(attn_weights, V)  # [B, num_heads, T_q, head_dim]
        
        # 拼接多头
        context = context.transpose(1, 2).contiguous().view(B, T_q, D)  # [B, T_q, D]
        
        # 输出投影
        output = self.out_proj(context)
        
        return output


class FeedForward(nn.Module):
    """
    前馈网络
    """
    def __init__(self, d_model, d_ff, dropout=0.1):
        super(FeedForward, self).__init__()
        
        self.net = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(d_ff, d_model),
            nn.Dropout(dropout)
        )
    
    def forward(self, x):
        return self.net(x)


class TransformerDecoderLayer(nn.Module):
    """
    Transformer 解码器层
    """
    def __init__(self, d_model, num_heads, d_ff, dropout=0.1):
        super(TransformerDecoderLayer, self).__init__()
        
        self.self_attn = MultiHeadAttention(d_model, num_heads, dropout)
        self.cross_attn = MultiHeadAttention(d_model, num_heads, dropout)
        self.ff = FeedForward(d_model, d_ff, dropout)
        
        self.norm1 = nn.LayerNorm(d_model)
        self.norm2 = nn.LayerNorm(d_model)
        self.norm3 = nn.LayerNorm(d_model)
        
        self.dropout = nn.Dropout(dropout)
    
    def forward(self, x, encoder_output=None, self_attn_mask=None, cross_attn_mask=None):
        """
        Args:
            x: [B, T, D]
            encoder_output: [B, S, D]
            self_attn_mask: [B, T, T]
            cross_attn_mask: [B, T, S]
        """
        # 自注意力
        residual = x
        x = self.norm1(x)
        x = self.self_attn(x, x, x, mask=self_attn_mask)
        x = self.dropout(x)
        x = x + residual
        
        # 交叉注意力（如果有 encoder）
        if encoder_output is not None:
            residual = x
            x = self.norm2(x)
            x = self.cross_attn(x, encoder_output, encoder_output, mask=cross_attn_mask)
            x = self.dropout(x)
            x = x + residual
        
        # 前馈网络
        residual = x
        x = self.norm3(x)
        x = self.ff(x)
        x = x + residual
        
        return x


class GPT(nn.Module):
    """
    GPT 风格的语言模型
    """
    def __init__(
        self,
        vocab_size,
        d_model=768,
        num_layers=12,
        num_heads=12,
        d_ff=3072,
        max_seq_len=1024,
        dropout=0.1
    ):
        super(GPT, self).__init__()
        
        self.d_model = d_model
        self.max_seq_len = max_seq_len
        
        # Token 嵌入
        self.token_embed = nn.Embedding(vocab_size, d_model)
        
        # 位置嵌入
        self.pos_embed = nn.Embedding(max_seq_len, d_model)
        
        # 解码器层
        self.layers = nn.ModuleList([
            TransformerDecoderLayer(d_model, num_heads, d_ff, dropout)
            for _ in range(num_layers)
        ])
        
        # 层归一化
        self.norm = nn.LayerNorm(d_model)
        
        # 输出投影
        self.output_proj = nn.Linear(d_model, vocab_size)
        
        # Dropout
        self.dropout = nn.Dropout(dropout)
    
    def forward(self, input_ids, attention_mask=None):
        """
        Args:
            input_ids: [B, T]
            attention_mask: [B, T]
        """
        B, T = input_ids.shape
        
        # Token 嵌入
        token_embed = self.token_embed(input_ids)  # [B, T, D]
        
        # 位置嵌入
        positions = torch.arange(T, device=input_ids.device)
        pos_embed = self.pos_embed(positions)  # [T, D]
        
        # 合并嵌入
        x = token_embed + pos_embed.unsqueeze(0)
        x = self.dropout(x)
        
        # 自注意力 mask
        if attention_mask is not None:
            # 扩展 mask 为 [B, T, T]
            self_attn_mask = attention_mask.unsqueeze(1) & attention_mask.unsqueeze(2)
            # 因果 mask
            causal_mask = torch.tril(torch.ones(T, T, device=input_ids.device)).bool()
            self_attn_mask = self_attn_mask & causal_mask
        else:
            self_attn_mask = torch.tril(torch.ones(T, T, device=input_ids.device)).bool()
        
        # 解码器层
        for layer in self.layers:
            x = layer(x, self_attn_mask=self_attn_mask)
        
        # 归一化
        x = self.norm(x)
        
        # 输出 logits
        logits = self.output_proj(x)  # [B, T, vocab_size]
        
        return logits
    
    def generate(
        self,
        input_ids,
        max_length=100,
        temperature=1.0,
        top_k=50,
        top_p=0.9,
        do_sample=True
    ):
        """
        生成文本
        """
        self.eval()
        
        with torch.no_grad():
            for _ in range(max_length):
                # 截断到最大长度
                if input_ids.size(1) >= self.max_seq_len:
                    input_ids = input_ids[:, -self.max_seq_len:]
                
                # 前向传播
                logits = self.forward(input_ids)
                
                # 获取最后一个 token 的 logits
                next_token_logits = logits[:, -1, :]
                
                # 温度缩放
                next_token_logits = next_token_logits / temperature
                
                # Top-k 采样
                if top_k > 0:
                    values, indices = torch.topk(next_token_logits, top_k)
                    next_token_logits = torch.full_like(next_token_logits, float('-inf'))
                    next_token_logits.scatter_(1, indices, values)
                
                # Top-p (nucleus) 采样
                if top_p < 1.0:
                    sorted_logits, sorted_indices = torch.sort(next_token_logits, descending=True)
                    cumulative_probs = torch.cumsum(F.softmax(sorted_logits, dim=-1), dim=-1)
                    
                    # 移除超过 top-p 的 token
                    sorted_indices_to_remove = cumulative_probs > top_p
                    sorted_indices_to_remove[..., 1:] = sorted_indices_to_remove[..., :-1].clone()
                    sorted_indices_to_remove[..., 0] = 0
                    
                    indices_to_remove = sorted_indices_to_remove.scatter(1, sorted_indices, sorted_indices_to_remove)
                    next_token_logits = next_token_logits.masked_fill(indices_to_remove, float('-inf'))
                
                # 采样下一个 token
                if do_sample:
                    probs = F.softmax(next_token_logits, dim=-1)
                    next_token = torch.multinomial(probs, num_samples=1)
                else:
                    next_token = next_token_logits.argmax(dim=-1, keepdim=True)
                
                # 拼接
                input_ids = torch.cat([input_ids, next_token], dim=1)
                
                # 检查是否达到 EOS
                if next_token.item() == 0:  # 假设 0 是 EOS token
                    break
        
        return input_ids


print("GPT 模型已定义")
```

### 3. 跨模态生成

#### 文本到图像（CLIP + Diffusion）
```python
class TextToImageGenerator(nn.Module):
    """
    文本到图像生成器
    """
    def __init__(
        self,
        text_encoder_name="openai/clip-vit-base-patch32",
        diffusion_model=UNet,
        d_model=512
    ):
        super(TextToImageGenerator, self).__init__()
        
        # 加载 CLIP 文本编码器
        from transformers import CLIPTextModel, CLIPTokenizer
        self.text_encoder = CLIPTextModel.from_pretrained(text_encoder_name)
        self.tokenizer = CLIPTokenizer.from_pretrained(text_encoder_name)
        
        # 冻结文本编码器
        for param in self.text_encoder.parameters():
            param.requires_grad = False
        
        # 扩散模型
        self.diffusion_model = diffusion_model(
            in_channels=d_model,
            out_channels=4,  # UNet 输出 4 通道（用于 VAE）
            base_channels=128
        )
        
        # 文本嵌入投影
        self.text_proj = nn.Linear(512, d_model)
        
        # 条件投影
        self.cond_proj = nn.Sequential(
            nn.Linear(512, d_model * 4),
            nn.SiLU(),
            nn.Linear(d_model * 4, d_model * 4)
        )
    
    def encode_text(self, text):
        """
        编码文本
        """
        inputs = self.tokenizer(
            text,
            padding=True,
            truncation=True,
            return_tensors="pt"
        )
        
        outputs = self.text_encoder(**inputs)
        text_embeds = outputs.last_hidden_state  # [B, T, 512]
        pooled_embeds = outputs.pooler_output  # [B, 512]
        
        return text_embeds, pooled_embeds
    
    def forward(self, noisy_latent, timestep, text_embeds):
        """
        前向传播
        Args:
            noisy_latent: [B, 4, H, W] (VAE 潜空间)
            timestep: [B]
            text_embeds: [B, T, 512]
        """
        # 投影文本嵌入
        text_embeds = self.text_proj(text_embeds)  # [B, T, d_model]
        
        # 条件嵌入
        cond_embed = self.cond_proj(text_embeds.mean(dim=1))  # [B, d_model * 4]
        
        # 扩散模型
        noise_pred = self.diffusion_model(noisy_latent, timestep)
        
        return noise_pred
    
    @torch.no_grad()
    def generate(
        self,
        text,
        num_inference_steps=50,
        guidance_scale=7.5,
        height=512,
        width=512
    ):
        """
        生成图像
        """
        # 编码文本
        text_embeds, pooled_embeds = self.encode_text(text)
        
        # 初始化噪声
        latent = torch.randn(1, 4, height // 8, width // 8).to(text_embeds.device)
        
        # 采样
        for i, t in enumerate(torch.linspace(1000, 0, num_inference_steps)):
            t = torch.tensor([t]).to(latent.device).long()
            
            # 无条件预测
            noise_pred_uncond = self.forward(latent, t, text_embeds * 0)
            
            # 条件预测
            noise_pred_cond = self.forward(latent, t, text_embeds)
            
            # CFG（Classifier-Free Guidance）
            noise_pred = noise_pred_uncond + guidance_scale * (noise_pred_cond - noise_pred_uncond)
            
            # 去噪（DDPM 采样器）
            alpha = 1 - t / 1000
            beta = t / 1000
            
            # 简化的去噪步骤
            latent = (latent - beta ** 0.5 * noise_pred) / alpha ** 0.5
        
        # 解码（需要 VAE）
        # image = vae.decode(latent)
        
        return latent


print("文本到图像生成器已定义")
```

---

## 总结

本文档深入探讨了多模态 AI 应用的高级技术，包括：

1. **高级图像理解**
   - 细粒度图像识别
   - 零样本和少样本学习
   - 图像分割与理解

2. **深度视频分析**
   - 动作识别（I3D、双流网络）
   - 视频对象跟踪（SiameseRPN）
   - 视频摘要生成

3. **高级语音处理**
   - 语音合成（Tacotron 2）
   - 语音增强与降噪
   - 说话人识别与验证

4. **跨模态检索优化**
   - 高效索引（HNSW）
   - 近似最近邻搜索（Faiss）

5. **内容生成高级技术**
   - 图像生成（U-Net）
   - 文本生成（GPT）
   - 跨模态生成（文本到图像）

这些技术为构建复杂的多模态 AI 应用提供了坚实的理论基础和实践指南。通过结合这些技术，可以开发出更强大、更智能的多模态 AI 系统。

---

## 参考资料

### 论文
- Prototypical Networks: Snell et al., "Prototypical Networks for Few-shot Learning", 2017
- DeepLabV3+: Chen et al., "Encoder-Decoder with Atrous Separable Convolution", 2018
- I3D: Carreira & Zisserman, "Quo Vadis, Action Recognition?", 2017
- SiameseRPN: Li et al., "High Performance Visual Tracking with Siamese Region Proposal Network", 2018
- Tacotron 2: Shen et al., "Natural TTS Synthesis by Conditioning Wavenet on MEL Spectrogram Predictions", 2018
- ECAPA-TDNN: Desplanques et al., "ECAPA-TDNN: Emphasized Channel Attention, Propagation and Aggregation in TDNN Based Speaker Verification", 2020

### 工具库
- Hugging Face Transformers: https://github.com/huggingface/transformers
- Fairseq: https://github.com/pytorch/fairseq
- ESPnet: https://github.com/espnet/espnet
- MMCV: https://github.com/open-mmlab/mmcv

---

**文档版本**: 2.0
**最后更新**: 2026-03-25
**作者**: OpenClaw 多模态 AI 研究团队

*本文档为多模态 AI 应用的高级指南，涵盖了最新的研究进展和实际实现细节。欢迎反馈和改进建议！*
