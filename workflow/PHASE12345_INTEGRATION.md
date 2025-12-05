# Phase 1-5 完整集成文档

## 📋 概述

本文档说明如何运行 Phase 1 到 Phase 5 的完整集成流程，从视频处理到每日总结生成的端到端流程。

## 🚀 快速开始

### 运行完整集成测试

```bash
source venv/bin/activate
source setup_env.sh
python workflow/integrate_phase12345.py
```

## 📊 完整数据流

```
[视频文件]
    ⬇️ Phase 1: CV_Pipeline
[Clip_Obj 列表]
    ⬇️ Phase 2: Event_Fusion_Pipeline
[Global_Event 列表]
    ⬇️ Phase 3: LLM_Reasoning_Pipeline
[带日志的 Global_Event 列表]
    ⬇️ Phase 4: Persistence_Pipeline
[event_logs 表 + event_appearances 表]
    ⬇️ Phase 5: Daily_Summary_Pipeline
[daily_summaries 表]
```

## 🔄 各阶段说明

### Phase 1: 视觉扫描与特征提取
- **输入**: 视频文件 + JSON 元数据
- **输出**: `Clip_Obj` 列表
- **功能**: 检测人物、提取特征、身份识别

### Phase 2: 时空事件合并
- **输入**: `Clip_Obj` 列表
- **输出**: `Global_Event` 列表
- **功能**: 基于时间和身份规则合并相关 Clip

### Phase 3: LLM 语义生成
- **输入**: `Global_Event` 列表
- **输出**: 带 `summary_text` 的 `Global_Event` 列表
- **功能**: 使用 LLM 生成自然语言事件日志

### Phase 4: 结构化落库
- **输入**: 带日志的 `Global_Event` 列表
- **输出**: 数据库记录（`event_logs` 和 `event_appearances` 表）
- **功能**: 选择最佳特征、持久化到 PostgreSQL

### Phase 5: 每日总结生成
- **输入**: `event_logs` 表中的事件数据
- **输出**: `daily_summaries` 表中的每日总结
- **功能**: 使用 LLM 生成宏观的每日活动总结

## 📝 使用示例

### 完整流程

```python
from workflow import (
    CV_Pipeline,
    Event_Fusion_Pipeline,
    LLM_Reasoning_Pipeline,
    Persistence_Pipeline,
    Daily_Summary_Pipeline
)
from pathlib import Path

# Phase 1: 视频处理
cv_pipeline = CV_Pipeline(
    dataset_json_path='memories_ai_benchmark/long_mem_dataset.json',
    videos_base_dir='memories_ai_benchmark/videos',
    yolo_model='yolov8n.pt',
    face_model_name='buffalo_l',
    reid_model_name='osnet_x1_0',
    enable_tracking=True
)
clip_objs = cv_pipeline.process_all_clips(max_clips=10)

# Phase 2: 事件融合
fusion_pipeline = Event_Fusion_Pipeline(time_threshold=60)
global_events = fusion_pipeline.run(clip_objs)

# Phase 3: LLM 生成日志
llm_pipeline = LLM_Reasoning_Pipeline()
processed_events = llm_pipeline.process_events(global_events)

# Phase 4: 数据库持久化
persistence_pipeline = Persistence_Pipeline()
saved_event_ids = persistence_pipeline.save_events(processed_events)

# Phase 5: 每日总结生成
summary_pipeline = Daily_Summary_Pipeline()

# 方式1: 处理单个日期
first_event_date = processed_events[0]['start_time'].strftime('%Y-%m-%d')
summary_pipeline.run_for_date(first_event_date, force_update=True)

# 方式2: 批量处理所有日期
summary_pipeline.run_batch(force_update=False)
```

## 🔧 配置选项

### Phase 1 配置
- `max_clips`: 处理的最大 Clip 数量（测试时可设置较小值）
- `enable_tracking`: 是否启用帧内跟踪优化

### Phase 2 配置
- `time_threshold`: 时间阈值（秒），超过此值认为不属于同一事件

### Phase 3 配置
- `model_name`: LLM 模型名称（默认：'gemini-2.5-flash-lite'）
- `temperature`: LLM 温度参数

### Phase 4 配置
- `db_config`: 数据库连接配置（默认从环境变量读取）

### Phase 5 配置
- `model_name`: LLM 模型名称（默认：'gemini-2.5-flash-lite'）
- `temperature`: LLM 温度参数（默认：0.3）
- `force_update`: 是否强制更新已存在的总结

## 📊 输出结果

### 数据库表

1. **event_logs**: 存储事件主记录
   - `id`: 事件ID (UUID)
   - `start_time`: 开始时间
   - `camera_location`: 摄像头位置
   - `llm_description`: LLM 生成的日志

2. **event_appearances**: 存储人物出场快照
   - `event_id`: 关联的事件ID
   - `person_id`: 人物ID
   - `match_method`: 匹配方法（face/body/new）
   - `body_embedding`: 身体特征向量

3. **daily_summaries**: 存储每日总结
   - `summary_date`: 日期
   - `summary_text`: 每日总结文本
   - `total_events`: 当天事件总数

## ⚠️ 注意事项

1. **环境变量**: 确保已设置数据库和 Google Cloud 的环境变量
2. **数据库连接**: 确保 PostgreSQL 数据库正在运行
3. **API 配额**: LLM 调用会消耗 API 配额，注意控制调用频率
4. **幂等性**: Phase 5 默认不会重新生成已存在的总结（使用 `force_update=True` 强制更新）
5. **数据依赖**: Phase 5 需要 Phase 4 已经将事件写入数据库

## 🧪 测试

### 运行完整集成测试

```bash
python workflow/integrate_phase12345.py
```

### 单独测试各阶段

```bash
# Phase 1
python workflow/phase1_cv_scanning/test_phase1.py

# Phase 2
python workflow/phase2_event_fusion/test_phase2.py

# Phase 3
python workflow/phase3_agent_interaction/test_phase3.py

# Phase 4
python workflow/phase4_clean_store/test_phase4.py

# Phase 5
python workflow/phase5_summarize/test_phase5.py
```

## 🔍 故障排查

### 常见问题

1. **数据库连接失败**
   - 检查 PostgreSQL 是否运行
   - 验证环境变量配置

2. **LLM API 调用失败**
   - 检查 Google Cloud 凭证
   - 验证 API 配额

3. **Phase 5 没有数据**
   - 确保 Phase 4 已成功写入数据库
   - 检查日期格式是否正确

## 📚 相关文档

- [Phase 1 README](phase1_cv_scanning/README.md)
- [Phase 2 README](phase2_event_fusion/README.md)
- [Phase 3 README](phase3_agent_interaction/README.md)
- [Phase 4 README](phase4_clean_store/README.md)
- [Phase 5 README](phase5_summarize/README.md)
- [流程完整.md](../../重要的模块/流程完整.md)

