"""
模块 2: 混合检索引擎 (Hybrid Retrieval Engine)
职责：执行 SQL 逻辑，联合多张表查找证据
"""

import os
import psycopg2
import numpy as np
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class RetrievalEngine:
    """混合检索引擎"""
    
    def __init__(self, db_config: Optional[Dict[str, str]] = None):
        """
        初始化检索引擎
        
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
        
        logger.debug("✅ RetrievalEngine 初始化完成")
    
    def retrieve(self, query_obj: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        根据查询对象检索数据
        
        Args:
            query_obj: 查询对象（来自 QueryParser）
        
        Returns:
            检索结果列表，每个结果包含事件信息和人物出场信息
        """
        query_type = query_obj.get('query_type', 'detail')
        
        if query_type == 'summary':
            # 查询每日总结
            return self._retrieve_summary(query_obj)
        else:
            # 查询详细事件
            return self._retrieve_detail(query_obj)
    
    def _retrieve_summary(self, query_obj: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        检索每日总结
        
        Args:
            query_obj: 查询对象
        
        Returns:
            总结记录列表
        """
        conn = None
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            date = query_obj.get('date')
            date_range = query_obj.get('date_range')
            
            if date_range:
                start_date, end_date = date_range
                cursor.execute("""
                    SELECT id, summary_date, summary_text, total_events, created_at, updated_at
                    FROM daily_summaries
                    WHERE summary_date BETWEEN %s AND %s
                    ORDER BY summary_date DESC
                """, (start_date, end_date))
            elif date:
                cursor.execute("""
                    SELECT id, summary_date, summary_text, total_events, created_at, updated_at
                    FROM daily_summaries
                    WHERE summary_date = %s
                """, (date,))
            else:
                # 如果没有指定日期，返回最近的总结
                cursor.execute("""
                    SELECT id, summary_date, summary_text, total_events, created_at, updated_at
                    FROM daily_summaries
                    ORDER BY summary_date DESC
                    LIMIT 10
                """)
            
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                results.append({
                    'type': 'summary',
                    'summary_id': row[0],
                    'summary_date': row[1],
                    'summary_text': row[2],
                    'total_events': row[3],
                    'created_at': row[4],
                    'updated_at': row[5]
                })
            
            logger.info(f"✅ 检索到 {len(results)} 条总结记录")
            
            cursor.close()
            conn.close()
            
            return results
            
        except Exception as e:
            logger.error(f"❌ 检索总结失败: {e}")
            if conn:
                conn.close()
            return []
    
    def _retrieve_detail(self, query_obj: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        检索详细事件
        
        Args:
            query_obj: 查询对象
        
        Returns:
            事件记录列表，包含事件信息和人物出场信息
        """
        conn = None
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            # 构建 SQL 查询
            conditions = []
            params = []
            
            # 时间条件
            date = query_obj.get('date')
            date_range = query_obj.get('date_range')
            
            if date_range:
                start_date, end_date = date_range
                conditions.append("DATE(el.start_time) BETWEEN %s AND %s")
                params.extend([start_date, end_date])
            elif date:
                conditions.append("DATE(el.start_time) = %s")
                params.append(date)
            
            # 人物条件
            person_id = query_obj.get('person_id')
            if person_id:
                conditions.append("ea.person_id = %s")
                params.append(person_id)
            
            # 关键词条件（在 llm_description 中搜索）
            # 注意：如果关键词匹配不到结果，会在后续放宽条件
            keyword = query_obj.get('keyword')
            keyword_condition = None
            if keyword:
                keyword_condition = "el.llm_description ILIKE %s"
                keyword_param = f'%{keyword}%'
            
            # 首先尝试带关键词的查询
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            if keyword_condition:
                where_clause_with_keyword = f"{where_clause} AND {keyword_condition}"
                params_with_keyword = params + [keyword_param]
            else:
                where_clause_with_keyword = where_clause
                params_with_keyword = params
            
            sql = f"""
                SELECT DISTINCT
                    el.id as event_id,
                    el.start_time,
                    el.camera_location,
                    el.llm_description,
                    el.video_filename,
                    ea.id as appearance_id,
                    ea.person_id,
                    ea.match_method,
                    ea.body_embedding,
                    p.name as person_name,
                    p.role as person_role
                FROM event_logs el
                JOIN event_appearances ea ON el.id = ea.event_id
                LEFT JOIN persons p ON ea.person_id = p.id
                WHERE {where_clause_with_keyword}
                ORDER BY el.start_time DESC
                LIMIT 50
            """
            
            cursor.execute(sql, params_with_keyword)
            rows = cursor.fetchall()
            
            # 如果带关键词的查询结果为空，且有关键词，尝试不带关键词的查询
            if len(rows) == 0 and keyword_condition:
                logger.info(f"⚠️  关键词 '{keyword}' 未匹配到结果，放宽条件重新查询...")
                sql = f"""
                    SELECT DISTINCT
                        el.id as event_id,
                        el.start_time,
                        el.camera_location,
                        el.llm_description,
                        el.video_filename,
                        ea.id as appearance_id,
                        ea.person_id,
                        ea.match_method,
                        ea.body_embedding,
                        p.name as person_name,
                        p.role as person_role
                    FROM event_logs el
                    JOIN event_appearances ea ON el.id = ea.event_id
                    LEFT JOIN persons p ON ea.person_id = p.id
                    WHERE {where_clause}
                    ORDER BY el.start_time DESC
                    LIMIT 50
                """
                cursor.execute(sql, params)
                rows = cursor.fetchall()
            
            # 按事件分组
            events_dict = {}
            for row in rows:
                event_id = row[0]
                
                if event_id not in events_dict:
                    events_dict[event_id] = {
                        'type': 'detail',
                        'event_id': event_id,
                        'start_time': row[1],
                        'camera_location': row[2],
                        'llm_description': row[3],
                        'video_filename': row[4],
                        'appearances': []
                    }
                
                # 添加人物出场信息
                if row[5]:  # appearance_id
                    appearance = {
                        'appearance_id': row[5],
                        'person_id': row[6],
                        'match_method': row[7],
                        'body_embedding': row[8],  # pgvector 字符串格式
                        'person_name': row[9],
                        'person_role': row[10]
                    }
                    events_dict[event_id]['appearances'].append(appearance)
            
            results = list(events_dict.values())
            
            logger.info(f"✅ 检索到 {len(results)} 个事件，共 {sum(len(e['appearances']) for e in results)} 条出场记录")
            
            cursor.close()
            conn.close()
            
            return results
            
        except Exception as e:
            logger.error(f"❌ 检索详细事件失败: {e}")
            import traceback
            traceback.print_exc()
            if conn:
                conn.close()
            return []

