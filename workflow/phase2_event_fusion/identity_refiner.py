"""
身份一致性检查模块 (Identity Consistency Refiner)
职责：在事件级别检查身份一致性，将疑似家人和陌生人重新评估
"""

from typing import Dict, Any, List, Set
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class IdentityRefiner:
    """身份一致性检查器"""
    
    def __init__(self, 
                 time_window_seconds: int = 300,  # 5分钟内认为是同一场景
                 confidence_boost: float = 0.1):  # 在同一事件中多次出现时，置信度提升
        """
        初始化身份一致性检查器
        
        Args:
            time_window_seconds: 时间窗口（秒），在此窗口内的检测认为是同一场景
            confidence_boost: 置信度提升值，当同一人在事件中多次出现时使用
        """
        self.time_window_seconds = time_window_seconds
        self.confidence_boost = confidence_boost
        
        logger.debug(f"✅ IdentityRefiner 初始化完成 (time_window={time_window_seconds}s, confidence_boost={confidence_boost})")
    
    def refine_event_identities(self, global_event: Dict[str, Any]) -> Dict[str, Any]:
        """
        在事件级别优化身份识别
        
        策略：
        1. 如果事件中既有家人又有疑似家人/陌生人，且他们在相似时间出现，将疑似家人/陌生人提升为家人
        2. 如果疑似家人在事件中多次出现，提升为家人
        3. 如果陌生人在事件中多次出现，且与家人出现时间重叠，标记为疑似家人
        
        Args:
            global_event: Global_Event 对象
        
        Returns:
            优化后的 Global_Event 对象
        """
        clips = global_event.get('clips', [])
        if not clips:
            return global_event
        
        # 统计事件中的人物出现情况
        person_stats = self._analyze_person_appearances(clips)
        
        # 应用优化规则
        refined_clips = []
        for clip in clips:
            refined_clip = self._refine_clip_identities(clip, person_stats)
            refined_clips.append(refined_clip)
        
        # 更新 global_event
        global_event['clips'] = refined_clips
        
        # 重新聚合人物信息
        self._reaggregate_people_info(global_event)
        
        logger.debug(f"✅ 身份一致性检查完成: 事件包含 {len(clips)} 个 Clip")
        
        return global_event
    
    def _analyze_person_appearances(self, clips: List[Dict[str, Any]]) -> Dict[str, Dict]:
        """
        分析事件中的人物出现情况
        
        Returns:
            {
                'person_id': {
                    'appearances': int,  # 出现次数
                    'roles': Set[str],   # 出现的角色（family, suspected_family, stranger）
                    'first_seen': datetime,
                    'last_seen': datetime,
                    'clips': List[int]   # 出现的 Clip 索引
                }
            }
        """
        person_stats = {}
        
        for clip_idx, clip in enumerate(clips):
            clip_time = clip.get('time')
            
            for frame_people in clip.get('people_detected', []):
                for person in frame_people:
                    person_id = person.get('person_id')
                    role = person.get('role', 'stranger')
                    
                    if person_id is None:
                        # 陌生人没有 person_id，使用特殊标记
                        person_id = 'stranger_unknown'
                    
                    if person_id not in person_stats:
                        person_stats[person_id] = {
                            'appearances': 0,
                            'roles': set(),
                            'first_seen': clip_time,
                            'last_seen': clip_time,
                            'clips': []
                        }
                    
                    stats = person_stats[person_id]
                    stats['appearances'] += 1
                    stats['roles'].add(role)
                    stats['last_seen'] = clip_time
                    if clip_idx not in stats['clips']:
                        stats['clips'].append(clip_idx)
        
        return person_stats
    
    def _refine_clip_identities(self, clip: Dict[str, Any], 
                                person_stats: Dict[str, Dict]) -> Dict[str, Any]:
        """
        优化单个 Clip 中的身份识别
        
        Args:
            clip: Clip_Obj
            person_stats: 人物统计信息
        
        Returns:
            优化后的 Clip_Obj
        """
        refined_frame_people = []
        
        for frame_people in clip.get('people_detected', []):
            refined_frame = []
            
            for person in frame_people:
                person_id = person.get('person_id')
                role = person.get('role', 'stranger')
                confidence = person.get('confidence', 0.0)
                
                # 规则1: 如果疑似家人在事件中多次出现（>=3次），提升为家人
                if role == 'suspected_family' and person_id:
                    if person_id in person_stats:
                        stats = person_stats[person_id]
                        if stats['appearances'] >= 3:
                            logger.info(f"🔄 提升疑似家人为家人: Person ID {person_id} (出现 {stats['appearances']} 次)")
                            person['role'] = 'family'
                            person['method'] = 'refined_from_suspected'
                            role = 'family'
                
                # 规则2: 如果陌生人在事件中多次出现（>=3次），且事件中有家人，标记为疑似家人
                if role == 'stranger' and person_id is None:
                    # 检查事件中是否有家人
                    has_family = any(
                        'family' in stats['roles'] or 'suspected_family' in stats['roles']
                        for pid, stats in person_stats.items()
                        if pid != 'stranger_unknown'
                    )
                    
                    # 统计当前陌生人的出现次数（在当前 Clip 中）
                    stranger_in_clip_count = sum(
                        1 for p in frame_people 
                        if p.get('role') == 'stranger' and p.get('person_id') is None
                    )
                    
                    # 统计事件中所有陌生人的总出现次数
                    stranger_total_count = person_stats.get('stranger_unknown', {}).get('appearances', 0)
                    
                    if has_family and stranger_total_count >= 3:
                        logger.info(f"🔄 将多次出现的陌生人标记为疑似家人 (事件中总共出现 {stranger_total_count} 次)")
                        person['role'] = 'suspected_family'
                        person['method'] = 'refined_from_stranger'
                        role = 'suspected_family'
                
                # 规则3: 如果疑似家人/陌生人与家人在同一 Clip 中出现，提升为家人
                if role in ['suspected_family', 'stranger']:
                    # 检查同一 Clip 中是否有家人
                    has_family_in_clip = any(
                        p.get('role') == 'family'
                        for p in frame_people
                    )
                    
                    if has_family_in_clip and person_id:
                        logger.info(f"🔄 提升为家人（与家人在同一 Clip）: Person ID {person_id}")
                        person['role'] = 'family'
                        person['method'] = 'refined_from_context'
                        role = 'family'
                
                refined_frame.append(person)
            
            refined_frame_people.append(refined_frame)
        
        clip['people_detected'] = refined_frame_people
        return clip
    
    def _reaggregate_people_info(self, global_event: Dict[str, Any]):
        """
        重新聚合人物信息（在身份优化后）
        注意：必须保留陌生人信息，否则 Phase 3 会误判为"无人出现"
        """
        people_ids = set()
        people_info = {}
        has_strangers = False
        stranger_count = 0
        
        for clip in global_event.get('clips', []):
            for frame_people in clip.get('people_detected', []):
                for person in frame_people:
                    person_id = person.get('person_id')
                    role = person.get('role', 'stranger')
                    method = person.get('method', 'unknown')
                    
                    # 统计所有人物（包括家人、疑似家人和陌生人）
                    if person_id:
                        people_ids.add(person_id)
                        
                        if person_id not in people_info:
                            people_info[person_id] = {
                                'person_id': person_id,
                                'role': role,
                                'method': method,
                                'first_seen': clip.get('time'),
                                'last_seen': clip.get('time'),
                                'cameras': set([clip.get('cam')])
                            }
                        else:
                            # 更新最后出现时间和摄像头
                            people_info[person_id]['last_seen'] = clip.get('time')
                            people_info[person_id]['cameras'].add(clip.get('cam'))
                        
                        # 如果这个 person_id 对应的是陌生人，标记
                        if role in ['stranger', 'unknown']:
                            has_strangers = True
                    elif role == 'stranger':
                        # 统计陌生人（即使没有 person_id）
                        has_strangers = True
                        stranger_count += 1
        
        # 将摄像头集合转换为列表
        for person_id in people_info:
            if person_id != -1:  # -1 是特殊标记，不需要转换 cameras
                people_info[person_id]['cameras'] = list(people_info[person_id]['cameras'])
        
        # 检查是否有陌生人（包括已有 person_id 的陌生人）
        # 统计 people_info 中 role='stranger' 或 role='unknown' 的人数
        stranger_person_count = 0
        for person_id, info in people_info.items():
            if person_id == -1:  # 跳过特殊标记
                continue
            role = info.get('role', 'unknown')
            if role in ['stranger', 'unknown']:
                stranger_person_count += 1
        
        # 如果有陌生人（无论是否有 person_id），在 people_info 中添加标记
        if has_strangers or stranger_person_count > 0:
            # 计算总陌生人数量（包括已有 person_id 的）
            total_stranger_count = stranger_count + stranger_person_count
            
            # 使用特殊键 -1 来标记陌生人
            if -1 not in people_info:
                people_info[-1] = {
                    'person_id': None,
                    'role': 'stranger',
                    'method': 'new',
                    'stranger_count': total_stranger_count,
                    'has_strangers': True
                }
                logger.info(f"   重新聚合后检测到 {total_stranger_count} 个陌生人（包括 {stranger_person_count} 个已有 person_id 的）")
            else:
                # 如果已存在，更新计数
                people_info[-1]['stranger_count'] = total_stranger_count
                people_info[-1]['has_strangers'] = True
                logger.info(f"   更新陌生人计数: {total_stranger_count} 个")
        
        global_event['people'] = people_ids
        global_event['people_info'] = people_info

