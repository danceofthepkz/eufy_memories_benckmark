# Phase 3: 宏观语义生成 (LLM Reasoning)

## 📋 概述

第三阶段使用 Gemini 2.5 Flash Lite 为合并后的事件生成自然语言日志，将结构化的监控数据转化为人类可读的文本描述。

## 🎯 核心功能

- **提示词工程**：组装 System Prompt 和 User Prompt，要求 LLM 详细描述人物行为
- **LLM 调用**：与 Google Gemini API 稳定交互
- **响应验证**：清洗和验证 LLM 输出
- **角色分类**：根据 LLM 描述的行为推断人物角色（如：快递员、服务人员等）⭐ **新增**
- **兜底生成**：API 失败时生成规则化日志

## 📁 模块结构

```
phase3_agent_interaction/
├── __init__.py              # 模块导出
├── prompt_engine.py         # 模块2: 提示词工程引擎
├── llm_gateway.py           # 模块3: LLM 客户端网关
├── response_validator.py    # 模块4: 响应清洗与校验器
├── role_classifier.py       # 角色分类器（基于行为推断角色）⭐ 新增
├── llm_reasoning_pipeline.py # 主 Pipeline
├── test_phase3.py           # 测试脚本
└── README.md                # 本文档
```

## 🔄 工作流程

```
Phase 2 输出 (Global_Event 列表)
  ↓
[模块2] 提示词工程（组装 System + User Prompt）
  ↓
[模块3] LLM 调用（Gemini API）
  ↓
[模块4] 响应验证（清洗、幻觉检测）
  ↓
[角色分类器] 根据行为推断角色（如：快递员、服务人员等）⭐ 新增
  ↓
输出: Global_Event 列表（包含 summary_text 和更新后的角色）
```

## 🆕 角色分类功能

### 基于行为的角色推断

Phase 3 新增了**角色分类器（RoleClassifier）**，可以根据 LLM 描述的行为自动推断人物角色：

**支持的角色类型**：
- `owner` / `family`: 家人
- `visitor`: 访客
- `delivery`: 快递员/配送员（根据"拿着包裹"、"送快递"等行为推断）
- `service`: 服务人员（根据"维修"、"清洁"等行为推断）
- `unknown`: 陌生人

**行为关键词示例**：
- **快递员**：包裹、快递、配送、送货、送餐、外卖、快递员、拿着包裹等
- **服务人员**：维修、清洁、保洁、安装、检修、工具箱等
- **访客**：访客、拜访、来访、客人、朋友、敲门、按门铃等

**工作流程**：
1. LLM 生成详细的事件描述（包含人物行为）
2. 角色分类器分析描述，提取行为关键词
3. 根据行为关键词推断角色（如：拿着包裹 → delivery）
4. 更新 `Global_Event` 中的 `people_info`，标记 `role_source='behavior_inference'`
5. Phase 4 保存时，将推断的角色映射到数据库支持的角色并更新

**角色映射到数据库**：
- `delivery` → `visitor`（数据库中的值）
- `service` → `visitor`（数据库中的值）
- `family` → `owner`（数据库中的值）
- `stranger` → `unknown`（数据库中的值）

## 📊 数据格式

### 输入：Global_Event（来自 Phase 2）

```python
{
    'start_time': datetime,
    'end_time': datetime,
    'duration': float,
    'cameras': List[str],
    'people': Set[int],
    'people_info': Dict[int, Dict],
    'clips': List[Dict],
    'prompt_text': str,  # Phase 2 生成的 Prompt
    ...
}
```

### 输出：Global_Event（添加了 summary_text 和更新后的角色）

```python
{
    ...  # 原有字段
    'summary_text': str,      # ✨ LLM 生成的日志文本（包含详细行为描述）
    'llm_valid': bool,        # ✨ 是否有效
    'llm_warnings': List[str], # ✨ 警告信息
    'people_info': Dict[int, Dict]  # ✨ 角色可能已更新（role_source='behavior_inference'）
}

# people_info 示例（角色已更新）：
{
    23: {
        'person_id': 23,
        'role': 'delivery',  # 从 'unknown' 更新为 'delivery'
        'role_source': 'behavior_inference',  # 标记为行为推断
        'behavior': '拿着包裹在门口按门铃',
        'method': 'new',
        ...
    },
    -1: {  # 陌生人标记
        'person_id': None,
        'role': 'delivery',  # 从 'unknown' 更新为 'delivery'
        'role_source': 'behavior_inference',
        'has_strangers': True,
        'stranger_count': 1,
        ...
    }
}
```

## 🚀 使用方法

### 基本使用

```python
from workflow.phase3_agent_interaction import LLM_Reasoning_Pipeline

# 初始化 Pipeline
pipeline = LLM_Reasoning_Pipeline(
    model_name='gemini-2.5-flash-lite',
    temperature=0.2,
    max_output_tokens=256
)

# 处理事件列表
processed_events = pipeline.process_events(global_events)

# 查看结果
for event in processed_events:
    print(f"日志: {event['summary_text']}")
```

### 与 Phase 2 集成

```python
from workflow import Event_Fusion_Pipeline, LLM_Reasoning_Pipeline

# Phase 2: 事件融合
fusion_pipeline = Event_Fusion_Pipeline(time_threshold=60)
global_events = fusion_pipeline.run(clip_objs)

# Phase 3: LLM 语义生成
llm_pipeline = LLM_Reasoning_Pipeline()
processed_events = llm_pipeline.process_events(global_events)
```

## ⚙️ 配置参数

### LLM_Reasoning_Pipeline 参数

- `model_name`: Gemini 模型名称（默认：`'gemini-2.5-flash-lite'`）
- `temperature`: 温度参数（默认：`0.2`，越低越客观）
- `max_output_tokens`: 最大输出 token 数（默认：`256`）
- `project_id`: Google Cloud 项目ID（默认：从环境变量读取）
- `location`: Vertex AI 区域（默认：`'us-central1'`）

### 环境变量

```bash
export GOOGLE_APPLICATION_CREDENTIALS=./gen-lang-sa.json
export GOOGLE_CLOUD_PROJECT=gen-lang-client-0057517563
export GOOGLE_CLOUD_LOCATION=us-central1
```

## 🧪 测试

运行测试脚本：

```bash
python workflow/phase3_agent_interaction/test_phase3.py
```

**注意**：测试需要配置 Google Cloud 环境变量和 Service Account 文件。

## 📈 示例输出

```
✅ LLM 语义生成完成: 2 个事件

📝 事件 #1:
   时间: 2025-09-01 09:00:00 ~ 2025-09-01 09:00:30
   人物: [1, 2] (2 个)
   生成日志: 09:00，家人(Person_1)和家人(Person_2)驾车回到庭院，随后步行经由正门进入室内。
   有效: True

📝 事件 #2:
   时间: 2025-09-01 09:01:30 ~ 2025-09-01 09:01:30
   人物: [] (0 个)
   生成日志: 09:01，在门口检测到陌生人出现，详情见视频。
   有效: True
```

## 🔍 关键特性

### 1. 提示词工程

- **System Prompt**：定义 LLM 角色和规则
- **User Prompt**：包含事件时间线和上下文信息
- **语义映射**：将摄像头代码转换为中文描述

### 2. 容错机制

- **重试机制**：使用 `tenacity` 库，自动重试失败的请求
- **指数退避**：避免频繁重试导致限流
- **兜底生成**：API 失败时生成规则化日志

### 3. 响应验证

- **格式清洗**：去除 Markdown 符号、多余换行
- **幻觉检测**：检查输出是否符合输入事件
- **质量保证**：确保生成的日志准确可靠

## 🐛 故障排除

### 问题1: Vertex AI 初始化失败

**错误信息**:
```
无法确定项目ID，请设置 GOOGLE_CLOUD_PROJECT 环境变量
```

**解决方案**:
```bash
export GOOGLE_CLOUD_PROJECT=your-project-id
export GOOGLE_APPLICATION_CREDENTIALS=./gen-lang-sa.json
```

### 问题2: API 调用失败

**错误信息**:
```
PermissionDenied: Permission 'aiplatform.models.predict' denied
```

**解决方案**:
- 检查 Service Account 是否有 `Vertex AI User` 角色
- 确认项目已启用 Vertex AI API

### 问题3: 模型不可用

**错误信息**:
```
404 models/gemini-2.5-flash-lite is not found
```

**解决方案**:
- 确认 Vertex AI 支持该模型
- 检查服务账号权限
- 验证模型名称是否正确

## 💡 最佳实践

1. **温度设置**：使用较低的 temperature（0.2）保证客观性
2. **Token 限制**：根据需求调整 `max_output_tokens`
3. **错误处理**：监控 `llm_warnings`，及时发现问题
4. **成本控制**：批量处理事件，避免频繁调用 API

## 🔗 相关文档

- `重要的模块/第三阶段.md` - 设计文档
- `重要的模块/流程完整.md` - 完整流程说明
- `workflow/README.md` - Workflow 总览
- `gemini_setup.md` - Gemini API 设置指南

## 📝 注意事项

- **API 成本**：每次调用都会产生费用，注意控制调用频率
- **响应时间**：LLM API 调用需要一定时间，批量处理时注意超时设置
- **错误处理**：系统会自动使用兜底生成，确保不会丢失数据

