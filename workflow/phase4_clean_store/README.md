# Phase 4: 结构化落库 (Persistence)

## 📋 概述

Phase 4 负责将 Phase 3 生成的 `Global_Event` 对象持久化到 PostgreSQL 数据库。这一阶段不仅仅是执行 SQL INSERT，更是一个数据清洗与优选的过程。

## 🏗️ 模块架构

### 1. QualitySelector (质量评估与优选器)

**职责：** "策展人"。从多次检测中选出最具代表性的一张作为"定妆照"。

**核心功能：**
- 从一个人物的多次检测记录中选择最佳的一张
- 评分策略：
  - **方法优先**：正脸确认 (face) > 身体匹配 (body) > 新检测 (new)
  - **置信度优先**：Face Score 或 ReID Confidence 最高的
  - **分辨率优先**：边界框 (bbox) 面积最大的
  - **居中优先**：人物位于画面中心，未被遮挡的

**关键方法：**
- `select_best(detection_list)`: 从检测列表中选择最佳检测
- `group_by_person(global_event)`: 将事件中的所有检测按人物ID分组（支持陌生人）
- `_generate_stranger_key(person, index)`: 为陌生人生成唯一标识

### 2. VectorAdapter (向量序列化适配器)

**职责：** "格式转换器"。打通 Python NumPy 与 PostgreSQL pgvector 之间的隔阂。

**核心功能：**
- 将 `numpy.ndarray` 转换为 pgvector 格式字符串 `"[0.12, -0.5, ...]"`
- 维度校验：确保向量维度符合数据库定义（Face=512, Body=2048）
- 向量归一化（L2 归一化）

**关键方法：**
- `to_pgvector(vector, expected_dim)`: 转换为 pgvector 格式
- `to_pgvector_face(vector)`: 转换人脸向量（512维）
- `to_pgvector_body(vector)`: 转换身体向量（2048维）

### 3. TransactionManager (事务管理器)

**职责：** "安全员"。保证数据的一致性 (ACID)。

**核心功能：**
- 开启数据库事务（使用上下文管理器）
- 自动提交（成功）或回滚（异常）
- 管理数据库连接生命周期

**关键方法：**
- `begin()`: 开启事务的上下文管理器

### 4. EventDAO & AppearanceDAO (数据访问对象层)

**职责：** "操作员"。执行具体的 SQL 语句。

**EventDAO：**
- `insert_event(cursor, global_event, summary_text)`: 插入事件主表 (`event_logs`)

**AppearanceDAO：**
- `insert_appearance(cursor, event_id, person_id, match_method, body_embedding_pgvector)`: 插入单条人物出场记录
- `batch_insert_appearances(cursor, appearances)`: 批量插入人物出场记录

### 5. Persistence_Pipeline (主 Pipeline)

**职责：** 整合所有模块，实现完整的持久化流程。

**核心流程：**
1. 验证 `Global_Event` 对象
2. 开启数据库事务
3. 插入事件主表 (`event_logs`)
4. 按人物分组（包括陌生人），选择最佳检测
5. **处理陌生人**：为陌生人生成唯一标识，创建 `persons` 记录
6. 转换向量格式
7. 批量插入人物出场快照表 (`event_appearances`)
8. 提交事务

**关键方法：**
- `save_event(global_event)`: 保存单个事件
- `save_events(global_events)`: 批量保存多个事件
- `_get_or_create_stranger_person(cursor, stranger_key, detection_list, global_event)`: 为陌生人创建 `persons` 记录

## 📊 数据库表结构

### event_logs (事件主表)

```sql
CREATE TABLE event_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_filename VARCHAR(100),
    start_time TIMESTAMP NOT NULL,
    camera_location VARCHAR(50),
    llm_description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### event_appearances (人物出场快照表)

```sql
CREATE TABLE event_appearances (
    id SERIAL PRIMARY KEY,
    event_id UUID REFERENCES event_logs(id) ON DELETE CASCADE,
    person_id INTEGER REFERENCES persons(id),
    match_method VARCHAR(20),  -- 'face', 'body_reid', 'new'
    body_embedding vector(2048),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 🔄 数据流

```
Global_Event (Phase 3)
    ↓
[验证对象]
    ↓
[开启事务]
    ↓
[插入 event_logs]
    ↓
[按人物分组] (包括陌生人)
    ↓
[处理陌生人] → 创建 persons 记录
    ↓
[选择最佳检测] (QualitySelector)
    ↓
[转换向量格式] (VectorAdapter)
    ↓
[批量插入 event_appearances]
    ↓
[提交事务]
    ↓
PostgreSQL 数据库
```

## 🚀 使用方法

### 基本用法

```python
from workflow.phase4_clean_store import Persistence_Pipeline

# 初始化 Pipeline
pipeline = Persistence_Pipeline()

# 保存单个事件
event_id = pipeline.save_event(global_event)

# 批量保存
event_ids = pipeline.save_events(global_events)
```

### 完整示例

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from workflow.phase4_clean_store import Persistence_Pipeline

# 假设 global_event 来自 Phase 3
global_event = {
    'start_time': datetime(2025, 9, 1, 9, 0, 0),
    'end_time': datetime(2025, 9, 1, 9, 0, 30),
    'cameras': ['doorbell', 'outdoor_high'],
    'people': {21, 22},
    'clips': [...],
    'summary_text': '09:00，家人出现在门口...'
}

# 保存到数据库
pipeline = Persistence_Pipeline()
event_id = pipeline.save_event(global_event)

if event_id:
    print(f"✅ 事件已保存: {event_id}")
else:
    print("❌ 保存失败")
```

## 🧪 测试

运行测试脚本：

```bash
cd /Users/danceofthepkz/Desktop/Eufynew
source venv/bin/activate
source setup_env.sh
python workflow/phase4_clean_store/test_phase4.py
```

## ⚙️ 配置

数据库配置通过环境变量读取：

- `POSTGRES_HOST`: 数据库主机（默认：localhost）
- `POSTGRES_PORT`: 数据库端口（默认：5432）
- `POSTGRES_DB`: 数据库名称（默认：neweufy）
- `POSTGRES_USER`: 数据库用户（默认：postgres）
- `POSTGRES_PASSWORD`: 数据库密码

## 🔍 关键设计决策

1. **质量优选的重要性**：
   - 一个事件可能包含数百次检测，但只存储最具代表性的一张
   - 这确保了数据库中的向量质量，提高了后续检索的准确性

2. **事务保证**：
   - 使用数据库事务确保数据一致性
   - 如果任何一步失败，整个操作会回滚

3. **批量插入优化**：
   - 使用 `execute_values` 进行批量插入，提高性能

4. **向量格式转换**：
   - 在应用层完成向量格式转换，而不是在数据库层
   - 这样可以提前发现维度不匹配等问题

5. **陌生人持久化** ⭐ **新增**：
   - 确保 LLM 描述和数据库记录的一致性
   - 为每个陌生人创建 `persons` 记录，使用 `role='unknown'`
   - 基于 `body_embedding` 生成唯一标识，区分不同的陌生人
   - 如果陌生人没有 `body_embedding`，使用索引标识

6. **匹配方法标准化** ⭐ **新增**：
   - 处理 Phase 2 `IdentityRefiner` 优化的方法：
     - `refined_from_suspected` → `body_reid_refined`
     - `refined_from_stranger` → `body_reid_refined`
     - `refined_from_context` → `body_reid_refined`
   - 确保所有检测记录都有正确的 `match_method` 标记

## 📝 注意事项

1. **向量维度**：
   - 确保 `body_embedding` 是 2048 维
   - 确保 `face_embedding` 是 512 维（如果使用）

2. **人物ID**：
   - 有 `person_id` 的检测（家人、疑似家人）直接存储
   - **陌生人处理**：`person_id=None` 的陌生人会被：
     - 基于 `body_embedding` 生成唯一标识（如 `stranger_hash_xxx`）
     - 在 `persons` 表中创建新记录（`role='unknown'`）
     - 使用新创建的 `person_id` 保存到 `event_appearances`
   - 这确保了 LLM 描述和数据库记录的一致性

3. **匹配方法**：
   - `face`: 正脸确认
   - `body_reid`: 身体匹配（ReID）
   - `body_reid_refined`: 身体匹配（经过 Phase 2 身份优化）
   - `new`: 新检测（陌生人，已创建 persons 记录）

4. **错误处理**：
   - 如果向量转换失败，该人物的记录会被跳过
   - 如果事务失败，所有操作都会回滚

## 🔗 相关文档

- [流程完整.md](../../重要的模块/流程完整.md)
- [第四阶段.md](../../重要的模块/第四阶段.md)
- [数据库初始化脚本](../../database/init_database.sql)

