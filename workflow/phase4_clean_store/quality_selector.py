"""
模块 1: 质量评估与优选器 (Quality Assessor & Selector)
职责：从多次检测中选出最具代表性的一张作为"定妆照"
"""

from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class QualitySelector:
    """质量评估与优选器"""
    
    def __init__(self):
        """初始化优选器"""
        pass
    
    def select_best(self, detection_list: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        从多次检测中选出最具代表性的一次
        
        评分策略：
        1. 分辨率优先：边界框 (bbox) 面积最大的
        2. 置信度优先：Face Score 或 ReID Confidence 最高的
        3. 居中优先：人物位于画面中心，未被遮挡的
        4. 方法优先：正脸确认 (face) > 身体匹配 (body) > 新检测 (new)
        
        Args:
            detection_list: 一个人的多次检测记录列表
                每个检测记录包含：
                {
                    'person_id': int,
                    'role': str,
                    'method': str,  # 'face', 'body', 'new'
                    'confidence': float,
                    'bbox': (x1, y1, x2, y2),
                    'body_embedding': np.ndarray,  # 2048维
                    'face_embedding': Optional[np.ndarray],  # 512维（如果有）
                    ...
                }
        
        Returns:
            最具代表性的检测记录，如果没有检测则返回 None
        """
        if not detection_list:
            logger.warning("⚠️  检测列表为空")
            return None
        
        if len(detection_list) == 1:
            logger.debug("   只有一次检测，直接返回")
            return detection_list[0]
        
        logger.debug(f"   从 {len(detection_list)} 次检测中选择最佳...")
        
        # 计算每个检测的评分
        scored_detections = []
        for idx, det in enumerate(detection_list):
            score = self._calculate_score(det)
            scored_detections.append((score, idx, det))
            logger.debug(f"   检测 #{idx}: 评分={score:.2f}, "
                       f"方法={det.get('method', 'unknown')}, "
                       f"置信度={det.get('confidence', 0.0):.3f}")
        
        # 按评分排序，取最高分
        scored_detections.sort(key=lambda x: x[0], reverse=True)
        best_score, best_idx, best_det = scored_detections[0]
        
        logger.info(f"✅ 选择最佳检测: 评分={best_score:.2f}, "
                   f"方法={best_det.get('method', 'unknown')}, "
                   f"置信度={best_det.get('confidence', 0.0):.3f}")
        
        return best_det
    
    def _calculate_score(self, detection: Dict[str, Any]) -> float:
        """
        计算检测的评分
        
        评分规则：
        - 方法加分：face (+10000) > body (+5000) > new (+0)
        - 置信度：* 100
        - bbox 面积：* 1.0（鼓励选择画面大的）
        - 居中度：- distance_from_center * 0.5（鼓励选择画面中心的）
        
        Args:
            detection: 检测记录
        
        Returns:
            评分（越高越好）
        """
        score = 0.0
        
        # 1. 方法加分（最重要）
        method = detection.get('method', 'unknown')
        if method == 'face':
            score += 10000  # 正脸确认，权重极大
        elif method == 'body':
            score += 5000   # 身体匹配
        elif method == 'new':
            score += 0      # 新检测（陌生人）
        
        # 2. 置信度加分
        confidence = detection.get('confidence', 0.0)
        score += confidence * 100
        
        # 3. bbox 面积加分（分辨率优先）
        bbox = detection.get('bbox')
        if bbox:
            try:
                x1, y1, x2, y2 = bbox
                area = (x2 - x1) * (y2 - y1)
                score += area * 1.0
            except (ValueError, TypeError):
                logger.warning(f"   无效的 bbox: {bbox}")
        
        # 4. 居中度（可选，如果有画面尺寸信息）
        # 这里假设画面中心在 (320, 240)，实际应该从视频元数据获取
        if bbox:
            try:
                x1, y1, x2, y2 = bbox
                center_x = (x1 + x2) / 2
                center_y = (y1 + y2) / 2
                # 假设画面中心在 (320, 240)
                distance_from_center = ((center_x - 320) ** 2 + (center_y - 240) ** 2) ** 0.5
                score -= distance_from_center * 0.5
            except (ValueError, TypeError):
                pass
        
        return score
    
    def group_by_person(self, global_event: Dict[str, Any]) -> Dict[Any, List[Dict[str, Any]]]:
        """
        将 Global_Event 中的所有检测按人物ID分组
        
        支持：
        - 有 person_id 的人物（家人、疑似家人）
        - 陌生人（person_id=None），使用特殊标识分组
        
        Args:
            global_event: Global_Event 对象
        
        Returns:
            按人物ID/标识分组的检测字典：
            {
                person_id (int): [detection1, detection2, ...],  # 已知人物
                'stranger_hash_xxx' (str): [detection1, ...],    # 陌生人（基于body_embedding）
                'stranger_unknown_N' (str): [detection1, ...],   # 陌生人（无body_embedding）
                ...
            }
        """
        grouped: Dict[Any, List[Dict[str, Any]]] = {}
        stranger_index = 0
        
        # 遍历所有 Clip
        clips = global_event.get('clips', [])
        for clip in clips:
            # 遍历所有帧
            for frame_people in clip.get('people_detected', []):
                # 遍历每帧的所有人物
                for person in frame_people:
                    person_id = person.get('person_id')
                    role = person.get('role', 'stranger')
                    
                    # 处理有 person_id 的检测（家人、疑似家人）
                    if person_id is not None:
                        if person_id not in grouped:
                            grouped[person_id] = []
                        grouped[person_id].append(person)
                    
                    # 处理陌生人（person_id=None）
                    elif role == 'stranger':
                        # 为陌生人生成唯一标识
                        stranger_key = self._generate_stranger_key(person, stranger_index)
                        stranger_index += 1
                        
                        if stranger_key not in grouped:
                            grouped[stranger_key] = []
                        grouped[stranger_key].append(person)
        
        logger.info(f"📊 按人物分组完成: {len(grouped)} 个不同人物")
        for person_key, detections in grouped.items():
            if isinstance(person_key, str) and person_key.startswith('stranger_'):
                logger.debug(f"   陌生人 {person_key}: {len(detections)} 次检测")
            else:
                logger.debug(f"   人物 {person_key}: {len(detections)} 次检测")
        
        return grouped
    
    def _generate_stranger_key(self, person: Dict[str, Any], index: int) -> str:
        """
        为陌生人生成唯一标识
        
        策略：
        1. 如果有 body_embedding，使用哈希值（相同身体特征 = 同一人）
        2. 否则，使用 'stranger_unknown_{index}'
        
        Args:
            person: 人物检测记录
            index: 陌生人索引（用于生成唯一标识）
        
        Returns:
            陌生人唯一标识字符串
        """
        body_embedding = person.get('body_embedding')
        if body_embedding is not None:
            try:
                import hashlib
                import numpy as np
                # 使用 body_embedding 的前20个值生成哈希（更稳定）
                hash_input = str(body_embedding[:20].tolist())
                hash_value = hashlib.md5(hash_input.encode()).hexdigest()[:8]
                return f'stranger_hash_{hash_value}'
            except Exception as e:
                logger.warning(f"⚠️  生成陌生人哈希失败: {e}，使用索引标识")
                return f'stranger_unknown_{index}'
        else:
            return f'stranger_unknown_{index}'

