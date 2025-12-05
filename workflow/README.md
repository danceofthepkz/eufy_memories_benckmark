# Workflow 模块

## 📋 概述

本模块实现了完整的视频处理工作流，包含多个阶段：

- **Phase 0**: 系统初始化 (Initialization)
- **Phase 1**: 视觉扫描与特征提取 (CV Scanning)

## 🏗️ 模块结构

```
workflow/
├── __init__.py                    # 模块导出
├── phase0_initialization.py       # Phase 0: 系统初始化
├── test_phase0.py                 # Phase 0 测试脚本
├── clear_database.py              # 清空数据库脚本（测试前使用）
├── phase1_cv_scanning/            # Phase 1: 视觉扫描与特征提取
│   ├── __init__.py
│   ├── data_loader.py             # 模块1: 数据加载与对齐
│   ├── frame_sampler.py           # 模块2: 视频流采样
│   ├── yolo_detector.py           # 模块3: 多目标检测
│   ├── feature_encoder.py         # 模块4: 双模态特征编码
│   ├── identity_arbiter.py        # 模块5: 身份仲裁与缓存管理
│   ├── result_buffer.py           # 模块6: 结果暂存
│   ├── cv_pipeline.py             # 主Pipeline类
│   ├── test_phase1.py             # Phase 1 测试脚本
│   ├── README.md                  # Phase 1 文档
│   └── IMPLEMENTATION_SUMMARY.md  # Phase 1 实现总结
└── README.md                      # 本文件
```

## 🧹 清空数据库

在测试前，可以使用 `clear_database.py` 清空所有数据（保留表结构）：

```bash
# 交互式确认
python workflow/clear_database.py

# 跳过确认（用于自动化测试）
python workflow/clear_database.py --yes
```

**注意**: 此脚本会清空以下表的所有数据：
- `event_appearances`
- `person_faces`
- `daily_summaries`
- `event_logs`
- `persons`

但会保留表结构，可以重新初始化。

## 🎬 Phase 0: 系统初始化

### 功能

在处理任何监控视频之前，系统必须先建立"认知基准"：

1. **读取底库 (Load Library)**
   - 扫描 `memories_ai_benchmark/lib/` 文件夹
   - 使用 ArcFace 提取每张家人照片的特征向量 (512维)

2. **建立身份注册表 (Registry)**
   - 在 PostgreSQL `persons` 表中创建记录：`role='owner'`
   - 在 `person_faces` 表中存入向量

### 使用方法

```python
from workflow import Phase0Initialization

# 初始化
phase0 = Phase0Initialization(face_model_name='buffalo_l')

# 执行初始化
lib_path = 'memories_ai_benchmark/lib'
success = phase0.run(lib_path)
```

### 测试

```bash
cd /Users/danceofthepkz/Desktop/Eufynew
source venv/bin/activate
source setup_env.sh
python workflow/test_phase0.py
```

## 🔄 Phase 1: 视觉扫描与特征提取

### 功能

系统遍历视频，提取元数据用于后续合并：

- 数据加载与对齐
- 视频流采样（每秒1帧）
- 多目标检测（YOLOv8）
- 双模态特征编码（人脸+身体）
- 身份仲裁与缓存管理
- 结果暂存（不写入数据库）

### 使用方法

```python
from workflow import CV_Pipeline

# 初始化 Pipeline
pipeline = CV_Pipeline(
    dataset_json_path='memories_ai_benchmark/long_mem_dataset.json',
    videos_base_dir='memories_ai_benchmark/videos'
)

# 处理单个视频
clip_obj = pipeline.process_one_clip(json_record)

# 处理所有视频
clip_objs = pipeline.process_all_clips(max_clips=10)
```

### 测试

```bash
python workflow/phase1_cv_scanning/test_phase1.py
```

## 🔧 配置要求

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

## 📊 工作流程

```
清空数据库 (可选)
  ↓
Phase 0: 系统初始化
  ↓
  加载家人底库 → 提取特征 → 注册到数据库
  ↓
Phase 1: 视觉扫描与特征提取
  ↓
  处理视频 → 检测人物 → 识别身份 → 暂存结果
  ↓
Phase 2: 时空事件合并 (待实现)
  ↓
Phase 3: 宏观语义生成 (待实现)
  ↓
...
```

## 🧪 完整测试流程

### 单阶段测试

```bash
# 1. 激活环境
source venv/bin/activate
source setup_env.sh

# 2. 清空数据库（可选）
python workflow/clear_database.py

# 3. 运行 Phase 0（加载家人人脸底库）
python workflow/test_phase0.py

# 4. 创建初始身体特征缓存（重要！）
# 从第一个视频提取人物背影，作为家人的初始身体特征缓存
python workflow/create_initial_body_cache.py

# 5. 运行 Phase 1（测试身体特征匹配）
python workflow/phase1_cv_scanning/test_phase1.py

# 6. 运行 Phase 2（测试事件融合）
python workflow/phase2_event_fusion/test_phase2.py
```

### 集成测试（Phase 1 + Phase 2）

```bash
# 运行完整的 Phase 1 → Phase 2 流程
python workflow/integrate_phase1_phase2.py
```

这会：
1. 运行 Phase 1 处理视频，生成 Clip_Obj 列表
2. 自动将 Clip_Obj 传递给 Phase 2
3. 生成全局事件（Global Events）
4. 显示完整的统计信息

### 为什么需要步骤 4？

如果视频中的人物都是侧脸/背影，系统无法通过人脸识别。但可以通过身体特征（ReID）匹配：
- **步骤 4** 从第一个视频提取人物背影特征
- 将这些特征作为家人的初始 `current_body_embedding` 缓存
- **步骤 5** 中，后续视频的人物背影可以匹配到这些缓存

## 📚 相关文档

- `重要的模块/流程完整.md` - 完整流程说明
- `重要的模块/第一阶段.md` - Phase 1 详细设计
- `workflow/phase1_cv_scanning/README.md` - Phase 1 使用文档
