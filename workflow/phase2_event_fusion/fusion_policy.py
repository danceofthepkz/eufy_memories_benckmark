"""
模块 2: 融合策略引擎 (Fusion Policy Engine)
职责：判断两个 Clip 是否属于同一个事件
"""

from typing import Dict, Any, Set
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class FusionPolicy:
    """融合策略引擎"""
    
    def __init__(self, time_threshold: int = 60):
        """
        初始化融合策略
        
        Args:
            time_threshold: 时间阈值（秒），超过此值认为不属于同一事件
        """
        self.time_threshold = time_threshold
        logger.debug(f"初始化融合策略: 时间阈值={time_threshold}秒")
    
    def is_connected(self, last_clip: Dict[str, Any], current_clip: Dict[str, Any]) -> bool:
        """
        判断两个 Clip 是否属于同一个事件
        
        Args:
            last_clip: 上一个 Clip_Obj
            current_clip: 当前 Clip_Obj
        
        Returns:
            True 如果应该合并，False 如果应该断开
        """
        # 1. 时间规则：检查时间间隔
        time_connected = self._check_time_rule(last_clip, current_clip)
        
        # 2. 身份规则：检查人物交集
        identity_connected = self._check_identity_rule(last_clip, current_clip)
        
        # 两个规则都满足才合并
        is_connected = time_connected and identity_connected
        
        if is_connected:
            logger.debug(f"✅ Clip 连接: {last_clip['time']} -> {current_clip['time']}")
        else:
            logger.debug(f"❌ Clip 断开: {last_clip['time']} -> {current_clip['time']} "
                        f"(时间: {time_connected}, 身份: {identity_connected})")
        
        return is_connected
    
    def _check_time_rule(self, last_clip: Dict[str, Any], 
                        current_clip: Dict[str, Any]) -> bool:
        """
        时间规则：检查时间间隔是否小于阈值
        
        Args:
            last_clip: 上一个 Clip
            current_clip: 当前 Clip
        
        Returns:
            True 如果时间间隔 < 阈值
        """
        last_time = last_clip['time']
        current_time = current_clip['time']
        
        # 计算时间差（秒）
        time_diff = (current_time - last_time).total_seconds()
        
        # 如果时间差为负（不应该发生，因为已经排序），返回 False
        if time_diff < 0:
            logger.warning(f"⚠️  时间顺序异常: {last_time} > {current_time}")
            return False
        
        return time_diff < self.time_threshold
    
    def _check_identity_rule(self, last_clip: Dict[str, Any], 
                            current_clip: Dict[str, Any]) -> bool:
        """
        身份规则：检查人物交集
        
        规则：
        1. 如果有共同的人物（person_id 相同），返回 True
        2. 如果都是陌生人且时间极短，返回 True（视为连续入侵）
        3. 如果一个是家人一个是陌生人，且时间重叠，返回 True（视为交互）
        
        Args:
            last_clip: 上一个 Clip
            current_clip: 当前 Clip
        
        Returns:
            True 如果满足身份规则
        """
        # 提取两个 Clip 中的人物集合
        last_people = self._extract_people_set(last_clip)
        current_people = self._extract_people_set(current_clip)
        
        # 规则1：有共同的人物
        if last_people['person_ids'] & current_people['person_ids']:
            return True
        
        # 规则2：都是陌生人且时间极短（< 10秒）
        time_diff = (current_clip['time'] - last_clip['time']).total_seconds()
        if (last_people['all_strangers'] and current_people['all_strangers'] 
            and time_diff < 10):
            return True
        
        # 规则3：一个是家人一个是陌生人，且时间重叠（同一时间或时间差 < 5秒）
        if (time_diff < 5 and 
            ((last_people['has_family'] and current_people['has_stranger']) or
             (last_people['has_stranger'] and current_people['has_family']))):
            return True
        
        return False
    
    def _extract_people_set(self, clip: Dict[str, Any]) -> Dict[str, Any]:
        """
        从 Clip 中提取人物信息集合
        
        Args:
            clip: Clip_Obj
        
        Returns:
            人物信息字典：
            {
                'person_ids': Set[int],  # 所有 person_id 的集合
                'all_strangers': bool,    # 是否全是陌生人
                'has_family': bool,       # 是否有家人
                'has_stranger': bool      # 是否有陌生人
            }
        """
        person_ids = set()
        has_family = False
        has_stranger = False
        
        # 遍历所有帧的所有人物
        for frame_people in clip.get('people_detected', []):
            for person in frame_people:
                person_id = person.get('person_id')
                role = person.get('role', 'stranger')
                
                if person_id:
                    person_ids.add(person_id)
                
                if role == 'family':
                    has_family = True
                elif role == 'stranger':
                    has_stranger = True
        
        all_strangers = has_stranger and not has_family
        
        return {
            'person_ids': person_ids,
            'all_strangers': all_strangers,
            'has_family': has_family,
            'has_stranger': has_stranger
        }

