"""
模块 5: 身份仲裁与缓存管理模块 (Identity Arbiter & Cache Manager)
职责：决定这个人是谁（最复杂的逻辑部分）
"""

import os
import psycopg2
import numpy as np
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()


class IdentityArbiter:
    """身份仲裁与缓存管理模块"""
    
    def __init__(self, 
                 face_threshold: float = 0.65,  # 提高阈值以减少误判（快递员等陌生人不应被误判为家人）
                 body_threshold: float = 0.60,  # 提高阈值以减少误判，但仍允许侧脸/背影匹配
                 soft_match_threshold: float = 0.55):  # 软匹配阈值（用于标记疑似家人）
        """
        初始化身份仲裁器
        
        Args:
            face_threshold: 人脸匹配阈值（余弦相似度），默认0.65（提高以减少误判）
            body_threshold: 身体匹配阈值（余弦相似度），默认0.60（提高以减少误判，但仍允许侧脸/背影匹配）
            soft_match_threshold: 软匹配阈值，默认0.55（用于标记疑似家人）
        """
        self.db_config = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': os.getenv('POSTGRES_PORT', '5432'),
            'database': os.getenv('POSTGRES_DB', 'neweufy'),
            'user': os.getenv('POSTGRES_USER', 'postgres'),
            'password': os.getenv('POSTGRES_PASSWORD', 'eufy123')
        }
        
        # 相似度阈值
        self.face_threshold = face_threshold
        self.body_threshold = body_threshold
        self.soft_match_threshold = soft_match_threshold  # 软匹配阈值
        
        logger.info(f"✅ 身份仲裁器初始化完成 (face_threshold={face_threshold}, body_threshold={body_threshold}, soft_match_threshold={soft_match_threshold})")
    
    def identify(self, vectors: Dict, timestamp: datetime) -> Dict:
        """
        识别身份
        
        Args:
            vectors: 特征包 {'face_vec': np.ndarray 或 None, 'body_vec': np.ndarray}
            timestamp: 当前时间戳
            
        Returns:
            身份信息: {
                'person_id': int,
                'role': 'family' | 'stranger' | 'suspected_family',
                'method': 'face' | 'body' | 'soft_match' | 'new',
                'confidence': float,  # 匹配置信度
                'body_embedding': np.ndarray  # 身体特征向量（如果存在）
            }
        """
        face_vec = vectors.get('face_vec')
        body_vec = vectors.get('body_vec')
        
        # 策略路由
        if face_vec is not None:
            # Face Match: 有脸 -> 搜底库 -> 成功则判定为家人
            result = self._match_by_face(face_vec, body_vec, timestamp)
            if result:
                return result
        
        # Body Match: 无脸 -> 搜 DB 缓存 (限制48小时内的 Owner) -> 成功则判定为家人
        if body_vec is not None:
            result = self._match_by_body(body_vec, timestamp)
            if result:
                return result
            
            # 软匹配：如果身体匹配失败，尝试更宽松的匹配
            soft_result = self._soft_match_by_body(body_vec, timestamp)
            if soft_result:
                return soft_result
        
        # No Match: 判定为 Stranger
        result = {
            'person_id': None,
            'role': 'stranger',
            'method': 'new',
            'confidence': 0.0
        }
        
        # 添加 body_embedding（如果存在，即使是陌生人也要保存）
        if body_vec is not None:
            result['body_embedding'] = body_vec
        
        return result
    
    def _match_by_face(self, face_vec: np.ndarray, body_vec: Optional[np.ndarray], 
                      timestamp: datetime) -> Optional[Dict]:
        """
        通过人脸匹配身份
        
        Args:
            face_vec: 人脸特征向量 (512维)
            body_vec: 身体特征向量 (2048维) 或 None
            timestamp: 当前时间戳
            
        Returns:
            身份信息或 None
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            # 在 person_faces 表中搜索最相似的人脸
            # 使用余弦相似度搜索
            face_vec_str = '[' + ','.join(map(str, face_vec)) + ']'
            
            cur.execute("""
                SELECT 
                    pf.person_id,
                    p.name,
                    p.role,
                    1 - (pf.embedding <=> %s::vector) as similarity
                FROM person_faces pf
                JOIN persons p ON pf.person_id = p.id
                WHERE 1 - (pf.embedding <=> %s::vector) > %s
                ORDER BY pf.embedding <=> %s::vector
                LIMIT 1
            """, (face_vec_str, face_vec_str, self.face_threshold, face_vec_str))
            
            result = cur.fetchone()
            
            if result:
                person_id, name, role, similarity = result
                
                # 【关键】立即更新该 ID 在 DB 中的 current_body_embedding
                if body_vec is not None:
                    self._update_body_cache(person_id, body_vec, timestamp, cur)
                    conn.commit()
                
                logger.info(f"✅ 人脸匹配成功: {name} (ID: {person_id}, 相似度: {similarity:.3f})")
                
                cur.close()
                conn.close()
                
                result = {
                    'person_id': person_id,
                    'role': 'family' if role == 'owner' else role,
                    'method': 'face',
                    'confidence': float(similarity)
                }
                
                # 添加 body_embedding（如果存在）
                if body_vec is not None:
                    result['body_embedding'] = body_vec
                
                return result
            
            cur.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ 人脸匹配失败: {e}")
        
        return None
    
    def _match_by_body(self, body_vec: np.ndarray, timestamp: datetime) -> Optional[Dict]:
        """
        通过身体特征匹配身份（支持侧脸/背影场景）
        
        Args:
            body_vec: 身体特征向量 (2048维)
            timestamp: 当前时间戳
            
        Returns:
            身份信息或 None
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            # 搜索48小时内的 Owner 的 current_body_embedding（延长时间窗口）
            time_limit = timestamp - timedelta(hours=48)
            
            body_vec_str = '[' + ','.join(map(str, body_vec)) + ']'
            
            # 首先尝试匹配有缓存的（最近48小时内的）
            cur.execute("""
                SELECT 
                    id,
                    name,
                    role,
                    1 - (current_body_embedding <=> %s::vector) as similarity
                FROM persons
                WHERE role = 'owner'
                  AND current_body_embedding IS NOT NULL
                  AND body_update_time >= %s
                  AND 1 - (current_body_embedding <=> %s::vector) > %s
                ORDER BY current_body_embedding <=> %s::vector
                LIMIT 1
            """, (body_vec_str, time_limit, body_vec_str, self.body_threshold, body_vec_str))
            
            result = cur.fetchone()
            
            if result:
                person_id, name, role, similarity = result
                
                # 更新缓存时间（即使匹配成功也更新，保持活跃）
                self._update_body_cache(person_id, body_vec, timestamp, cur)
                conn.commit()
                
                logger.info(f"✅ 身体匹配成功: {name} (ID: {person_id}, 相似度: {similarity:.3f})")
                
                cur.close()
                conn.close()
                
                return {
                    'person_id': person_id,
                    'role': 'family',
                    'method': 'body',
                    'confidence': float(similarity),
                    'body_embedding': body_vec
                }
            
            cur.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ 身体匹配失败: {e}")
        
        return None
    
    def _soft_match_by_body(self, body_vec: np.ndarray, timestamp: datetime) -> Optional[Dict]:
        """
        软匹配：使用更宽松的阈值匹配身体特征（标记为疑似家人）
        这用于处理低辨识度的情况，后续在事件级别可以进一步确认
        
        Args:
            body_vec: 身体特征向量 (2048维)
            timestamp: 当前时间戳
            
        Returns:
            身份信息或 None（如果找到软匹配）
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            # 搜索48小时内的 Owner 的 current_body_embedding
            time_limit = timestamp - timedelta(hours=48)
            
            body_vec_str = '[' + ','.join(map(str, body_vec)) + ']'
            
            # 使用软匹配阈值（更宽松）
            cur.execute("""
                SELECT 
                    id,
                    name,
                    role,
                    1 - (current_body_embedding <=> %s::vector) as similarity
                FROM persons
                WHERE role = 'owner'
                  AND current_body_embedding IS NOT NULL
                  AND body_update_time >= %s
                  AND 1 - (current_body_embedding <=> %s::vector) > %s
                  AND 1 - (current_body_embedding <=> %s::vector) <= %s
                ORDER BY current_body_embedding <=> %s::vector
                LIMIT 1
            """, (body_vec_str, time_limit, body_vec_str, self.soft_match_threshold, 
                  body_vec_str, self.body_threshold, body_vec_str))
            
            result = cur.fetchone()
            
            if result:
                person_id, name, role, similarity = result
                
                logger.info(f"⚠️  软匹配（疑似家人）: {name} (ID: {person_id}, 相似度: {similarity:.3f})")
                
                cur.close()
                conn.close()
                
                return {
                    'person_id': person_id,
                    'role': 'suspected_family',  # 标记为疑似家人
                    'method': 'soft_match',
                    'confidence': float(similarity),
                    'body_embedding': body_vec
                }
            
            cur.close()
            conn.close()
            
        except Exception as e:
            logger.debug(f"软匹配失败: {e}")
        
        return None
    
    def _update_body_cache(self, person_id: int, body_vec: np.ndarray, 
                           timestamp: datetime, cursor):
        """
        更新数据库中人物的 current_body_embedding 缓存
        
        Args:
            person_id: 人物ID
            body_vec: 身体特征向量
            timestamp: 当前时间戳
            cursor: 数据库游标
        """
        try:
            body_vec_str = '[' + ','.join(map(str, body_vec)) + ']'
            
            cursor.execute("""
                UPDATE persons
                SET current_body_embedding = %s::vector,
                    body_update_time = %s,
                    last_seen = %s
                WHERE id = %s
            """, (body_vec_str, timestamp, timestamp, person_id))
            
            logger.debug(f"✅ 更新身体缓存: Person ID {person_id}")
            
        except Exception as e:
            logger.error(f"❌ 更新身体缓存失败: {e}")
            raise
