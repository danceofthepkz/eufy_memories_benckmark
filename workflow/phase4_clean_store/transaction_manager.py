"""
模块 3 & 4: 事务管理器 (Transaction Manager) 和数据访问对象层 (DAO Layer)
职责：保证数据一致性 (ACID)，执行具体的 SQL 操作
"""

import os
import psycopg2
from psycopg2.extras import execute_values
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from contextlib import contextmanager
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def get_db_config() -> Dict[str, str]:
    """从环境变量获取数据库配置"""
    return {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': os.getenv('POSTGRES_PORT', '5432'),
        'database': os.getenv('POSTGRES_DB', 'neweufy'),
        'user': os.getenv('POSTGRES_USER', 'postgres'),
        'password': os.getenv('POSTGRES_PASSWORD', 'eufy123')
    }


class TransactionManager:
    """事务管理器"""
    
    def __init__(self, db_config: Optional[Dict[str, str]] = None):
        """
        初始化事务管理器
        
        Args:
            db_config: 数据库配置字典（如果为None，从环境变量读取）
        """
        self.db_config = db_config or get_db_config()
        self.conn = None
    
    @contextmanager
    def begin(self):
        """
        开启数据库事务的上下文管理器
        
        用法：
            with tx_manager.begin() as cursor:
                # 执行 SQL 操作
                cursor.execute(...)
            # 自动 commit（如果成功）或 rollback（如果异常）
        """
        conn = None
        cursor = None
        try:
            conn = psycopg2.connect(**self.db_config)
            conn.autocommit = False
            cursor = conn.cursor()
            
            logger.debug("🔵 开启数据库事务")
            yield cursor
            
            conn.commit()
            logger.debug("✅ 事务提交成功")
            
        except Exception as e:
            if conn:
                conn.rollback()
                logger.error(f"❌ 事务回滚: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
                logger.debug("🔵 数据库连接已关闭")


class EventDAO:
    """事件数据访问对象"""
    
    def __init__(self, tx_manager: TransactionManager):
        """
        初始化 EventDAO
        
        Args:
            tx_manager: 事务管理器
        """
        self.tx_manager = tx_manager
    
    def insert_event(self, cursor, global_event: Dict[str, Any], 
                    summary_text: str) -> uuid.UUID:
        """
        插入事件主表 (event_logs)
        
        Args:
            cursor: 数据库游标
            global_event: Global_Event 对象
            summary_text: LLM 生成的描述文本
        
        Returns:
            生成的事件 UUID
        """
        # 从 Global_Event 中提取信息
        start_time = global_event.get('start_time')
        cameras = global_event.get('cameras', [])
        
        # 选择第一个摄像头作为主要位置（或合并多个摄像头）
        camera_location = ', '.join(cameras) if cameras else 'unknown'
        
        # 从 clips 中提取视频文件名（如果有）
        video_filename = None
        clips = global_event.get('clips', [])
        if clips and 'video_path' in clips[0]:
            video_path = clips[0]['video_path']
            if video_path:
                # 提取文件名
                import os
                video_filename = os.path.basename(video_path)
        
        # 插入事件
        insert_sql = """
            INSERT INTO event_logs (
                video_filename,
                start_time,
                camera_location,
                llm_description
            ) VALUES (%s, %s, %s, %s)
            RETURNING id;
        """
        
        cursor.execute(insert_sql, (
            video_filename,
            start_time,
            camera_location,
            summary_text
        ))
        
        event_id = cursor.fetchone()[0]
        logger.info(f"✅ 插入事件主表: event_id={event_id}, "
                   f"时间={start_time}, 摄像头={camera_location}")
        
        return event_id


class AppearanceDAO:
    """人物出场快照数据访问对象"""
    
    def __init__(self, tx_manager: TransactionManager):
        """
        初始化 AppearanceDAO
        
        Args:
            tx_manager: 事务管理器
        """
        self.tx_manager = tx_manager
    
    def insert_appearance(self, cursor, event_id: uuid.UUID, 
                         person_id: int, match_method: str,
                         body_embedding_pgvector: str) -> int:
        """
        插入人物出场快照表 (event_appearances)
        
        Args:
            cursor: 数据库游标
            event_id: 事件 UUID
            person_id: 人物 ID
            match_method: 匹配方法 ('face', 'body_reid', 'new')
            body_embedding_pgvector: 身体特征向量（pgvector 格式字符串）
        
        Returns:
            插入的记录 ID
        """
        insert_sql = """
            INSERT INTO event_appearances (
                event_id,
                person_id,
                match_method,
                body_embedding
            ) VALUES (%s, %s, %s, %s::vector)
            RETURNING id;
        """
        
        cursor.execute(insert_sql, (
            event_id,
            person_id,
            match_method,
            body_embedding_pgvector
        ))
        
        appearance_id = cursor.fetchone()[0]
        logger.info(f"✅ 插入人物出场快照: appearance_id={appearance_id}, "
                   f"person_id={person_id}, method={match_method}")
        
        return appearance_id
    
    def batch_insert_appearances(self, cursor, appearances: List[Dict[str, Any]]) -> List[int]:
        """
        批量插入人物出场快照
        
        Args:
            cursor: 数据库游标
            appearances: 出场记录列表，每个记录包含：
                {
                    'event_id': uuid.UUID,
                    'person_id': int,
                    'match_method': str,
                    'body_embedding_pgvector': str
                }
        
        Returns:
            插入的记录 ID 列表
        """
        if not appearances:
            return []
        
        # 对于批量插入，我们需要使用单独的 INSERT 语句，因为 execute_values 不支持类型转换
        # 或者我们可以使用 CAST 函数
        insert_sql = """
            INSERT INTO event_appearances (
                event_id,
                person_id,
                match_method,
                body_embedding
            ) VALUES %s
            RETURNING id;
        """
        
        # 注意：execute_values 不支持类型转换，所以我们需要在 SQL 中使用 CAST
        # 但更好的方法是逐个插入，或者修改 SQL 使用 CAST
        # 这里我们改用逐个插入的方式，因为向量类型转换比较复杂
        appearance_ids = []
        for app in appearances:
            single_insert_sql = """
                INSERT INTO event_appearances (
                    event_id,
                    person_id,
                    match_method,
                    body_embedding
                ) VALUES (%s, %s, %s, %s::vector)
                RETURNING id;
            """
            cursor.execute(single_insert_sql, (
                app['event_id'],
                app['person_id'],
                app['match_method'],
                app['body_embedding_pgvector']
            ))
            appearance_ids.append(cursor.fetchone()[0])
        
        logger.info(f"✅ 批量插入 {len(appearance_ids)} 条人物出场快照")
        
        return appearance_ids

