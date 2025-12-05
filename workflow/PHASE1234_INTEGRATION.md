# Phase 1-4 完整集成文档

## 📋 概述

`integrate_phase1234.py` 是一个完整的端到端集成脚本，展示了从视频处理到数据库持久化的完整流程。

## 🔄 数据流

```
视频文件
    ↓
Phase 1: 视觉扫描与特征提取
    ↓
Clip_Obj (视频片段对象)
    ↓
Phase 2: 时空事件合并
    ↓
Global_Event (全局事件对象)
    ↓
Phase 3: LLM 语义生成
    ↓
Global_Event + summary_text (带自然语言日志的事件)
    ↓
Phase 4: 结构化落库
    ↓
PostgreSQL 数据库
```

## 🚀 使用方法

### 基本运行

```bash
cd /Users/danceofthepkz/Desktop/Eufynew
source venv/bin/activate
source setup_env.sh
python workflow/integrate_phase1234.py
```

### 运行要求

1. **环境变量**：
   - PostgreSQL 连接信息（`POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`）
   - Google Cloud 凭证（`GOOGLE_APPLICATION_CREDENTIALS`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`）

2. **数据文件**：
   - `memories_ai_benchmark/long_mem_dataset.json` - 数据集元数据
   - `memories_ai_benchmark/videos/` - 视频文件目录

3. **数据库**：
   - PostgreSQL 数据库已初始化（运行过 `database/init_database.py`）
   - pgvector 扩展已启用

## 📊 输出说明

### Phase 1 输出

- **Clip_Obj 数量**：处理的视频片段数量
- **总帧数**：所有视频片段的总帧数
- **总检测次数**：检测到人物的总次数

### Phase 2 输出

- **全局事件数量**：合并后的事件数量
- **总 Clip 数**：参与事件融合的 Clip 总数
- **平均每个事件 Clip 数**：每个事件平均包含的 Clip 数量
- **总时间跨度**：所有事件的总持续时间（秒）

### Phase 3 输出

- **处理的事件数量**：成功生成日志的事件数量
- **有效日志数量**：通过验证的日志数量
- **每个事件的日志文本**：LLM 生成的自然语言描述

### Phase 4 输出

- **保存的事件数量**：成功保存到数据库的事件数量
- **每个事件的数据库ID**：PostgreSQL 中生成的事件 UUID

## 🔍 数据库验证

保存完成后，可以通过以下 SQL 查询验证数据：

```sql
-- 查看所有事件
SELECT id, start_time, camera_location, llm_description 
FROM event_logs 
ORDER BY start_time DESC 
LIMIT 10;

-- 查看人物出场记录
SELECT ea.id, ea.person_id, ea.match_method, el.start_time, el.llm_description
FROM event_appearances ea
JOIN event_logs el ON ea.event_id = el.id
ORDER BY el.start_time DESC
LIMIT 10;

-- 统计信息
SELECT 
    COUNT(*) as total_events,
    COUNT(DISTINCT person_id) as unique_people,
    COUNT(*) FILTER (WHERE match_method = 'face') as face_matches,
    COUNT(*) FILTER (WHERE match_method = 'body_reid') as body_matches
FROM event_appearances;
```

## ⚙️ 配置选项

### Phase 1 配置

在脚本中可以修改以下参数：

```python
cv_pipeline = CV_Pipeline(
    dataset_json_path=str(dataset_json),
    videos_base_dir=str(videos_dir),
    yolo_model='yolov8n.pt',          # YOLO 模型
    face_model_name='buffalo_l',      # InsightFace 模型
    reid_model_name='osnet_x1_0',     # ReID 模型
    enable_tracking=True              # 启用跟踪优化
)

clip_objs = cv_pipeline.process_all_clips(max_clips=5)  # 处理前5个视频
```

### Phase 2 配置

```python
fusion_pipeline = Event_Fusion_Pipeline(time_threshold=60)  # 时间阈值60秒
```

### Phase 3 配置

```python
llm_pipeline = LLM_Reasoning_Pipeline(
    model_name='gemini-2.5-flash-lite',  # Gemini 模型
    temperature=0.2,                     # 温度参数
    max_output_tokens=256                # 最大输出token数
)
```

## 🐛 故障排除

### 问题 1: Phase 1 初始化失败

**可能原因**：
- 模型文件未下载
- 视频文件路径错误

**解决方案**：
- 检查模型文件是否存在
- 验证视频文件路径

### 问题 2: Phase 3 LLM 调用失败

**可能原因**：
- Google Cloud 凭证未设置
- 网络连接问题
- API 配额限制

**解决方案**：
- 检查 `GOOGLE_APPLICATION_CREDENTIALS` 环境变量
- 验证网络连接
- 检查 API 配额

### 问题 3: Phase 4 数据库保存失败

**可能原因**：
- 数据库连接失败
- 表结构未初始化
- 向量格式错误

**解决方案**：
- 检查数据库连接配置
- 运行 `database/init_database.py` 初始化数据库
- 检查向量维度是否正确（2048维）

## 📝 示例输出

```
============================================================
Phase 1 + Phase 2 + Phase 3 + Phase 4 完整集成测试
============================================================

============================================================
Phase 1: 视觉扫描与特征提取
============================================================
✅ Phase 1 Pipeline 初始化成功
✅ Phase 1 完成: 生成了 5 个 Clip_Obj
   总帧数: 114
   总检测次数: 85

============================================================
Phase 2: 时空事件合并
============================================================
✅ Phase 2 Pipeline 初始化成功
✅ Phase 2 完成: 生成了 3 个全局事件
   总 Clip 数: 5
   平均每个事件 Clip 数: 1.7
   总时间跨度: 58 秒

============================================================
Phase 3: LLM 语义生成
============================================================
✅ Phase 3 Pipeline 初始化成功
✅ Phase 3 完成: 成功处理 3 个事件

============================================================
Phase 4: 结构化落库
============================================================
✅ Phase 4 Pipeline 初始化成功
✅ Phase 4 完成: 成功保存 3 个事件到数据库
   事件 #1: f8a2c351-8442-4766-a8bc-75c9dd3b8fa8
   事件 #2: 7318bce8-f7bb-420c-bac7-105766903928
   事件 #3: 76dbefb6-40a9-4c08-a147-c203d863fdda

============================================================
完整流程结果
============================================================
📝 事件 #1:
   时间: 2025-09-01 07:07:05 ~ 2025-09-01 07:07:05
   持续时间: 27 秒
   摄像头: doorbell, outdoor_side, outdoor_high
   人物: [21, 22] (2 个)
   Clip 数: 3

   📝 生成的日志:
   07:07，在doorbell、outdoor_side等3个位置检测到2个人员活动，详情见视频。

   ✅ LLM 生成: 有效
   💾 数据库ID: f8a2c351-8442-4766-a8bc-75c9dd3b8fa8

📊 最终统计:
   Phase 1: 5 个 Clip_Obj
   Phase 2: 3 个全局事件
   Phase 3: 3 个事件已生成日志
   有效日志: 3/3
   Phase 4: 3 个事件已保存到数据库

✅ 完整流程测试完成！
```

## 🔗 相关文档

- [Phase 1 文档](phase1_cv_scanning/README.md)
- [Phase 2 文档](phase2_event_fusion/README.md)
- [Phase 3 文档](phase3_agent_interaction/README.md)
- [Phase 4 文档](phase4_clean_store/README.md)
- [数据库初始化文档](../database/README.md)

