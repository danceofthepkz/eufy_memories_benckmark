"""
模块 1: 语义查询解析器 (Semantic Query Parser / NLU)
职责：将用户的自然语言问题转化为结构化的 SQL 查询条件
"""

import re
import os
import psycopg2
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class QueryParser:
    """语义查询解析器"""
    
    def __init__(self, db_config: Optional[Dict[str, str]] = None):
        """
        初始化查询解析器
        
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
        
        # 人物名称映射（中文 -> 可能的数据库名称）
        # 注意：实际数据库中可能存储的是 "Family_1", "Family_2" 等
        # 这里提供关键词映射，实际查询时会尝试匹配
        self.person_keywords = {
            'Family_1': ['爸爸', '爸', 'father', 'dad', 'person_21', 'person21'],
            'Family_2': ['妈妈', '妈', 'mother', 'mom', 'person_22', 'person22'],
            'family': ['家人', '家庭成员', 'family'],
        }
        
        # 动作关键词映射
        self.action_keywords = {
            '回家': ['回家', '回来', '返回', '到家', '进门'],
            '出门': ['出门', '出去', '离开', '外出'],
            '出现': ['出现', '看到', '检测到'],
        }
        
        # 意图类型
        self.intent_types = {
            'describe_appearance': ['穿什么', '穿', '衣服', '衣着', '穿着', '打扮'],
            'query_time': ['什么时候', '几点', '何时', '时间'],
            'query_location': ['在哪里', '哪个位置', '什么地方', '位置'],
            'query_summary': ['总结', '概况', '大概', '规律'],
        }
        
        logger.debug("✅ QueryParser 初始化完成")
    
    def parse(self, user_query: str) -> Dict[str, Any]:
        """
        解析用户查询
        
        Args:
            user_query: 用户的自然语言问题
        
        Returns:
            查询对象: {
                'person_id': Optional[int],
                'person_name': Optional[str],
                'date': Optional[str],  # 'YYYY-MM-DD'
                'date_range': Optional[tuple],  # (start_date, end_date)
                'keyword': Optional[str],  # 动作关键词
                'intent': str,  # 意图类型
                'query_type': str,  # 'detail' 或 'summary'
            }
        """
        logger.info(f"🔍 解析用户查询: {user_query}")
        
        query_obj = {
            'person_id': None,
            'person_name': None,
            'date': None,
            'date_range': None,
            'keyword': None,
            'intent': 'general',
            'query_type': 'detail'  # 默认查询详细事件
        }
        
        # 1. 提取人物信息
        person_info = self._extract_person(user_query)
        if person_info:
            query_obj['person_id'] = person_info.get('person_id')
            query_obj['person_name'] = person_info.get('person_name')
        
        # 2. 提取时间信息
        date_info = self._extract_date(user_query)
        if date_info:
            if isinstance(date_info, tuple):
                query_obj['date_range'] = date_info
            else:
                query_obj['date'] = date_info
        
        # 3. 提取动作关键词
        keyword = self._extract_keyword(user_query)
        if keyword:
            query_obj['keyword'] = keyword
        
        # 4. 识别意图
        intent = self._detect_intent(user_query)
        query_obj['intent'] = intent
        
        # 5. 判断查询类型（详细 vs 总结）
        if intent == 'query_summary' or '总结' in user_query or '概况' in user_query:
            query_obj['query_type'] = 'summary'
        
        logger.info(f"✅ 查询解析完成: {query_obj}")
        
        return query_obj
    
    def _extract_person(self, query: str) -> Optional[Dict[str, Any]]:
        """
        提取人物信息
        
        Args:
            query: 用户查询
        
        Returns:
            {'person_id': int, 'person_name': str} 或 None
        """
        # 1. 尝试从关键词匹配（中文 -> 数据库名称）
        for db_name, keywords in self.person_keywords.items():
            if any(kw in query for kw in keywords):
                # 查询数据库获取 person_id
                person_id = self._get_person_id_by_name(db_name)
                if person_id:
                    # 获取实际的人物名称
                    actual_name = self._get_person_name_by_id(person_id)
                    return {
                        'person_id': person_id, 
                        'person_name': actual_name or db_name
                    }
        
        # 2. 尝试直接匹配 Person_ID（如 "Person_21", "Person21"）
        person_id_match = re.search(r'Person[_\s]*(\d+)', query, re.IGNORECASE)
        if person_id_match:
            person_id = int(person_id_match.group(1))
            person_name = self._get_person_name_by_id(person_id)
            if person_name:
                return {'person_id': person_id, 'person_name': person_name}
        
        # 3. 尝试在数据库中模糊搜索（如果查询中包含中文名称）
        # 例如：查询 "爸爸" 时，搜索 notes 字段包含 "爸爸" 的记录
        for db_name, keywords in self.person_keywords.items():
            if any(kw in query for kw in keywords[:2]):  # 只使用前2个关键词（中文）
                person_id = self._search_person_by_keywords(keywords[:2])
                if person_id:
                    actual_name = self._get_person_name_by_id(person_id)
                    return {
                        'person_id': person_id,
                        'person_name': actual_name or db_name
                    }
        
        return None
    
    def _search_person_by_keywords(self, keywords: List[str]) -> Optional[int]:
        """
        通过关键词在数据库中搜索人物
        
        Args:
            keywords: 关键词列表
        
        Returns:
            person_id 或 None
        """
        conn = None
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            # 在 name 或 notes 字段中搜索
            conditions = []
            params = []
            for keyword in keywords:
                conditions.append("(name ILIKE %s OR notes ILIKE %s)")
                params.extend([f'%{keyword}%', f'%{keyword}%'])
            
            where_clause = " OR ".join(conditions)
            
            cursor.execute(f"""
                SELECT id FROM persons
                WHERE role = 'owner' AND ({where_clause})
                LIMIT 1
            """, params)
            
            result = cursor.fetchone()
            if result:
                return result[0]
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.debug(f"关键词搜索失败: {e}")
        finally:
            if conn:
                conn.close()
        
        return None
    
    def _extract_date(self, query: str) -> Optional[str]:
        """
        提取日期信息
        
        Args:
            query: 用户查询
        
        Returns:
            日期字符串 'YYYY-MM-DD' 或日期范围元组 (start_date, end_date)
        """
        current_year = datetime.now().year
        
        # 匹配 "9月1日"、"9月1号"、"2025-09-01" 等格式
        patterns = [
            (r'(\d{4})[年\-/](\d{1,2})[月\-/](\d{1,2})[日号]?', True),  # 2025年9月1日（有年份）
            (r'(\d{1,2})[月\-/](\d{1,2})[日号]', False),  # 9月1日（无年份，使用当前年份）
            (r'(\d{4})-(\d{2})-(\d{2})', True),  # 2025-09-01
        ]
        
        for pattern, has_year in patterns:
            match = re.search(pattern, query)
            if match:
                groups = match.groups()
                if has_year and len(groups) == 3:
                    # 有年份的格式
                    year, month, day = groups
                    try:
                        date_str = f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
                        return date_str
                    except ValueError:
                        continue
                elif not has_year and len(groups) == 2:
                    # 无年份的格式（如"9月1日"），使用当前年份
                    month, day = groups
                    try:
                        date_str = f"{current_year:04d}-{int(month):02d}-{int(day):02d}"
                        return date_str
                    except ValueError:
                        continue
        
        # 匹配相对时间："今天"、"昨天"、"前天"
        if '今天' in query or '今日' in query:
            return datetime.now().strftime('%Y-%m-%d')
        elif '昨天' in query or '昨日' in query:
            return (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        elif '前天' in query:
            return (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
        
        return None
    
    def _extract_keyword(self, query: str) -> Optional[str]:
        """
        提取动作关键词
        
        Args:
            query: 用户查询
        
        Returns:
            关键词字符串或 None
        """
        for action, keywords in self.action_keywords.items():
            if any(kw in query for kw in keywords):
                return action
        
        return None
    
    def _detect_intent(self, query: str) -> str:
        """
        检测用户意图
        
        Args:
            query: 用户查询
        
        Returns:
            意图类型字符串
        """
        for intent, keywords in self.intent_types.items():
            if any(kw in query for kw in keywords):
                return intent
        
        return 'general'
    
    def _get_person_id_by_name(self, name: str) -> Optional[int]:
        """
        通过名称查询 person_id
        
        Args:
            name: 人物名称
        
        Returns:
            person_id 或 None
        """
        conn = None
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            # 查询 persons 表
            # 注意：这里假设 name 字段存储的是类似 "Dad", "Mom" 等
            # 如果存储的是中文，需要调整查询逻辑
            cursor.execute("""
                SELECT id FROM persons
                WHERE name ILIKE %s OR notes ILIKE %s
                LIMIT 1
            """, (f'%{name}%', f'%{name}%'))
            
            result = cursor.fetchone()
            if result:
                return result[0]
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ 查询人物ID失败: {e}")
        finally:
            if conn:
                conn.close()
        
        return None
    
    def _get_person_name_by_id(self, person_id: int) -> Optional[str]:
        """
        通过 person_id 查询人物名称
        
        Args:
            person_id: 人物ID
        
        Returns:
            人物名称或 None
        """
        conn = None
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT name FROM persons WHERE id = %s
            """, (person_id,))
            
            result = cursor.fetchone()
            if result:
                return result[0]
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ 查询人物名称失败: {e}")
        finally:
            if conn:
                conn.close()
        
        return None

