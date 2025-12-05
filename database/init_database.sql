-- ============================================
-- 家庭智能安防系统数据库初始化脚本
-- 基于 sql方案.md 设计
-- ============================================

-- 0. 启用向量扩展插件 (必须)
CREATE EXTENSION IF NOT EXISTS vector;

-- 1. 身份档案表 (persons)
-- 存储人物的唯一标识和全局状态
CREATE TABLE IF NOT EXISTS persons (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,       -- 显示名称: "Dad", "Stranger_20250901"
    role VARCHAR(20) NOT NULL,        -- 角色类型: 'owner' (家人), 'visitor' (访客), 'unknown' (陌生人)
    
    -- [ReID 缓存字段] 
    -- 记录该人"最后一次出现时"的全身特征。
    -- 用于在只有背影时，快速与最近出现的熟人进行比对。
    current_body_embedding vector(2048), 
    body_update_time TIMESTAMP,
    
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT                        -- 备注: "红衣男子", "快递员"
);

-- 索引: 加快按角色查询速度
CREATE INDEX IF NOT EXISTS idx_persons_role ON persons(role);

-- 2. 人脸底库表 (person_faces)
-- 存储家人的多张人脸底库照片（从 lib/ 导入）
CREATE TABLE IF NOT EXISTS person_faces (
    id SERIAL PRIMARY KEY,
    person_id INTEGER REFERENCES persons(id) ON DELETE CASCADE,
    
    embedding vector(512),            -- 人脸特征向量 (假设 ArcFace 512维)
    source_image VARCHAR(200),        -- 来源图片路径: "lib/1.jpeg"
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引: 加快人脸向量搜索 (HNSW 索引)
CREATE INDEX IF NOT EXISTS idx_person_faces_embedding 
    ON person_faces USING hnsw (embedding vector_cosine_ops);

-- 3. 事件主表 (event_logs)
-- 记录视频片段的元数据和宏观描述。注意：这里不存具体的 vector，只存故事。
CREATE TABLE IF NOT EXISTS event_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    video_filename VARCHAR(100),      -- 视频文件名: "1.mp4"
    start_time TIMESTAMP NOT NULL,    -- 事件发生时间 (来自 JSON)
    camera_location VARCHAR(50),       -- 语义化地点: "Front Door", "Driveway"
    
    -- LLM 生成的完整描述
    -- 例: "09:00，家人(ID:1)与一名陌生人在门口交谈。"
    llm_description TEXT,             
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引: 加快按时间范围查询 (比如查询9月份的所有录像)
CREATE INDEX IF NOT EXISTS idx_event_time ON event_logs(start_time);
CREATE INDEX IF NOT EXISTS idx_event_camera ON event_logs(camera_location);

-- 4. [核心] 人物出场快照表 (event_appearances)
-- 解决"多目标同框"的关键表。如果一个视频里有 3 个人，event_logs 只有 1 行，但这张表会有 3 行记录。
CREATE TABLE IF NOT EXISTS event_appearances (
    id SERIAL PRIMARY KEY,
    
    event_id UUID REFERENCES event_logs(id) ON DELETE CASCADE, -- 关联主事件
    person_id INTEGER REFERENCES persons(id),                  -- 关联具体的人
    
    -- 识别方式: 
    -- 'face' (正脸确认), 'body_reid' (背影推断), 'new' (陌生人)
    match_method VARCHAR(20),       
    
    -- [最重要的字段] 本次出场时的全身特征
    -- 即使这个人是家人，我们也要存下他这次穿的衣服
    -- 这样以后搜"红衣服"，才能搜到这一条记录
    body_embedding vector(2048),    
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引: 加快衣着向量搜索 (支持以图搜人)
-- 注意: 对于 2048 维向量，使用 ivfflat 而不是 hnsw（hnsw 最多支持 2000 维）
-- 注意: ivfflat 索引需要在有数据后创建，这里先注释掉，稍后手动创建
-- CREATE INDEX IF NOT EXISTS idx_event_appearances_body_embedding 
--     ON event_appearances USING ivfflat (body_embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_event_appearances_event_id ON event_appearances(event_id);
CREATE INDEX IF NOT EXISTS idx_event_appearances_person_id ON event_appearances(person_id);

-- 5. 每日总结表 (daily_summaries)
-- 存储 Gemini 对全天数据的宏观分析
CREATE TABLE IF NOT EXISTS daily_summaries (
    id SERIAL PRIMARY KEY,
    summary_date DATE UNIQUE NOT NULL, -- 日期: 2025-09-01
    summary_text TEXT,                 -- 全天总结
    total_events INTEGER,              -- 当天事件总数
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引: 加快按日期查询
CREATE INDEX IF NOT EXISTS idx_daily_summaries_date ON daily_summaries(summary_date);

-- ============================================
-- 验证脚本
-- ============================================

-- 检查扩展是否安装
SELECT * FROM pg_extension WHERE extname = 'vector';

-- 显示所有表
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

