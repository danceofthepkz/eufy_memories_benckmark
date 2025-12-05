# Phase 5: Daily Summary (每日总结)

## 📋 概述

Phase 5 是"记忆压缩"阶段，从数据库中查询每日事件，使用 LLM 生成宏观的每日活动总结，并存储到 `daily_summaries` 表中。

## 🏗️ 架构设计

Phase 5 包含 4 个核心模块：

### 1. QueryEngine (时间切片查询器)
- **职责**：从数据库中精准捞取特定日期的数据
- **功能**：
  - `fetch_events(target_date)`: 查询指定日期的所有事件
  - `get_distinct_dates()`: 获取数据库中有事件的所有日期

### 2. NarrativeAggregator (叙事流聚合器)
- **职责**：将事件列表转化为 LLM 易读的纯文本时间轴
- **功能**：
  - `format_timeline(events)`: 格式化时间线文本
  - `estimate_tokens(text)`: 估算 token 数量
  - `check_token_limit(text)`: 检查 token 限制

### 3. InsightEngine (高维洞察引擎)
- **职责**：使用 LLM 生成每日总结
- **功能**：
  - `analyze(timeline_text, target_date)`: 分析时间线并生成总结
  - 使用专门的"分析型 Prompt"，要求归纳演绎而非简单复述

### 4. ArchivePersister (归档持久化器)
- **职责**：将总结写入数据库，支持幂等写入
- **功能**：
  - `save(summary_date, summary_text, total_events)`: 保存总结（UPSERT）
  - `get_summary(summary_date)`: 查询指定日期的总结

## 🚀 使用方法

### 基本用法

```python
from workflow import Daily_Summary_Pipeline

# 初始化 Pipeline
pipeline = Daily_Summary_Pipeline()

# 处理单个日期
record_id = pipeline.run_for_date('2025-09-01', force_update=False)

# 批量处理所有日期
results = pipeline.run_batch(force_update=False)
```

### 高级用法

```python
from workflow.phase5_summarize import (
    QueryEngine,
    NarrativeAggregator,
    InsightEngine,
    ArchivePersister
)

# 单独使用各个模块
query_engine = QueryEngine()
events = query_engine.fetch_events('2025-09-01')

aggregator = NarrativeAggregator()
timeline_text = aggregator.format_timeline(events)

insight_engine = InsightEngine()
summary = insight_engine.analyze(timeline_text, '2025-09-01')

persister = ArchivePersister()
record_id = persister.save('2025-09-01', summary, len(events))
```

## 📊 数据流

```
[event_logs 表]
    ⬇️ QueryEngine.fetch_events()
[事件列表 (List[Dict])]
    ⬇️ NarrativeAggregator.format_timeline()
[时间线文本 (str)]
    ⬇️ InsightEngine.analyze()
[每日总结 (str)]
    ⬇️ ArchivePersister.save()
[daily_summaries 表]
```

## 🔧 配置选项

### Daily_Summary_Pipeline 参数

- `db_config`: 数据库连接配置（可选，默认从环境变量读取）
- `model_name`: LLM 模型名称（默认：'gemini-2.5-flash-lite'）
- `temperature`: LLM 温度参数（默认：0.3）
- `max_output_tokens`: LLM 最大输出 token 数（默认：512）

### run_for_date 参数

- `target_date`: 目标日期，格式为 'YYYY-MM-DD'
- `force_update`: 如果为 True，即使已存在总结也会重新生成

### run_batch 参数

- `date_list`: 日期列表（可选，如果为 None 则处理所有日期）
- `force_update`: 如果为 True，即使已存在总结也会重新生成

## 📝 Prompt 设计

### System Prompt

```
你是一个专业的家庭安防分析师。你的任务是根据提供的事件日志，生成每日活动总结。

要求：
1. **规律分析**：识别家人的出门和回家时间
2. **安全提醒**：明确提及任何与陌生人（未知人员）的互动
3. **异常标记**：突出敏感时段的活动（如 00:00 - 05:00）
4. **简洁性**：不要列举每个事件，而是将相似事件归类
5. **客观性**：基于提供的时间线信息，不要推断或添加未明确提到的事件

输出格式（中文）：
- [家人动态]: ...
- [访客/陌生人]: ... (如果没有，说"无")
- [异常关注]: ... (如果没有，说"无")
```

## 🗄️ 数据库表结构

### daily_summaries 表

```sql
CREATE TABLE daily_summaries (
    id SERIAL PRIMARY KEY,
    summary_date DATE UNIQUE NOT NULL,  -- 日期: 2025-09-01
    summary_text TEXT,                  -- 全天总结
    total_events INTEGER,               -- 当天事件总数
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**幂等性保证**：使用 `INSERT ... ON CONFLICT DO UPDATE` 确保同一天只有一条最新的总结。

## 🧪 测试

运行测试脚本：

```bash
source venv/bin/activate
source setup_env.sh
python workflow/phase5_summarize/test_phase5.py
```

## ⚠️ 注意事项

1. **依赖 Phase 4**：Phase 5 需要 Phase 4 已经将事件写入数据库
2. **幂等性**：默认情况下，如果某日期已有总结，不会重新生成（使用 `force_update=True` 强制更新）
3. **Token 限制**：如果某天事件过多，时间线文本可能很长，系统会检查 token 限制并发出警告
4. **LLM 调用**：如果 LLM 调用失败，会使用兜底总结

## 📈 与 Phase 4 的衔接

Phase 5 从 Phase 4 写入的 `event_logs` 表中读取数据：

1. Phase 4 将 `Global_Event` 写入 `event_logs` 表
2. Phase 5 从 `event_logs` 表查询指定日期的事件
3. Phase 5 生成总结并写入 `daily_summaries` 表

## 🔄 完整流程示例

```python
# 1. Phase 1-4: 处理视频并写入数据库
from workflow import CV_Pipeline, Event_Fusion_Pipeline, LLM_Reasoning_Pipeline, Persistence_Pipeline

cv_pipeline = CV_Pipeline(...)
clip_objs = cv_pipeline.process_all_clips(max_clips=10)

fusion_pipeline = Event_Fusion_Pipeline()
global_events = fusion_pipeline.run(clip_objs)

llm_pipeline = LLM_Reasoning_Pipeline()
processed_events = llm_pipeline.process_events(global_events)

persistence_pipeline = Persistence_Pipeline()
persistence_pipeline.save_events(processed_events)

# 2. Phase 5: 生成每日总结
from workflow import Daily_Summary_Pipeline

summary_pipeline = Daily_Summary_Pipeline()
summary_pipeline.run_batch()  # 处理所有日期
```

## 📚 相关文档

- [流程完整.md](../../重要的模块/流程完整.md)
- [第五阶段.md](../../重要的模块/第五阶段.md)

