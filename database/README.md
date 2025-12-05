# 数据库配置指南

## 📋 概述

本项目使用 **PostgreSQL + pgvector** 作为数据库，根据 `sql方案.md` 设计。

## 🔧 安装步骤

### 1. 安装 PostgreSQL

**macOS (使用 Homebrew):**
```bash
brew install postgresql@15
brew services start postgresql@15
```

**验证安装:**
```bash
psql --version
```

### 2. 安装 pgvector 扩展

**macOS (使用 Homebrew):**
```bash
brew install pgvector
```

**从源码编译:**
```bash
git clone --branch v0.5.1 https://github.com/pgvector/pgvector.git
cd pgvector
make
make install
```

### 3. 配置数据库连接

创建 `.env` 文件（在项目根目录）或修改 `setup_env.sh`：

```bash
# PostgreSQL 配置
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=eufy_memories
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=your_password_here
```

### 4. 初始化数据库

**方式 1: 使用 Python 脚本（推荐）**

```bash
# 激活虚拟环境
source venv/bin/activate

# 设置环境变量
source setup_env.sh

# 运行初始化脚本
python database/init_database.py
```

**方式 2: 手动执行 SQL**

```bash
# 连接到 PostgreSQL
psql -U postgres

# 创建数据库
CREATE DATABASE eufy_memories;

# 连接到新数据库
\c eufy_memories

# 执行 SQL 脚本
\i database/init_database.sql
```

## 📊 数据库表结构

根据 `sql方案.md`，系统包含以下 5 个核心表：

1. **persons** - 身份档案表
   - 存储人物的唯一标识和全局状态
   - 包含 ReID 缓存字段 `current_body_embedding`

2. **person_faces** - 人脸底库表
   - 存储家人的多张人脸底库照片
   - 使用 HNSW 索引加速人脸向量搜索

3. **event_logs** - 事件主表
   - 记录视频片段的元数据和 LLM 生成的描述
   - 不存储向量，只存储故事

4. **event_appearances** - 人物出场快照表（核心表）
   - 解决"多目标同框"问题
   - 每个视频中的每个人都有独立记录
   - 存储每次出场的全身特征向量

5. **daily_summaries** - 每日总结表
   - 存储 Gemini 对全天数据的宏观分析

## 🔍 验证安装

运行验证脚本：

```bash
python database/init_database.py
```

如果成功，您应该看到：
- ✅ 数据库创建成功
- ✅ 所有表创建成功
- ✅ pgvector 扩展已启用

## 🐛 故障排除

### 错误 1: psql: command not found

**解决方案:**
- 确保 PostgreSQL 已安装
- 检查 PATH 环境变量
- macOS: `brew install postgresql@15`

### 错误 2: extension "vector" does not exist

**解决方案:**
```bash
# 安装 pgvector
brew install pgvector

# 或在数据库中手动创建
psql -U postgres -d eufy_memories -c "CREATE EXTENSION vector;"
```

### 错误 3: 连接被拒绝

**解决方案:**
- 检查 PostgreSQL 服务是否运行: `brew services list`
- 检查端口是否正确（默认 5432）
- 检查防火墙设置

### 错误 4: 认证失败

**解决方案:**
- 检查用户名和密码
- 检查 PostgreSQL 的 `pg_hba.conf` 配置
- 可能需要重置密码: `ALTER USER postgres PASSWORD 'new_password';`

## 📚 相关文档

- [sql方案.md](../sql方案.md) - 完整的数据库设计方案
- [POSTGRESQL_SETUP.md](../POSTGRESQL_SETUP.md) - PostgreSQL 详细配置说明

