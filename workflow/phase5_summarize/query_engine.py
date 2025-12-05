"""
模块 1: 时间切片查询器 (Time-Slice Query Engine)
职责：从数据库中精准捞取特定日期的数据
"""

import os
import psycopg2
from typing import List, Dict, Any, Optional
from datetime import datetime, date
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class QueryEngine:
    """时间切片查询器"""
    
    def __init__(self, db_config: Optional[Dict[str, str]] = None):
        """
        初始化查询引擎
        
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
        
        logger.debug(f"✅ QueryEngine 初始化完成")
    
    def fetch_events(self, target_date: str) -> List[Dict[str, Any]]:
        """
        查询指定日期的所有事件
        
        Args:
            target_date: 目标日期，格式为 'YYYY-MM-DD' (如 '2025-09-01')
        
        Returns:
            事件列表，每个事件包含 id, start_time, end_time, camera_location, llm_description
        """
        conn = None
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            # 查询指定日期的事件（使用 DATE() 函数提取日期部分）
            query = """
                SELECT 
                    id,
                    start_time,
                    camera_location,
                    llm_description
                FROM event_logs
                WHERE DATE(start_time) = %s
                ORDER BY start_time ASC
            """
            
            cursor.execute(query, (target_date,))
            rows = cursor.fetchall()
            
            events = []
            for row in rows:
                events.append({
                    'id': row[0],
                    'start_time': row[1],
                    'camera_location': row[2],
                    'llm_description': row[3]
                })
            
            logger.info(f"📅 查询日期 {target_date}: 找到 {len(events)} 个事件")
            
            return events
            
        except psycopg2.Error as e:
            logger.error(f"❌ 数据库查询失败: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def get_distinct_dates(self) -> List[str]:
        """
        获取数据库中有事件的所有日期（去重）
        
        Returns:
            日期字符串列表，格式为 'YYYY-MM-DD'
        """
        conn = None
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            query = """
                SELECT DISTINCT DATE(start_time) as event_date
                FROM event_logs
                ORDER BY event_date ASC
            """
            
            cursor.execute(query)
            rows = cursor.fetchall()
            
            dates = [row[0].strftime('%Y-%m-%d') for row in rows]
            
            logger.info(f"📅 数据库中共有 {len(dates)} 个不同的日期")
            
            return dates
            
        except psycopg2.Error as e:
            logger.error(f"❌ 查询日期列表失败: {e}")
            raise
        finally:
            if conn:
                conn.close()

