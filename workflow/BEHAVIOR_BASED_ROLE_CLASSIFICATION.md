# 基于行为的角色分类功能

## 📋 功能概述

Phase 3 新增了**基于行为的角色分类**功能，可以根据 LLM 描述的人物行为自动推断并更新人物角色。

## 🎯 核心目标

1. **更详细的 LLM 描述**：要求 LLM 详细描述人物在做什么（例如：拿着包裹、按门铃、等待等）
2. **自动角色推断**：根据行为关键词自动推断人物角色（如：拿着包裹 → delivery）
3. **角色更新**：更新 `Global_Event` 中的人物角色，并在 Phase 4 保存到数据库

## 🏗️ 实现架构

### 1. RoleClassifier（角色分类器）

**位置**：`workflow/phase3_agent_interaction/role_classifier.py`

**核心功能**：
- `classify_from_description(description, current_role)`: 从描述中推断角色
- `extract_person_behaviors(description, people_info)`: 提取每个人物的行为信息
- `update_people_roles(global_event, behaviors)`: 更新 Global_Event 中的人物角色

**行为关键词映射**：
- **delivery（快递员）**：快递、包裹、配送、送货、送餐、外卖、快递员、拿着包裹等
- **service（服务人员）**：维修、清洁、保洁、安装、检修、工具箱等
- **visitor（访客）**：访客、拜访、来访、客人、朋友、敲门、按门铃等
- **owner（家人）**：家人、主人、住户、居民等

### 2. Prompt 增强

**位置**：`workflow/phase3_agent_interaction/prompt_engine.py`

**修改内容**：
- 在 System Prompt 中添加行为描述要求
- 要求 LLM 详细描述人物在做什么（例如：拿着包裹、按门铃、等待、离开等）
- 输出格式从 50-150 字扩展到 50-200 字

### 3. Phase 3 Pipeline 集成

**位置**：`workflow/phase3_agent_interaction/llm_reasoning_pipeline.py`

**修改内容**：
- 在 LLM 响应验证后，调用角色分类器
- 提取人物行为并推断角色
- 更新 `Global_Event` 中的 `people_info`

### 4. Phase 4 角色更新

**位置**：`workflow/phase4_clean_store/persistence_pipeline.py`

**修改内容**：
- 在保存 `event_appearances` 时，检查是否有推断的角色
- 如果有，更新 `persons` 表的 `role` 字段
- 将推断的角色映射到数据库支持的角色（delivery → visitor）

## 🔄 数据流

```
Phase 2: Global_Event (people_info 中 role='unknown')
  ↓
Phase 3: LLM 生成描述（包含详细行为）
  ↓
Phase 3: RoleClassifier 分析行为
  ↓
Phase 3: 更新 people_info (role='delivery', role_source='behavior_inference')
  ↓
Phase 4: 保存到数据库
  ↓
Phase 4: 更新 persons.role = 'visitor' (delivery 映射为 visitor)
```

## 📊 角色映射规则

### 推断的角色 → 数据库角色

| 推断角色 | 数据库角色 | 说明 |
|---------|-----------|------|
| `owner` | `owner` | 家人 |
| `family` | `owner` | 家人（同义词） |
| `visitor` | `visitor` | 访客 |
| `delivery` | `visitor` | 快递员（映射为访客） |
| `service` | `visitor` | 服务人员（映射为访客） |
| `stranger` | `unknown` | 陌生人 |
| `unknown` | `unknown` | 未知 |

**注意**：当前数据库 schema 只支持 `owner`, `visitor`, `unknown`。如果需要支持 `delivery` 和 `service`，需要扩展数据库 schema。

## 🧪 使用示例

### 示例 1：快递员识别

**LLM 描述**：
```
07:07:05 门口出现一个陌生人，拿着包裹在按门铃，疑似快递员送快递。
```

**角色推断**：
- 检测到关键词：`拿着包裹`、`按门铃`、`快递员`、`送快递`
- 推断角色：`delivery`
- 更新：`people_info[-1]['role'] = 'delivery'`

**数据库保存**：
- `persons.role = 'visitor'`（delivery 映射为 visitor）
- `persons.notes = '[行为推断: delivery]'`

### 示例 2：服务人员识别

**LLM 描述**：
```
10:30:00 门口出现一个陌生人，拿着工具箱，疑似维修工进行检修。
```

**角色推断**：
- 检测到关键词：`工具箱`、`维修工`、`检修`
- 推断角色：`service`
- 更新：`people_info[-1]['role'] = 'service'`

**数据库保存**：
- `persons.role = 'visitor'`（service 映射为 visitor）
- `persons.notes = '[行为推断: service]'`

## 🔧 配置和扩展

### 添加新的角色类型

1. **在 `RoleClassifier.BEHAVIOR_PATTERNS` 中添加新的行为关键词**：
```python
BEHAVIOR_PATTERNS = {
    'new_role': [
        r'关键词1', r'关键词2', ...
    ],
    ...
}
```

2. **在 `Persistence_Pipeline._map_role_to_db` 中添加映射规则**：
```python
role_mapping = {
    'new_role': 'visitor',  # 或 'owner', 'unknown'
    ...
}
```

3. **（可选）扩展数据库 schema**：
如果需要数据库直接支持新角色，需要修改 `database/init_database.sql` 中的 `role` 字段注释和约束。

## 📝 注意事项

1. **角色推断的准确性**：
   - 依赖于 LLM 描述的详细程度
   - 如果 LLM 描述不够详细，可能无法正确推断
   - 可以通过优化 Prompt 来提高描述质量

2. **角色映射**：
   - 当前 `delivery` 和 `service` 都映射为 `visitor`
   - 如果需要区分，需要扩展数据库 schema

3. **性能影响**：
   - 角色推断使用正则表达式匹配，性能开销很小
   - 不会影响整体处理速度

4. **向后兼容**：
   - 如果 LLM 描述中没有行为关键词，角色保持不变
   - 不会影响现有功能

## 🔗 相关文档

- [Phase 3 README](phase3_agent_interaction/README.md)
- [Phase 4 README](phase4_clean_store/README.md)
- [数据库 Schema](../../database/init_database.sql)

