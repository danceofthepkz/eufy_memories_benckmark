# Phase 2: 时空事件合并 (Event Fusion)

## 📋 概述

第二阶段将第一阶段的 `Clip_Obj` 列表合并为全局事件（Global Events），实现时空事件的智能聚合。

## 🎯 核心功能

- **时间流预处理**：排序和验证 Clip_Obj
- **事件融合**：基于时间和身份规则合并相关 Clip
- **事件聚合**：打包成完整的 Global_Event 对象
- **Prompt 生成**：为 LLM 生成自然语言上下文

## 📁 模块结构

```
phase2_event_fusion/
├── __init__.py              # 模块导出
├── stream_sorter.py         # 模块1: 时间流预处理
├── fusion_policy.py         # 模块2: 融合策略引擎
├── session_manager.py       # 模块3: 滑动窗口会话管理器
├── event_aggregator.py      # 模块4: 全局事件聚合器
├── context_builder.py       # 模块5: 多视角上下文构建器
├── event_fusion_pipeline.py # 主 Pipeline
├── test_phase2.py           # 测试脚本
└── README.md                # 本文档
```

## 🔄 工作流程

```
第一阶段输出 (Clip_Obj 列表)
  ↓
[模块1] 时间流预处理（排序、验证）
  ↓
[模块2-3] 事件分组（融合策略 + 会话管理）
  ↓
[模块4] 事件聚合（打包成 Global_Event）
  ↓
[模块5] Prompt 生成（为 LLM 准备上下文）
  ↓
输出: Global_Event 列表
```

## 📊 数据格式

### 输入：Clip_Obj

```python
{
    'time': datetime,
    'cam': str,
    'people_detected': [
        [  # 第1帧
            {'person_id': 1, 'role': 'family', 'method': 'face', ...},
            {'person_id': None, 'role': 'stranger', 'method': 'new', ...}
        ],
        [  # 第2帧
            ...
        ]
    ]
}
```

### 输出：Global_Event

```python
{
    'start_time': datetime,
    'end_time': datetime,
    'duration': float,  # 秒
    'cameras': List[str],
    'people': Set[int],
    'people_info': Dict[int, Dict],
    'clips': List[Dict],  # 原始 Clip 列表
    'keyframes': Dict[int, Dict],  # 每个人物的代表性特征
    'prompt_text': str,  # LLM Prompt
    'clip_count': int
}
```

## 🚀 使用方法

### 基本使用

```python
from workflow.phase2_event_fusion import Event_Fusion_Pipeline

# 初始化 Pipeline
pipeline = Event_Fusion_Pipeline(time_threshold=60)

# 运行事件融合
global_events = pipeline.run(clip_objs)

# 处理结果
for event in global_events:
    print(f"事件: {event['start_time']} ~ {event['end_time']}")
    print(f"人物: {event['people']}")
    print(f"Prompt: {event['prompt_text']}")
```

### 与第一阶段集成

```python
from workflow import CV_Pipeline, Event_Fusion_Pipeline

# 第一阶段：处理视频
cv_pipeline = CV_Pipeline(...)
clip_objs = cv_pipeline.process_all_clips(max_clips=10)

# 第二阶段：事件融合
fusion_pipeline = Event_Fusion_Pipeline(time_threshold=60)
global_events = fusion_pipeline.run(clip_objs)
```

## ⚙️ 配置参数

### FusionPolicy 参数

- `time_threshold`: 时间阈值（秒），默认 60
  - 超过此值认为不属于同一事件

### 融合规则

1. **时间规则**：`Current.StartTime - Last.EndTime < THRESHOLD`
2. **身份规则**：
   - 有共同的人物 → 合并
   - 都是陌生人且时间极短（< 10秒）→ 合并
   - 家人和陌生人交互（时间差 < 5秒）→ 合并

## 🧪 测试

运行测试脚本：

```bash
python workflow/phase2_event_fusion/test_phase2.py
```

测试会：
1. 创建模拟的 Clip_Obj 数据
2. 运行事件融合流程
3. 输出生成的全局事件

## 📈 示例输出

```
✅ 事件融合完成: 3 个全局事件

📦 全局事件 #1:
   开始时间: 2025-09-01 09:00:00
   结束时间: 2025-09-01 09:00:30
   持续时间: 30 秒
   摄像头: doorbell, indoor_living, outdoor_high
   人物数量: 1
   人物ID: [1]
   Clip 数量: 3

   Prompt 文本:
   Plaintext时间线：
   - 09:00:00 [outdoor_high]: 家人(Person_1) 出现
   - 09:00:15 [doorbell]: 家人(Person_1) 出现
   - 09:00:30 [indoor_living]: 家人(Person_1) 出现
   提示: 人物从室外移动到室内
   任务：生成一条连贯的中文日志，描述这个事件的完整过程。
```

## 🔗 相关文档

- `重要的模块/第二阶段.md` - 设计文档
- `重要的模块/流程完整.md` - 完整流程说明
- `workflow/README.md` - Workflow 总览

## 💡 设计亮点

1. **模块化设计**：5个独立模块，易于维护和扩展
2. **策略可配置**：融合策略独立封装，易于调整
3. **状态管理**：会话管理器维护事件上下文
4. **智能聚合**：自动选择最佳 Keyframe
5. **LLM 就绪**：自动生成 Prompt 文本

## 🎯 下一步

- [ ] 集成到完整流程（Phase 1 → Phase 2 → Phase 3）
- [ ] 添加数据库持久化（Phase 4）
- [ ] 优化融合策略（空间逻辑、人物逻辑）
- [ ] 性能优化（大批量数据处理）

