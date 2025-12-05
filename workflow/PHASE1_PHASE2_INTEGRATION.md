# Phase 1 + Phase 2 集成指南

## 🔗 连接方式

第一阶段（Phase 1）的输出是 `Clip_Obj` 列表，直接作为第二阶段（Phase 2）的输入。

## 📊 数据流

```
Phase 1: CV_Pipeline
  ↓
输出: List[Clip_Obj]
  ↓
Phase 2: Event_Fusion_Pipeline
  ↓
输出: List[Global_Event]
```

## 🚀 使用方法

### 方法1：使用集成脚本（推荐）

```bash
python workflow/integrate_phase1_phase2.py
```

这会自动运行 Phase 1 → Phase 2 的完整流程。

### 方法2：手动连接

```python
from workflow import CV_Pipeline, Event_Fusion_Pipeline

# ========== Phase 1 ==========
cv_pipeline = CV_Pipeline(
    dataset_json_path='memories_ai_benchmark/long_mem_dataset.json',
    videos_base_dir='memories_ai_benchmark/videos'
)

# 处理视频，生成 Clip_Obj 列表
clip_objs = cv_pipeline.process_all_clips(max_clips=10)

# ========== Phase 2 ==========
fusion_pipeline = Event_Fusion_Pipeline(time_threshold=60)

# 将 Phase 1 的输出传递给 Phase 2
global_events = fusion_pipeline.run(clip_objs)

# ========== 处理结果 ==========
for event in global_events:
    print(f"事件: {event['start_time']} ~ {event['end_time']}")
    print(f"人物: {event['people']}")
    print(f"Prompt: {event['prompt_text']}")
```

## 📋 数据格式

### Phase 1 输出：Clip_Obj

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
                'bbox': (100, 100, 200, 300),
                'confidence': 0.9,
                'frame_idx': 0
            }
        ],
        [  # 第2帧
            ...
        ]
    ]
}
```

### Phase 2 输出：Global_Event

```python
{
    'start_time': datetime(2025, 9, 1, 9, 0, 0),
    'end_time': datetime(2025, 9, 1, 9, 0, 30),
    'duration': 30.0,
    'cameras': ['doorbell', 'indoor_living'],
    'people': {1, 2},
    'people_info': {
        1: {
            'person_id': 1,
            'role': 'family',
            'method': 'face',
            'first_seen': datetime(...),
            'last_seen': datetime(...),
            'cameras': ['doorbell', 'indoor_living']
        }
    },
    'clips': [...],  # 原始 Clip_Obj 列表
    'keyframes': {
        1: {
            'bbox': (100, 100, 200, 300),
            'confidence': 0.9,
            'method': 'face',
            'clip_time': datetime(...),
            'cam': 'doorbell'
        }
    },
    'prompt_text': 'Plaintext时间线：\n- 09:00:00 [doorbell]: 家人(Person_1) 出现\n...',
    'clip_count': 3
}
```

## 💡 关键点

### 1. 数据传递

Phase 1 的输出（`clip_objs`）直接作为 Phase 2 的输入：

```python
clip_objs = cv_pipeline.process_all_clips(...)  # Phase 1
global_events = fusion_pipeline.run(clip_objs)  # Phase 2
```

### 2. 数据格式兼容

Phase 1 输出的 `Clip_Obj` 格式完全符合 Phase 2 的输入要求，无需转换。

### 3. 批量处理

可以一次性处理多个视频：

```python
# Phase 1: 处理所有视频
clip_objs = cv_pipeline.process_all_clips()  # 处理全部665个视频

# Phase 2: 一次性融合所有事件
global_events = fusion_pipeline.run(clip_objs)
```

### 4. 增量处理

也可以分批处理：

```python
# 分批处理
for batch in range(0, total_videos, 100):
    clip_objs = cv_pipeline.process_all_clips(max_clips=100, start_idx=batch)
    global_events = fusion_pipeline.run(clip_objs)
    # 保存或处理 global_events
```

## 🔍 完整示例

```python
#!/usr/bin/env python3
"""完整的 Phase 1 → Phase 2 流程"""

from workflow import CV_Pipeline, Event_Fusion_Pipeline
from pathlib import Path

# 1. 初始化 Phase 1
cv_pipeline = CV_Pipeline(
    dataset_json_path='memories_ai_benchmark/long_mem_dataset.json',
    videos_base_dir='memories_ai_benchmark/videos',
    enable_tracking=True  # 启用跟踪优化
)

# 2. 运行 Phase 1
print("运行 Phase 1...")
clip_objs = cv_pipeline.process_all_clips(max_clips=10)
print(f"✅ Phase 1 完成: {len(clip_objs)} 个 Clip_Obj")

# 3. 初始化 Phase 2
fusion_pipeline = Event_Fusion_Pipeline(time_threshold=60)

# 4. 运行 Phase 2
print("\n运行 Phase 2...")
global_events = fusion_pipeline.run(clip_objs)
print(f"✅ Phase 2 完成: {len(global_events)} 个全局事件")

# 5. 处理结果
for idx, event in enumerate(global_events, 1):
    print(f"\n事件 #{idx}:")
    print(f"  时间: {event['start_time']} ~ {event['end_time']}")
    print(f"  人物: {list(event['people'])}")
    print(f"  Clip 数: {event['clip_count']}")
    print(f"  Prompt: {event['prompt_text'][:100]}...")
```

## 🐛 常见问题

### Q: Phase 1 没有输出怎么办？

A: 检查：
1. 视频文件是否存在
2. 数据库是否已初始化（Phase 0）
3. 身体特征缓存是否已创建

### Q: Phase 2 没有生成事件怎么办？

A: 检查：
1. Clip_Obj 列表是否为空
2. 时间阈值是否设置合理（默认60秒）
3. Clip 之间是否有时间间隔

### Q: 如何调整融合策略？

A: 修改 `Event_Fusion_Pipeline` 的参数：

```python
fusion_pipeline = Event_Fusion_Pipeline(
    time_threshold=120  # 增加到120秒
)
```

## 📚 相关文档

- `workflow/integrate_phase1_phase2.py` - 集成脚本
- `workflow/phase1_cv_scanning/README.md` - Phase 1 文档
- `workflow/phase2_event_fusion/README.md` - Phase 2 文档

