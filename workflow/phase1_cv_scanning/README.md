# Workflow - 第一阶段：视觉扫描与特征提取

## 📋 概述

本模块实现了第一阶段（Phase 1: CV Scanning）的完整流程，按照模块化设计拆分为6个核心模块。

## 🏗️ 模块结构

### 模块 1: DataLoader (数据加载与对齐)
- **文件**: `data_loader.py`
- **职责**: 读取 JSON 元数据，解析时间，验证视频路径
- **类**: `DataLoader`

### 模块 2: FrameSampler (视频流采样)
- **文件**: `frame_sampler.py`
- **职责**: 控制处理频率，每秒提取1帧
- **类**: `FrameSampler`

### 模块 3: YoloDetector (多目标检测)
- **文件**: `yolo_detector.py`
- **职责**: 使用 YOLOv8 检测人物，裁剪 ROI
- **类**: `YoloDetector`, `PersonCrop`

### 模块 4: FeatureEncoder (双模态特征编码)
- **文件**: `feature_encoder.py`
- **职责**: 提取人脸特征（512维）和身体特征（2048维）
- **类**: `FeatureEncoder`

### 模块 5: IdentityArbiter (身份仲裁与缓存管理)
- **文件**: `identity_arbiter.py`
- **职责**: 决定人物身份，更新数据库缓存
- **类**: `IdentityArbiter`

### 模块 6: ResultBuffer (结果暂存)
- **文件**: `result_buffer.py`
- **职责**: 打包结果，暂存内存
- **类**: `ResultBuffer`

### 主 Pipeline: CV_Pipeline
- **文件**: `cv_pipeline.py`
- **职责**: 整合所有模块，实现完整流程
- **类**: `CV_Pipeline`

## 🚀 使用方法

### 基本使用

```python
from workflow import CV_Pipeline

# 初始化 Pipeline
pipeline = CV_Pipeline(
    dataset_json_path='memories_ai_benchmark/long_mem_dataset.json',
    videos_base_dir='memories_ai_benchmark/videos'
)

# 处理单个视频
json_record = {
    'video_path': '1.mp4',
    'camera': 'doorbell',
    'time': '2025-09-01 09:00:00'
}
clip_obj = pipeline.process_one_clip(json_record)

# 处理所有视频（测试：只处理前10个）
clip_objs = pipeline.process_all_clips(max_clips=10)
```

### 输出格式

`Clip_Obj` 结构：

```python
{
    'time': datetime(2025, 9, 1, 9, 0, 0),
    'cam': 'doorbell',
    'people_detected': [
        [  # 第1帧
            {
                'person_id': 1,
                'role': 'family',
                'method': 'face',
                'bbox': (100, 200, 300, 500),
                'confidence': 0.95,
                'frame_idx': 0
            },
            {
                'person_id': None,
                'role': 'stranger',
                'method': 'new',
                'bbox': (400, 300, 600, 700),
                'confidence': 0.87,
                'frame_idx': 0
            }
        ],
        [  # 第2帧
            ...
        ],
        ...
    ]
}
```

## 🔧 配置

### 环境变量

确保已设置数据库连接信息（通过 `setup_env.sh`）：

```bash
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=neweufy
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=eufy123
```

### 数据库要求

- PostgreSQL 15+
- pgvector 扩展已启用
- 表结构已初始化（运行 `database/init_database.py`）

## 📝 注意事项

1. **不写入 Event Log**: 第一阶段只暂存结果，不写入数据库的 `event_logs` 表
2. **缓存更新**: 模块5会自动更新 `persons` 表的 `current_body_embedding` 缓存
3. **性能优化**: 每秒只处理1帧，大幅降低计算量
4. **模块化设计**: 每个模块可独立测试和调试

## 🔄 数据流向

```
JSON 记录
  ↓ [DataLoader]
视频路径 + 时间戳
  ↓ [FrameSampler]
原始帧数组
  ↓ [YoloDetector]
人物裁剪对象列表
  ↓ [FeatureEncoder]
特征向量包 (face + body)
  ↓ [IdentityArbiter]
身份信息 (person_id, role, method)
  ↓ [ResultBuffer]
Clip_Obj (准备传给第二阶段)
```

## 🧪 测试

创建测试脚本：

```python
# test_workflow_phase1.py
from workflow import CV_Pipeline
import logging

logging.basicConfig(level=logging.INFO)

pipeline = CV_Pipeline(
    dataset_json_path='memories_ai_benchmark/long_mem_dataset.json',
    videos_base_dir='memories_ai_benchmark/videos'
)

# 测试处理前3个视频
clip_objs = pipeline.process_all_clips(max_clips=3)

for clip_obj in clip_objs:
    print(f"\n📹 {clip_obj['cam']} @ {clip_obj['time']}")
    print(f"   帧数: {len(clip_obj['people_detected'])}")
    print(f"   检测次数: {sum(len(p) for p in clip_obj['people_detected'])}")
```

