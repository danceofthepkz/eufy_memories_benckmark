# Phase 6: User Retrieval & RAG (用户检索与 RAG)

## 📋 概述

Phase 6 是用户交互阶段，实现从自然语言问题到数据库检索再到自然语言回答的完整流程。用户可以通过自然语言查询历史事件、人物活动、衣着信息等。

## 🏗️ 架构设计

Phase 6 包含 4 个核心模块：

### 1. QueryParser (语义查询解析器)
- **职责**：将用户的自然语言问题转化为结构化的 SQL 查询条件
- **功能**：
  - 实体识别（NER）：提取人物、时间、动作关键词
  - 意图识别：识别用户意图（查询衣着、时间、位置、总结等）
  - 查询类型判断：判断是查询详细事件还是每日总结

### 2. RetrievalEngine (混合检索引擎)
- **职责**：执行 SQL 逻辑，联合多张表查找证据
- **功能**：
  - 策略路由：根据查询类型选择查询 `daily_summaries` 或 `event_logs + event_appearances`
  - SQL 构建与执行：构建并执行 JOIN 查询
  - 结果格式化：将数据库记录格式化为结构化数据

### 3. EvidenceMaterializer (证据实物化模块)
- **职责**：找到对应的图片，将数据库记录转化为可视化的证据
- **功能**：
  - 路径回溯：通过 `video_filename` 找到视频文件
  - 抓拍提取：从视频中提取关键帧
  - URL 生成：生成前端可访问的图片 URL

### 4. RAGSynthesisEngine (RAG 合成引擎)
- **职责**：结合用户问题和检索到的证据，生成最终回答
- **功能**：
  - Prompt 组装：构建包含上下文和问题的 Prompt
  - 回答生成：使用 LLM 生成人性化的回答
  - 结果格式化：返回包含文本和图片的回答

## 🚀 使用方法

### 基本用法

```python
from workflow import User_Retrieval_Pipeline
from pathlib import Path

# 初始化 Pipeline
pipeline = User_Retrieval_Pipeline(
    videos_base_dir='memories_ai_benchmark/videos'
)

# 回答用户问题
result = pipeline.answer("9月1日那天，爸爸回家的时候穿什么衣服？")

print(result['answer'])
print(f"证据数量: {result['evidence_count']}")
print(f"图片: {result['images']}")
```

### 高级用法

```python
from workflow.phase6_usr_retrieval import (
    QueryParser,
    RetrievalEngine,
    EvidenceMaterializer,
    RAGSynthesisEngine
)

# 单独使用各个模块
parser = QueryParser()
query_obj = parser.parse("9月1日爸爸回家穿什么？")

engine = RetrievalEngine()
records = engine.retrieve(query_obj)

materializer = EvidenceMaterializer(videos_base_dir='...')
materialized = materializer.materialize(records)

synthesis = RAGSynthesisEngine()
answer = synthesis.synthesize("9月1日爸爸回家穿什么？", materialized, query_obj)
```

## 📊 数据流

```
[用户自然语言问题]
    ⬇️ QueryParser.parse()
[查询对象 (Query_Object)]
    ⬇️ RetrievalEngine.retrieve()
[检索结果 (Retrieved_Records)]
    ⬇️ EvidenceMaterializer.materialize()
[实物化证据 (Materialized_Records)]
    ⬇️ RAGSynthesisEngine.synthesize()
[最终回答 (Answer)]
```

## 🔧 配置选项

### User_Retrieval_Pipeline 参数

- `db_config`: 数据库连接配置（可选，默认从环境变量读取）
- `videos_base_dir`: 视频文件基础目录（用于提取快照）
- `snapshots_dir`: 快照保存目录（默认：`/tmp/eufy_snapshots`）
- `model_name`: LLM 模型名称（默认：'gemini-2.5-flash-lite'）
- `temperature`: LLM 温度参数（默认：0.3）
- `max_output_tokens`: LLM 最大输出 token 数（默认：512）

## 📝 支持的查询类型

### 1. 详细事件查询
- **示例**："9月1日爸爸回家穿什么衣服？"
- **查询表**：`event_logs` + `event_appearances`
- **返回**：事件描述 + 人物出场信息 + 图片

### 2. 每日总结查询
- **示例**："9月1日有什么活动？"
- **查询表**：`daily_summaries`
- **返回**：每日总结文本

### 3. 时间范围查询
- **示例**："9月1日到9月5日有什么事件？"
- **支持格式**：
  - "9月1日" → `2025-09-01`
  - "今天"、"昨天"、"前天"
  - "2025-09-01"

### 4. 人物查询
- **示例**："爸爸什么时候回家？"
- **支持格式**：
  - "爸爸"、"妈妈"、"家人"
  - "Person_21"、"Person_22"

## 🧪 测试

运行测试脚本：

```bash
source venv/bin/activate
source setup_env.sh
python workflow/phase6_usr_retrieval/test_phase6.py
```

## ⚠️ 注意事项

1. **依赖 Phase 4**：Phase 6 需要 Phase 4 已经将事件写入数据库
2. **视频文件路径**：需要提供正确的 `videos_base_dir` 才能提取图片
3. **人物名称映射**：当前实现使用简单的关键词匹配，可能需要根据实际数据库中的 `persons.name` 字段调整
4. **图片提取**：如果视频文件不存在或无法打开，会跳过图片提取但继续返回文本回答

## 🔍 查询解析示例

### 输入
```
"9月1日那天，爸爸回家的时候穿什么衣服？"
```

### 解析结果
```python
{
    'person_id': 1,  # 假设数据库中爸爸的ID是1
    'person_name': '爸爸',
    'date': '2025-09-01',
    'keyword': '回家',
    'intent': 'describe_appearance',
    'query_type': 'detail'
}
```

### SQL 查询（简化）
```sql
SELECT el.*, ea.*, p.name
FROM event_logs el
JOIN event_appearances ea ON el.id = ea.event_id
LEFT JOIN persons p ON ea.person_id = p.id
WHERE DATE(el.start_time) = '2025-09-01'
  AND ea.person_id = 1
  AND el.llm_description ILIKE '%回家%'
ORDER BY el.start_time DESC
LIMIT 50
```

## 📚 相关文档

- [流程完整.md](../../重要的模块/流程完整.md)
- [第六阶段.md](../../重要的模块/第六阶段.md)

