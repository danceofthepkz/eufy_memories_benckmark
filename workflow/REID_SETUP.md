# ReID 模型设置指南

## 📋 概述

系统已集成真正的 ReID（行人重识别）模型，使用 `torchreid` 库和 OSNet 模型。

## 🔧 安装依赖

```bash
# 激活虚拟环境
source venv/bin/activate

# 安装 ReID 相关依赖
pip install torch torchvision torchreid
```

## 🎯 支持的 ReID 模型

系统默认使用 `osnet_x1_0`，但支持以下模型：

- `osnet_x1_0` - OSNet x1.0（默认，平衡速度和精度）
- `osnet_ibn_x1_0` - OSNet with IBN（更好的泛化能力）
- `osnet_x0_75` - 更小的模型（更快）
- `osnet_x0_25` - 最小的模型（最快）
- `osnet_x1_5` - 更大的模型（更准确）

## 📊 特征维度

- **OSNet 原始输出**: 512 维
- **系统使用**: 2048 维（扩展到 2048 维以保持与数据库兼容）

## 🚀 使用方法

### 基本使用

```python
from workflow import CV_Pipeline

# 使用默认 ReID 模型 (osnet_x1_0)
pipeline = CV_Pipeline(
    dataset_json_path='memories_ai_benchmark/long_mem_dataset.json',
    videos_base_dir='memories_ai_benchmark/videos'
)

# 使用自定义 ReID 模型
pipeline = CV_Pipeline(
    dataset_json_path='memories_ai_benchmark/long_mem_dataset.json',
    videos_base_dir='memories_ai_benchmark/videos',
    reid_model_name='osnet_ibn_x1_0'  # 使用 IBN 版本
)
```

### 单独使用 FeatureEncoder

```python
from workflow.phase1_cv_scanning import FeatureEncoder, PersonCrop
import cv2

# 初始化编码器
encoder = FeatureEncoder(
    face_model_name='buffalo_l',
    reid_model_name='osnet_x1_0'
)

# 加载图片
img = cv2.imread('person.jpg')
crop = PersonCrop(img, (0, 0, 128, 256), 0.9)

# 提取特征
features = encoder.extract(crop)
body_vec = features['body_vec']  # 2048 维 ReID 特征
face_vec = features['face_vec']  # 512 维人脸特征（如果有）
```

## ⚙️ 模型自动下载

首次使用时，torchreid 会自动下载预训练模型到：
- `~/.torchreid/models/`

## 🔍 工作原理

1. **图像预处理**:
   - 转换为 RGB 格式
   - Resize 到 (128, 256) - ReID 标准尺寸
   - ImageNet 标准化

2. **特征提取**:
   - 使用预训练的 OSNet 模型
   - 提取 512 维特征向量

3. **维度扩展**:
   - 扩展到 2048 维（保持与数据库兼容）
   - L2 归一化

## 🐛 故障排除

### 问题 1: torchreid 未安装

**错误信息**:
```
⚠️  torchreid 未安装，将使用简化的身体特征提取
```

**解决方案**:
```bash
pip install torchreid
```

### 问题 2: CUDA 不可用

系统会自动检测并使用 CPU 或 GPU。如果 CUDA 不可用，会使用 CPU（速度较慢但功能正常）。

### 问题 3: 模型下载失败

**解决方案**:
- 检查网络连接
- 手动下载模型到 `~/.torchreid/models/`
- 或使用离线模式

### 问题 4: 内存不足

如果遇到内存问题，可以：
- 使用更小的模型：`osnet_x0_75` 或 `osnet_x0_25`
- 减少批处理大小
- 使用 CPU 模式（虽然更慢）

## 📈 性能对比

| 模型 | 参数量 | 速度 | 精度 | 推荐场景 |
|------|--------|------|------|----------|
| osnet_x0_25 | ~0.6M | 最快 | 较低 | 资源受限 |
| osnet_x0_75 | ~1.3M | 快 | 中等 | 平衡场景 |
| osnet_x1_0 | ~2.2M | 中等 | 高 | **推荐** |
| osnet_ibn_x1_0 | ~2.2M | 中等 | 高 | 跨域场景 |
| osnet_x1_5 | ~3.3M | 较慢 | 最高 | 高精度需求 |

## 💡 最佳实践

1. **首次运行**: 使用默认的 `osnet_x1_0`，平衡速度和精度
2. **侧脸/背影场景**: ReID 模型特别适合，因为不依赖人脸
3. **性能优化**: 如果有 GPU，确保 PyTorch 使用 GPU 版本
4. **特征缓存**: 系统会自动缓存身体特征到数据库，提高后续匹配速度

## 🔗 相关资源

- [torchreid 官方文档](https://github.com/KaiyangZhou/deep-person-reid)
- [OSNet 论文](https://arxiv.org/abs/1905.00953)
- [ReID 数据集](https://github.com/KaiyangZhou/deep-person-reid#datasets)

