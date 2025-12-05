# 家庭智能安防系统 - 完整配置与运行指南

## 📋 项目概述

这是一个基于 AI 的家庭智能安防系统，能够：
- 自动识别视频中的人物（家人/陌生人）
- 通过时空事件合并，理解连续的活动场景
- 使用 LLM 生成自然语言日志
- 支持以图搜人、自然语言查询等高级功能

**系统架构**: Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6

## 🎯 系统要求

### 硬件要求
- **CPU**: 支持 AVX 指令集（用于深度学习模型）
- **内存**: 至少 8GB RAM（推荐 16GB+）
- **存储**: 至少 10GB 可用空间（用于模型和数据库）
- **GPU**: 可选，但会显著加速处理速度

### 软件要求
- **操作系统**: macOS / Linux / Windows (WSL2)
- **Python**: 3.8+ (推荐 3.11)
- **PostgreSQL**: 15+ (必须)
- **pgvector**: 扩展插件 (必须)

## 🚀 快速开始

### 步骤 1: 克隆项目

```bash
cd /path/to/your/workspace
git clone <repository-url>
cd Eufynew
```

### 步骤 2: 创建 Python 虚拟环境

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
# macOS/Linux:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```

### 步骤 3: 安装依赖

```bash
# 确保已激活虚拟环境
pip install --upgrade pip
pip install -r requirements.txt
```

**注意**: 首次安装可能需要 10-20 分钟，因为需要下载深度学习模型。

### 步骤 4: 安装 PostgreSQL 和 pgvector

#### macOS (使用 Homebrew)

```bash
# 安装 PostgreSQL
brew install postgresql@15
brew services start postgresql@15

# 安装 pgvector
brew install pgvector
```

#### Linux (Ubuntu/Debian)

```bash
# 安装 PostgreSQL
sudo apt-get update
sudo apt-get install postgresql-15 postgresql-contrib-15

# 安装 pgvector
sudo apt-get install postgresql-15-pgvector

# 启动服务
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

#### 验证安装

```bash
# 检查 PostgreSQL 版本
psql --version

# 检查服务状态 (macOS)
brew services list | grep postgresql

# 检查服务状态 (Linux)
sudo systemctl status postgresql
```

### 步骤 5: 配置数据库

#### 5.1 创建数据库用户（如果需要）

```bash
# 连接到 PostgreSQL
psql -U postgres

# 创建用户（如果还没有）
CREATE USER postgres WITH PASSWORD 'your_password';
ALTER USER postgres CREATEDB;
\q
```

#### 5.2 初始化数据库

```bash
# 确保已激活虚拟环境
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate      # Windows

# 设置环境变量（临时）
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=neweufy
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=your_password  # 替换为你的密码

# 运行初始化脚本
python database/init_database.py
```

**预期输出**:
```
✅ 数据库 'neweufy' 创建成功
✅ 数据库表结构创建成功！
📊 已创建的表 (5 个):
   - daily_summaries
   - event_appearances
   - event_logs
   - person_faces
   - persons
✅ pgvector 扩展已启用
🎉 数据库初始化完成！
```

### 步骤 6: 配置 Google Cloud / Gemini API

#### 6.1 获取 Service Account 文件

1. 登录 [Google Cloud Console](https://console.cloud.google.com/)
2. 选择或创建项目
3. 进入 **IAM & Admin** > **Service Accounts**
4. 创建或选择服务账号
5. 下载 JSON 密钥文件（例如：`gen-lang-sa.json`）
6. 将文件放在项目根目录

#### 6.2 配置权限

Service Account 需要以下 IAM 角色：
- **Vertex AI User** (`roles/aiplatform.user`)
- **Service Account User** (`roles/iam.serviceAccountUser`)

#### 6.3 设置环境变量

创建或编辑 `setup_env.sh`:

```bash
#!/bin/bash

# Google Cloud 配置
export GOOGLE_APPLICATION_CREDENTIALS=./gen-lang-sa.json
export GOOGLE_CLOUD_PROJECT=your-project-id  # 替换为你的项目ID
export GOOGLE_CLOUD_LOCATION=us-central1

# PostgreSQL 配置
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=neweufy
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=your_password  # 替换为你的密码
```

**使用方式**:
```bash
source setup_env.sh
```

#### 6.4 验证 Google Cloud 配置

```bash
python scripts/verify_google_cloud_config.py
```

### 步骤 7: 准备数据文件

确保以下文件/目录存在：

```
Eufynew/
├── memories_ai_benchmark/
│   ├── lib/                    # 家人照片底库
│   │   ├── 1.jpeg
│   │   └── 2.jpeg
│   ├── long_mem_dataset.json   # 视频元数据
│   └── videos/                 # 视频文件目录
│       ├── 1.mp4
│       ├── 2.mp4
│       └── ...
└── gen-lang-sa.json            # Google Cloud Service Account 文件
```

## 🎬 运行完整流程

### 方式 1: 完整集成测试（推荐）

运行 Phase 0 → Phase 6 的完整流程：

```bash
# 1. 激活环境
source venv/bin/activate
source setup_env.sh

# 2. 清空数据库（可选，用于重新开始）
python workflow/clear_database.py --yes

# 3. 运行完整流程
python workflow/integrate_all_phases.py
```

### 方式 2: 分阶段运行

#### Phase 0: 系统初始化

```bash
source venv/bin/activate
source setup_env.sh

# 运行 Phase 0（加载家人人脸底库）
python workflow/test_phase0.py
```

**预期输出**:
```
✅ 加载底库图片: 1 -> 特征维度: (512,)
✅ 加载底库图片: 2 -> 特征维度: (512,)
✅ 底库加载完成，共 2 张有效图片
✅ 注册完成:
   - 新建家人记录: 2
   - 新增人脸特征: 2
```

#### Phase 1: 视觉扫描与特征提取

```bash
# 创建初始身体特征缓存（重要！）
# 从第一个视频提取人物背影，作为家人的初始身体特征缓存
python workflow/create_initial_body_cache.py

# 运行 Phase 1
python workflow/phase1_cv_scanning/test_phase1.py
```

#### Phase 2: 时空事件合并

```bash
python workflow/phase2_event_fusion/test_phase2.py
```

#### Phase 3: LLM 语义生成

```bash
python workflow/phase3_agent_interaction/test_phase3.py
```

#### Phase 4: 结构化落库

```bash
python workflow/phase4_clean_store/test_phase4.py
```

#### Phase 5: 记忆压缩

```bash
python workflow/phase5_summarize/test_phase5.py
```

#### Phase 6: 用户检索

```bash
python workflow/phase6_usr_retrieval/test_phase6.py
```

### 方式 3: 集成测试（部分阶段）

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

## 📊 工作流程说明

### 完整数据流

```
[视频文件] 
   ⬇️ (Phase 1: YOLO + ArcFace + ReID)
[Clip_Obj] (元数据碎片)
   ⬇️ (Phase 2: 时间 & 人物聚类)
[Global_Event] (全局事件包)
   ⬇️ (Phase 3: Gemini 2.5 Flash Lite)
[自然语言故事]
   ⬇️ (Phase 4: PostgreSQL)
[数据库 (Events + Appearances)]
   ⬇️ (Phase 5: 每日总结)
[daily_summaries]
   ⬇️ (Phase 6: RAG Search)
[用户答案]
```

### 各阶段功能

| 阶段 | 功能 | 输入 | 输出 |
|------|------|------|------|
| **Phase 0** | 系统初始化 | 底库图片 | 数据库中的家人记录 |
| **Phase 1** | 视觉扫描 | 视频文件 | Clip_Obj 列表 |
| **Phase 2** | 事件合并 | Clip_Obj 列表 | Global_Event 列表 |
| **Phase 3** | LLM 语义生成 | Global_Event 列表 | 带 summary_text 的事件 |
| **Phase 4** | 结构化落库 | 带 summary 的事件 | 数据库记录 |
| **Phase 5** | 记忆压缩 | 数据库事件 | 每日总结 |
| **Phase 6** | 用户检索 | 用户问题 | 答案 + 图片证据 |

## 🔧 配置详解

### 环境变量配置

#### 方式 1: 使用 setup_env.sh（推荐）

```bash
source setup_env.sh
```

#### 方式 2: 使用 .env 文件

创建 `.env` 文件：

```bash
# Google Cloud
GOOGLE_APPLICATION_CREDENTIALS=./gen-lang-sa.json
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=neweufy
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
```

#### 方式 3: 手动设置

```bash
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=neweufy
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=your_password
export GOOGLE_APPLICATION_CREDENTIALS=./gen-lang-sa.json
export GOOGLE_CLOUD_PROJECT=your-project-id
export GOOGLE_CLOUD_LOCATION=us-central1
```

### 数据库配置

#### 修改数据库连接

编辑 `setup_env.sh` 或 `.env` 文件中的以下变量：

```bash
POSTGRES_HOST=localhost      # 数据库主机
POSTGRES_PORT=5432           # 数据库端口
POSTGRES_DB=neweufy          # 数据库名称
POSTGRES_USER=postgres       # 用户名
POSTGRES_PASSWORD=your_pass  # 密码
```

#### 测试数据库连接

```bash
python database/test_connection.py
```

### Google Cloud 配置

#### 修改项目配置

编辑 `setup_env.sh` 或 `.env` 文件：

```bash
GOOGLE_APPLICATION_CREDENTIALS=./gen-lang-sa.json
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
```

#### 验证配置

```bash
python scripts/verify_google_cloud_config.py
```

## 🧪 测试指南

### 快速测试（小数据集）

```bash
# 1. 激活环境
source venv/bin/activate
source setup_env.sh

# 2. 清空数据库
python workflow/clear_database.py --yes

# 3. 运行 Phase 0
python workflow/test_phase0.py

# 4. 创建初始身体特征缓存
python workflow/create_initial_body_cache.py

# 5. 运行 Phase 1（只处理前 5 个视频）
python -c "
from workflow import CV_Pipeline
pipeline = CV_Pipeline(
    dataset_json_path='memories_ai_benchmark/long_mem_dataset.json',
    videos_base_dir='memories_ai_benchmark/videos'
)
clip_objs = pipeline.process_all_clips(max_clips=5)
print(f'处理完成: {len(clip_objs)} 个 Clip_Obj')
"
```

### 完整测试（所有视频）

```bash
# 运行完整流程（处理所有视频）
python workflow/integrate_all_phases.py
```

### 单阶段测试

每个阶段都有独立的测试脚本：

```bash
# Phase 0
python workflow/test_phase0.py

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

# Phase 6
python workflow/phase6_usr_retrieval/test_phase6.py
```

## 🐛 故障排除

### 问题 1: PostgreSQL 连接失败

**错误信息**:
```
psycopg2.OperationalError: could not connect to server
```

**解决方案**:
1. 检查 PostgreSQL 服务是否运行：
   ```bash
   # macOS
   brew services list | grep postgresql
   
   # Linux
   sudo systemctl status postgresql
   ```

2. 启动服务：
   ```bash
   # macOS
   brew services start postgresql@15
   
   # Linux
   sudo systemctl start postgresql
   ```

3. 检查端口是否正确（默认 5432）

### 问题 2: pgvector 扩展未找到

**错误信息**:
```
ERROR: extension "vector" does not exist
```

**解决方案**:
```bash
# macOS
brew install pgvector

# Linux
sudo apt-get install postgresql-15-pgvector

# 然后在数据库中启用
psql -U postgres -d neweufy -c "CREATE EXTENSION vector;"
```

### 问题 3: Google Cloud 认证失败

**错误信息**:
```
google.auth.exceptions.DefaultCredentialsError: Could not automatically determine credentials
```

**解决方案**:
1. 检查 Service Account 文件是否存在：
   ```bash
   ls -la gen-lang-sa.json
   ```

2. 检查环境变量：
   ```bash
   echo $GOOGLE_APPLICATION_CREDENTIALS
   ```

3. 确保文件路径正确（使用绝对路径或相对路径）

### 问题 4: 模型下载失败

**错误信息**:
```
FileNotFoundError: Model file not found
```

**解决方案**:
1. InsightFace 模型会自动下载，首次运行需要网络连接
2. YOLOv8 模型会自动下载
3. ReID 模型会自动下载

如果下载失败，可以手动下载：
- YOLOv8: https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt
- 放在项目根目录

### 问题 5: 内存不足

**错误信息**:
```
RuntimeError: CUDA out of memory
```

**解决方案**:
1. 减少批处理大小
2. 使用 CPU 模式（在代码中设置）
3. 处理更少的视频（使用 `max_clips` 参数）

### 问题 6: 视频文件找不到

**错误信息**:
```
FileNotFoundError: Video file not found
```

**解决方案**:
1. 检查 `memories_ai_benchmark/videos/` 目录是否存在
2. 检查 `long_mem_dataset.json` 中的路径是否正确
3. 确保视频文件已下载

## 📚 相关文档

### 核心文档
- `重要的模块/流程完整.md` - 完整流程说明
- `重要的模块/第一阶段.md` ~ `第六阶段.md` - 各阶段详细设计
- `重要的模块/sql方案.md` - 数据库设计方案

### 配置文档
- `database/README.md` - 数据库配置指南
- `重要的模块/gemini_setup.md` - Google Cloud / Gemini 配置
- `重要的模块/POSTGRESQL_SETUP.md` - PostgreSQL 详细配置

### 工作流文档
- `workflow/README.md` - Workflow 模块说明
- `workflow/phase1_cv_scanning/README.md` - Phase 1 使用文档
- `workflow/REID_SETUP.md` - ReID 模型配置

### UML 图
- `workflow/系统完整流程UML图.puml` - 系统架构 UML 图
- `workflow/系统流程序列图.puml` - 序列图
- `workflow/系统数据流向图.puml` - 数据流向图

## 💡 最佳实践

### 1. 环境管理
- 始终在虚拟环境中运行
- 使用 `setup_env.sh` 统一管理环境变量
- 不要将敏感信息（密码、密钥）提交到 Git

### 2. 数据库管理
- 定期备份数据库
- 使用 `clear_database.py` 清空测试数据
- 监控数据库大小和性能

### 3. 模型管理
- 首次运行会自动下载模型，需要网络连接
- 模型文件较大，确保有足够存储空间
- 可以缓存模型文件，避免重复下载

### 4. 性能优化
- 使用 GPU 加速（如果可用）
- 调整批处理大小
- 使用跟踪优化（Phase 1 中的 `enable_tracking=True`）

### 5. 错误处理
- 查看日志文件了解详细错误信息
- 使用测试脚本验证各阶段功能
- 分阶段运行，便于定位问题

## 🔄 更新和维护

### 更新依赖

```bash
# 激活虚拟环境
source venv/bin/activate

# 更新所有包
pip install --upgrade -r requirements.txt
```

### 更新数据库结构

如果数据库结构有更新：

```bash
# 备份数据库（重要！）
pg_dump -U postgres neweufy > backup.sql

# 运行更新脚本
python database/init_database.py
```

### 清理缓存

```bash
# 清理 Python 缓存
find . -type d -name __pycache__ -exec rm -r {} +
find . -type f -name "*.pyc" -delete

# 清理日志文件（如果有）
rm -f *.log
```

## 📞 获取帮助

如果遇到问题：

1. 查看相关文档
2. 检查日志输出
3. 运行测试脚本验证配置
4. 查看 GitHub Issues（如果有）

## 📝 许可证

[在此添加许可证信息]

---

**最后更新**: 2025年  
**版本**: v5.0  
**维护者**: [在此添加维护者信息]

