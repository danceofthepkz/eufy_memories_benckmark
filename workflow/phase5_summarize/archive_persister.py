"""
模块 4: 归档持久化器 (Archive Persister)
职责：将总结写入数据库，支持幂等写入（UPSERT）
"""

import os
import psycopg2
from psycopg2.extras import execute_values
from typing import Dict, Any, Optional
from datetime import datetime
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class ArchivePersister:
    """归档持久化器"""
    
    def __init__(self, db_config: Optional[Dict[str, str]] = None):
        """
        初始化持久化器
        
        Args:
            db_config: 数据库连接配置。如果为None，则从环境变量加载。
        """
        if db_config is None:
            self.db_config = {
                'host': os.getenv('POSTGRES_HOST', 'localhost'),
                'port': os.getenv('POSTGRES_PORT', '5432'),
                'database': os.getenv('POSTGRES_DB', 'neweufy'),
                'user': os.getenv('POSTGRES_USER', 'postgres'),
                'password': os.getenv('POSTGRES_PASSWORD', 'eufy123')
            }
        else:
            self.db_config = db_config
        
        logger.debug("✅ ArchivePersister 初始化完成")
    
    def save(self, summary_date: str, summary_text: str, total_events: int) -> int:
        """
        保存每日总结到数据库（幂等写入：如果已存在则更新）
        
        Args:
            summary_date: 总结日期，格式为 'YYYY-MM-DD'
            summary_text: 总结文本
            total_events: 当天事件总数
        
        Returns:
            插入或更新的记录ID
        """
        conn = None
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            # 使用 UPSERT (INSERT ... ON CONFLICT DO UPDATE)
            # 确保同一天只有一条最新的总结
            upsert_sql = """
                INSERT INTO daily_summaries (
                    summary_date,
                    summary_text,
                    total_events,
                    created_at,
                    updated_at
                ) VALUES (%s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT (summary_date) 
                DO UPDATE SET
                    summary_text = EXCLUDED.summary_text,
                    total_events = EXCLUDED.total_events,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id;
            """
            
            cursor.execute(upsert_sql, (summary_date, summary_text, total_events))
            record_id = cursor.fetchone()[0]
            
            conn.commit()
            
            logger.info(f"✅ 每日总结已保存: date={summary_date}, id={record_id}, events={total_events}")
            
            return record_id
            
        except psycopg2.Error as e:
            if conn:
                conn.rollback()
            logger.error(f"❌ 保存每日总结失败: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def get_summary(self, summary_date: str) -> Optional[Dict[str, Any]]:
        """
        查询指定日期的总结（如果存在）
        
        Args:
            summary_date: 总结日期，格式为 'YYYY-MM-DD'
        
        Returns:
            总结字典（如果存在），否则返回 None
        """
        conn = None
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            query = """
                SELECT id, summary_date, summary_text, total_events, created_at, updated_at
                FROM daily_summaries
                WHERE summary_date = %s
            """
            
            cursor.execute(query, (summary_date,))
            row = cursor.fetchone()
            
            if row:
                return {
                    'id': row[0],
                    'summary_date': row[1],
                    'summary_text': row[2],
                    'total_events': row[3],
                    'created_at': row[4],
                    'updated_at': row[5]
                }
            else:
                return None
                
        except psycopg2.Error as e:
            logger.error(f"❌ 查询每日总结失败: {e}")
            raise
        finally:
            if conn:
                conn.close()

