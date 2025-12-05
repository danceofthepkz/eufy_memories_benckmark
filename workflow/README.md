# Workflow 模块

## 📋 概述

本模块实现了完整的视频处理工作流，从视频输入到用户检索的端到端流程，包含 7 个阶段：

- **Phase 0**: 系统初始化 (Initialization) - 加载家人底库
- **Phase 1**: 视觉扫描与特征提取 (CV Scanning) - 视频处理和人物识别
- **Phase 2**: 时空事件合并 (Event Fusion) - 将碎片化事件合并为连续场景
- **Phase 3**: 宏观语义生成 (LLM Reasoning) - 使用 Gemini 生成自然语言日志
- **Phase 4**: 结构化落库 (Persistence) - 持久化到 PostgreSQL 数据库
- **Phase 5**: 记忆压缩 (Daily Summary) - 生成每日总结
- **Phase 6**: 用户检索 (User Retrieval) - RAG 检索和问答

## 🏗️ 模块结构

```
workflow/
├── __init__.py                    # 模块导出
├── phase0_initialization.py       # Phase 0: 系统初始化
├── test_phase0.py                 # Phase 0 测试脚本
├── clear_database.py              # 清空数据库脚本（测试前使用）
├── create_initial_body_cache.py   # 创建初始身体特征缓存
│
├── phase1_cv_scanning/            # Phase 1: 视觉扫描与特征提取
│   ├── __init__.py
│   ├── data_loader.py             # 模块1: 数据加载与对齐
│   ├── frame_sampler.py           # 模块2: 视频流采样
│   ├── yolo_detector.py           # 模块3: 多目标检测
│   ├── feature_encoder.py         # 模块4: 双模态特征编码
│   ├── identity_arbiter.py        # 模块5: 身份仲裁与缓存管理
│   ├── result_buffer.py           # 模块6: 结果暂存
│   ├── simple_tracker.py          # 跟踪优化模块
│   ├── cv_pipeline.py             # 主Pipeline类
│   ├── test_phase1.py             # Phase 1 测试脚本
│   └── README.md                  # Phase 1 文档
│
├── phase2_event_fusion/           # Phase 2: 时空事件合并
│   ├── __init__.py
│   ├── stream_sorter.py           # 时间流排序
│   ├── fusion_policy.py           # 融合策略引擎
│   ├── session_manager.py         # 会话管理器
│   ├── event_aggregator.py        # 事件聚合器
│   ├── identity_refiner.py        # 身份一致性检查
│   ├── context_builder.py         # 上下文构建器
│   ├── event_fusion_pipeline.py   # 主Pipeline类
│   ├── test_phase2.py             # Phase 2 测试脚本
│   └── README.md                  # Phase 2 文档
│
├── phase3_agent_interaction/      # Phase 3: 宏观语义生成
│   ├── __init__.py
│   ├── prompt_engine.py           # 提示词工程引擎
│   ├── llm_gateway.py             # LLM 客户端网关
│   ├── response_validator.py      # 响应验证器
│   ├── role_classifier.py         # 角色分类器
│   ├── llm_reasoning_pipeline.py # 主Pipeline类
│   ├── test_phase3.py             # Phase 3 测试脚本
│   └── README.md                  # Phase 3 文档
│
├── phase4_clean_store/            # Phase 4: 结构化落库
│   ├── __init__.py
│   ├── quality_selector.py        # 质量评估与优选器
│   ├── vector_adapter.py          # 向量序列化适配器
│   ├── transaction_manager.py    # 事务管理器
│   ├── persistence_pipeline.py   # 主Pipeline类
│   ├── test_phase4.py             # Phase 4 测试脚本
│   └── README.md                  # Phase 4 文档
│
├── phase5_summarize/              # Phase 5: 记忆压缩
│   ├── __init__.py
│   ├── query_engine.py            # 时间切片查询器
│   ├── narrative_aggregator.py   # 叙事流聚合器
│   ├── insight_engine.py          # 高维洞察引擎
│   ├── archive_persister.py       # 归档持久化器
│   ├── daily_summary_pipeline.py  # 主Pipeline类
│   ├── test_phase5.py             # Phase 5 测试脚本
│   └── README.md                  # Phase 5 文档
│
├── phase6_usr_retrieval/          # Phase 6: 用户检索
│   ├── __init__.py
│   ├── query_parser.py            # 语义查询解析器
│   ├── retrieval_engine.py        # 混合检索引擎
│   ├── evidence_materializer.py   # 证据实物化模块
│   ├── rag_synthesis_engine.py    # RAG 合成引擎
│   ├── user_retrieval_pipeline.py # 主Pipeline类
│   ├── test_phase6.py             # Phase 6 测试脚本
│   └── README.md                  # Phase 6 文档
│
├── integrate_phase1_phase2.py     # Phase 1+2 集成测试
├── integrate_phase123.py          # Phase 1+2+3 集成测试
├── integrate_phase1234.py         # Phase 1+2+3+4 集成测试
├── integrate_phase12345.py        # Phase 1+2+3+4+5 集成测试
├── integrate_all_phases.py        # Phase 0-6 完整集成测试
│
├── 系统完整流程UML图.puml         # 系统架构 UML 图
├── 系统流程序列图.puml            # 序列图
├── 系统数据流向图.puml            # 数据流向图
│
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
source venv/bin/activate
source setup_env.sh
python workflow/test_phase0.py
```

## 🔄 Phase 1: 视觉扫描与特征提取

### 功能

系统遍历视频，提取元数据用于后续合并：

- **数据加载与对齐**: 解析 JSON 元数据，对齐视频文件
- **视频流采样**: 每秒提取 1 帧
- **多目标检测**: YOLOv8 检测所有人物
- **双模态特征编码**: 
  - 人脸特征 (ArcFace 512维)
  - 身体特征 (ReID 2048维)
- **身份仲裁与缓存管理**: 
  - 有正脸 → 匹配底库
  - 无正脸 → 匹配身体缓存
  - 无匹配 → 判定为陌生人
- **跟踪优化**: 可选，跳过重复检测以提高性能
- **结果暂存**: 生成 Clip_Obj（不写入数据库）

### 使用方法

```python
from workflow import CV_Pipeline

# 初始化 Pipeline
pipeline = CV_Pipeline(
    dataset_json_path='memories_ai_benchmark/long_mem_dataset.json',
    videos_base_dir='memories_ai_benchmark/videos',
    enable_tracking=True  # 启用跟踪优化
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

## 🔗 Phase 2: 时空事件合并

### 功能

将碎片化的 Clip 合并为连续的全局事件：

- **时间流排序**: 按时间戳排序所有 Clip
- **融合策略判断**: 
  - 时间间隔 < 60秒
  - 有共同人物
- **滑动窗口分组**: 将相关 Clip 合并为事件
- **事件聚合打包**: 生成 Global_Event 对象
- **身份一致性检查**: 优化身份识别结果
- **上下文构建**: 生成 LLM Prompt 文本

### 使用方法

```python
from workflow import Event_Fusion_Pipeline

# 初始化 Pipeline
fusion_pipeline = Event_Fusion_Pipeline(time_threshold=60)

# 运行事件融合
global_events = fusion_pipeline.run(clip_objs)
```

### 测试

```bash
python workflow/phase2_event_fusion/test_phase2.py
```

## 🧠 Phase 3: 宏观语义生成

### 功能

使用 Gemini 2.5 Flash Lite 为事件生成自然语言日志：

- **提示词工程**: 构建系统提示和用户提示
- **LLM 调用**: 通过 Vertex AI 调用 Gemini API
- **响应验证**: 清洗和验证 LLM 输出
- **角色分类**: 根据行为推断人物角色（家人/访客/快递员等）

### 使用方法

```python
from workflow import LLM_Reasoning_Pipeline

# 初始化 Pipeline
llm_pipeline = LLM_Reasoning_Pipeline(
    model_name='gemini-2.5-flash-lite',
    temperature=0.2
)

# 处理事件列表
processed_events = llm_pipeline.process_events(global_events)
```

### 测试

```bash
python workflow/phase3_agent_interaction/test_phase3.py
```

## 💾 Phase 4: 结构化落库

### 功能

将分析结果持久化到 PostgreSQL 数据库：

- **质量评估优选**: 选择最佳检测记录
- **向量格式转换**: 转换为 pgvector 格式
- **事务管理**: 保证数据一致性
- **批量写入**: 
  - `event_logs` 表（事件主表）
  - `event_appearances` 表（人物出场快照）
  - `persons` 表（陌生人自动创建）

### 使用方法

```python
from workflow import Persistence_Pipeline

# 初始化 Pipeline
persistence_pipeline = Persistence_Pipeline()

# 保存单个事件
event_id = persistence_pipeline.save_event(global_event)

# 批量保存
event_ids = persistence_pipeline.save_events(global_events)
```

### 测试

```bash
python workflow/phase4_clean_store/test_phase4.py
```

## 📅 Phase 5: 记忆压缩

### 功能

从数据库中查询每日事件，使用 LLM 生成每日总结：

- **时间切片查询**: 查询指定日期的事件
- **叙事流聚合**: 格式化时间线文本
- **高维洞察引擎**: LLM 生成总结
- **归档持久化**: 保存到 `daily_summaries` 表

### 使用方法

```python
from workflow import Daily_Summary_Pipeline

# 初始化 Pipeline
summary_pipeline = Daily_Summary_Pipeline()

# 处理指定日期
summary_pipeline.run_for_date('2025-09-01', force_update=False)

# 批量处理
summary_pipeline.run_batch(date_list=None, force_update=False)
```

### 测试

```bash
python workflow/phase5_summarize/test_phase5.py
```

## 🔍 Phase 6: 用户检索

### 功能

回答用户的自然语言问题，支持 RAG 检索：

- **语义查询解析**: 解析用户问题，提取实体和意图
- **混合检索**: 查询数据库（SQL + 向量搜索）
- **证据实物化**: 提取相关图片
- **RAG 合成**: 使用 LLM 生成最终回答

### 使用方法

```python
from workflow import User_Retrieval_Pipeline

# 初始化 Pipeline
retrieval_pipeline = User_Retrieval_Pipeline(
    videos_base_dir='memories_ai_benchmark/videos'
)

# 回答用户问题
result = retrieval_pipeline.answer("9月1日那天，爸爸回家的时候穿什么衣服？")

print(result['answer'])  # 最终回答
print(result['images'])  # 相关图片列表
```

### 测试

```bash
python workflow/phase6_usr_retrieval/test_phase6.py
```

## 🔧 配置要求

### 环境变量

确保已设置数据库和 Google Cloud 连接信息（通过 `setup_env.sh`）：

```bash
# PostgreSQL 配置
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=neweufy
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=your_password

# Google Cloud 配置
export GOOGLE_APPLICATION_CREDENTIALS=./gen-lang-sa.json
export GOOGLE_CLOUD_PROJECT=your-project-id
export GOOGLE_CLOUD_LOCATION=us-central1
```

### 数据库要求

- PostgreSQL 15+
- pgvector 扩展已启用
- 表结构已初始化（运行 `database/init_database.py`）

### Google Cloud 要求

- Service Account JSON 文件
- Vertex AI API 已启用
- 服务账号具有 `Vertex AI User` 角色

## 📊 完整工作流程

```
清空数据库 (可选)
  ↓
Phase 0: 系统初始化
  ↓
  加载家人底库 → 提取特征 → 注册到数据库
  ↓
创建初始身体特征缓存 (重要！)
  ↓
  从第一个视频提取人物背影特征
  ↓
Phase 1: 视觉扫描与特征提取
  ↓
  处理视频 → 检测人物 → 识别身份 → 暂存结果 (Clip_Obj)
  ↓
Phase 2: 时空事件合并
  ↓
  时间流排序 → 融合策略判断 → 事件分组 → 生成全局事件 (Global_Event)
  ↓
Phase 3: 宏观语义生成
  ↓
  构建 Prompt → 调用 Gemini → 生成自然语言日志 (summary_text)
  ↓
Phase 4: 结构化落库
  ↓
  质量优选 → 向量转换 → 事务写入 → 保存到数据库
  ↓
Phase 5: 记忆压缩 (可选，定时执行)
  ↓
  查询每日事件 → LLM 生成总结 → 保存到 daily_summaries
  ↓
Phase 6: 用户检索 (实时查询)
  ↓
  解析用户问题 → 检索数据库 → RAG 合成 → 返回答案
```

## 🧪 测试流程

### 方式 1: 完整集成测试（推荐）

运行 Phase 0 → Phase 6 的完整流程：

```bash
# 1. 激活环境
source venv/bin/activate
source setup_env.sh

# 2. 清空数据库（可选）
python workflow/clear_database.py --yes

# 3. 运行完整流程
python workflow/integrate_all_phases.py
```

### 方式 2: 分阶段测试

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

# 7. 运行 Phase 3（测试 LLM 生成）
python workflow/phase3_agent_interaction/test_phase3.py

# 8. 运行 Phase 4（测试数据库持久化）
python workflow/phase4_clean_store/test_phase4.py

# 9. 运行 Phase 5（测试每日总结）
python workflow/phase5_summarize/test_phase5.py

# 10. 运行 Phase 6（测试用户检索）
python workflow/phase6_usr_retrieval/test_phase6.py
```

### 方式 3: 部分集成测试

```bash
# Phase 1 + Phase 2
python workflow/integrate_phase1_phase2.py

# Phase 1 + Phase 2 + Phase 3
python workflow/integrate_phase123.py

# Phase 1 + Phase 2 + Phase 3 + Phase 4
python workflow/integrate_phase1234.py

# Phase 1 + Phase 2 + Phase 3 + Phase 4 + Phase 5
python workflow/integrate_phase12345.py
```

### 为什么需要步骤 4（创建初始身体特征缓存）？

如果视频中的人物都是侧脸/背影，系统无法通过人脸识别。但可以通过身体特征（ReID）匹配：

- **步骤 4** 从第一个视频提取人物背影特征
- 将这些特征作为家人的初始 `current_body_embedding` 缓存
- **步骤 5** 中，后续视频的人物背影可以匹配到这些缓存

## 📈 性能优化

### Phase 1 跟踪优化

启用跟踪可以显著提高性能：

```python
pipeline = CV_Pipeline(
    enable_tracking=True,      # 启用跟踪
    iou_threshold=0.7,         # IoU 阈值
    revalidate_interval=5,     # 重新验证间隔（帧数）
    max_age=3                  # 跟踪最大年龄（帧数）
)
```

**效果**: 可以跳过 30-50% 的重复检测，显著减少计算量。

### 批处理大小

根据内存情况调整批处理大小：

```python
# 处理少量视频（测试）
clip_objs = pipeline.process_all_clips(max_clips=5)

# 处理所有视频（生产）
clip_objs = pipeline.process_all_clips(max_clips=None)
```

## 📚 相关文档

### 核心文档
- `重要的模块/流程完整.md` - 完整流程说明
- `重要的模块/第一阶段.md` ~ `第六阶段.md` - 各阶段详细设计
- `重要的模块/sql方案.md` - 数据库设计方案

### 阶段文档
- `workflow/phase1_cv_scanning/README.md` - Phase 1 使用文档
- `workflow/phase2_event_fusion/README.md` - Phase 2 使用文档
- `workflow/phase3_agent_interaction/README.md` - Phase 3 使用文档
- `workflow/phase4_clean_store/README.md` - Phase 4 使用文档
- `workflow/phase5_summarize/README.md` - Phase 5 使用文档
- `workflow/phase6_usr_retrieval/README.md` - Phase 6 使用文档

### UML 图
- `workflow/系统完整流程UML图.puml` - 系统架构 UML 图（类图）
- `workflow/系统流程序列图.puml` - 序列图
- `workflow/系统数据流向图.puml` - 数据流向图（活动图）

**查看 UML 图**:
- 使用在线工具: https://www.plantuml.com/plantuml/uml/
- 使用 VS Code 插件: 安装 "PlantUML" 插件
- 使用命令行: `plantuml workflow/系统完整流程UML图.puml`

### 实现总结
- `workflow/PHASE0_IMPLEMENTATION.md` - Phase 0 实现总结
- `workflow/PHASE1_PHASE2_INTEGRATION.md` - Phase 1+2 集成说明
- `workflow/PHASE1234_INTEGRATION.md` - Phase 1-4 集成说明
- `workflow/PHASE12345_INTEGRATION.md` - Phase 1-5 集成说明
- `workflow/BEHAVIOR_BASED_ROLE_CLASSIFICATION.md` - 基于行为的角色分类
- `workflow/IDENTITY_REFINEMENT.md` - 身份优化说明
- `workflow/REID_SETUP.md` - ReID 模型配置

## 🔍 数据流示例

### 示例场景: "爸爸回家"

1. **Phase 0**: 系统初始化时，爸爸的照片已注册到底库
2. **Phase 1**: 
   - 视频1 (09:00:00, 庭院): 检测到人物A，有正脸 → 匹配底库 → 判定为爸爸
   - 视频2 (09:00:15, 门口): 检测到人物A，有正脸 → 匹配底库 → 判定为爸爸
   - 视频3 (09:00:30, 客厅): 检测到人物A，有正脸 → 匹配底库 → 判定为爸爸
3. **Phase 2**: 
   - 三个视频时间间隔 < 60秒，且有共同人物(爸爸)
   - 合并为一个 Global_Event: "09:00:00 ~ 09:00:30，爸爸从庭院到门口到客厅"
4. **Phase 3**: 
   - LLM 生成: "09:00，家人(Dad)驾车回到庭院，随后步行经由正门进入室内。"
5. **Phase 4**: 
   - 写入 `event_logs` 表
   - 写入 `event_appearances` 表 (爸爸的出场记录，包含当时的身体特征)
6. **Phase 5**: (可选，定时执行)
   - 查询当天所有事件，生成每日总结
7. **Phase 6**: (用户查询时)
   - 用户问: "9月1日爸爸回家穿什么衣服？"
   - 检索数据库，找到相关事件和身体特征
   - LLM 生成回答: "9月1日18:00爸爸回家时，身穿红色T恤和黑色长裤。"

## 💡 最佳实践

1. **首次运行**: 必须按顺序执行 Phase 0 → 创建缓存 → Phase 1
2. **批量处理**: 使用集成测试脚本，避免手动传递数据
3. **错误处理**: 查看日志输出，定位问题阶段
4. **性能优化**: 启用跟踪优化，减少重复计算
5. **数据备份**: 定期备份数据库，避免数据丢失

## 🐛 常见问题

### Q: Phase 1 无法识别背影人物？

**A**: 需要先运行 `create_initial_body_cache.py` 创建初始身体特征缓存。

### Q: Phase 3 LLM 调用失败？

**A**: 检查 Google Cloud 配置和 Service Account 权限。

### Q: Phase 4 数据库写入失败？

**A**: 检查数据库连接和表结构是否正确初始化。

### Q: Phase 6 检索不到结果？

**A**: 确保 Phase 4 已成功写入数据，检查查询条件是否正确。

---

**最后更新**: 2025年  
**版本**: v5.0
