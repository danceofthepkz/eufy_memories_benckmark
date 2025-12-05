"""
模块 4: 全局事件聚合器 (Global Event Aggregator)
职责：将一组 Clip 打包成一个 Global_Event 对象
"""

from typing import List, Dict, Any, Set, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class EventAggregator:
    """全局事件聚合器"""
    
    def __init__(self):
        """初始化聚合器"""
        pass
    
    def pack(self, clips: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        将一组 Clip 打包成一个 Global_Event 对象
        
        Args:
            clips: Clip_Obj 列表（属于同一个事件）
        
        Returns:
            Global_Event 对象：
            {
                'start_time': datetime,
                'end_time': datetime,
                'duration': float,  # 秒
                'cameras': List[str],  # 涉及的摄像头列表
                'people': Set[int],  # 涉及的人物ID集合
                'people_info': Dict[int, Dict],  # 每个人物的详细信息
                'clips': List[Dict],  # 原始 Clip 列表
                'keyframes': Dict[int, Dict],  # 每个人物的代表性特征
            }
        """
        if not clips:
            logger.warning("⚠️  尝试打包空的事件")
            return None
        
        logger.info(f"📦 打包事件: {len(clips)} 个 Clip")
        
        # 1. 时间聚合
        start_time = clips[0]['time']
        end_time = clips[-1]['time']
        
        # 计算 duration：使用事件内相关视频的最长时长
        video_durations = []
        for clip in clips:
            if 'video_duration' in clip and clip['video_duration']:
                video_durations.append(clip['video_duration'])
        
        if video_durations:
            # 使用最长视频时长
            duration = max(video_durations)
            logger.debug(f"   视频时长列表: {video_durations}, 使用最长时长: {duration:.2f}秒")
        else:
            # 降级方案：使用时间差
            duration = (end_time - start_time).total_seconds()
            logger.debug(f"   未找到视频时长信息，使用时间差: {duration:.2f}秒")
        
        # 2. 摄像头聚合
        cameras = list(set(clip['cam'] for clip in clips))
        
        # 3. 人物聚合
        people_ids, people_info = self._extract_people_info(clips)
        
        # 4. 代表性特征提取（Keyframe Selection）
        keyframes = self._select_keyframes(clips, people_ids)
        
        # 构建 Global_Event 对象
        global_event = {
            'start_time': start_time,
            'end_time': end_time,
            'duration': duration,
            'cameras': cameras,
            'people': people_ids,
            'people_info': people_info,
            'clips': clips,
            'keyframes': keyframes,
            'clip_count': len(clips)
        }
        
        logger.info(f"✅ 事件打包完成: "
                   f"时间跨度 {duration:.0f}秒, "
                   f"{len(cameras)} 个摄像头, "
                   f"{len(people_ids)} 个人物, "
                   f"{len(clips)} 个 Clip")
        
        return global_event
    
    def _extract_people_info(self, clips: List[Dict[str, Any]]) -> Tuple[Set[int], Dict[int, Dict]]:
        """
        从 Clip 列表中提取人物信息
        
        修改：统计陌生人数量，即使没有 person_id 也要标记为有人出现
        
        Args:
            clips: Clip 列表
        
        Returns:
            (人物ID集合, 人物信息字典)
            注意：如果只有陌生人（没有 person_id），people_ids 可能为空，
            但会在 people_info 中添加特殊标记 'has_strangers': True
        """
        people_ids: Set[int] = set()
        people_info: Dict[int, Dict] = {}
        has_strangers = False
        stranger_count = 0
        
        for clip in clips:
            for frame_people in clip.get('people_detected', []):
                for person in frame_people:
                    person_id = person.get('person_id')
                    role = person.get('role', 'stranger')
                    method = person.get('method', 'unknown')
                    
                    if person_id:
                        people_ids.add(person_id)
                        
                        # 更新人物信息（保留最新的信息）
                        if person_id not in people_info:
                            people_info[person_id] = {
                                'person_id': person_id,
                                'role': role,
                                'method': method,
                                'first_seen': clip['time'],
                                'last_seen': clip['time'],
                                'cameras': set([clip['cam']])
                            }
                        else:
                            # 更新最后出现时间和摄像头
                            people_info[person_id]['last_seen'] = clip['time']
                            people_info[person_id]['cameras'].add(clip['cam'])
                        
                        # 如果这个 person_id 对应的是陌生人（role='stranger' 或 'unknown'），也标记
                        if role in ['stranger', 'unknown']:
                            has_strangers = True
                    elif role == 'stranger':
                        # 统计陌生人（即使没有 person_id）
                        has_strangers = True
                        stranger_count += 1
        
        # 将摄像头集合转换为列表
        for person_id in people_info:
            people_info[person_id]['cameras'] = list(people_info[person_id]['cameras'])
        
        # 检查是否有陌生人（包括已有 person_id 的陌生人）
        # 统计 people_info 中 role='stranger' 或 role='unknown' 的人数
        stranger_person_count = 0
        for person_id, info in people_info.items():
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
                logger.info(f"   检测到 {total_stranger_count} 个陌生人（包括 {stranger_person_count} 个已有 person_id 的）")
            else:
                # 如果已存在，更新计数
                people_info[-1]['stranger_count'] = total_stranger_count
                logger.info(f"   更新陌生人计数: {total_stranger_count} 个")
        
        return people_ids, people_info
    
    def _select_keyframes(self, clips: List[Dict[str, Any]], 
                          people_ids: Set[int]) -> Dict[int, Dict]:
        """
        为每个人物选择代表性特征（Keyframe Selection）
        
        策略：
        - 选择置信度最高的检测
        - 如果有多个相同置信度，选择画面最大的（bbox面积最大）
        - 优先选择有正脸的检测
        
        Args:
            clips: Clip 列表
            people_ids: 人物ID集合
        
        Returns:
            每个人物的代表性特征字典：
            {
                person_id: {
                    'bbox': (x1, y1, x2, y2),
                    'confidence': float,
                    'method': str,
                    'frame_idx': int,
                    'clip_time': datetime,
                    'cam': str
                }
            }
        """
        keyframes: Dict[int, Dict] = {}
        
        for person_id in people_ids:
            best_detection = None
            best_score = -1
            
            # 遍历所有 Clip 的所有帧，寻找最佳检测
            for clip in clips:
                for frame_idx, frame_people in enumerate(clip.get('people_detected', [])):
                    for person in frame_people:
                        if person.get('person_id') != person_id:
                            continue
                        
                        # 计算评分
                        score = self._calculate_detection_score(person)
                        
                        if score > best_score:
                            best_score = score
                            best_detection = {
                                'bbox': person.get('bbox'),
                                'confidence': person.get('confidence', 0.0),
                                'method': person.get('method', 'unknown'),
                                'frame_idx': frame_idx,
                                'clip_time': clip['time'],
                                'cam': clip['cam']
                            }
            
            if best_detection:
                keyframes[person_id] = best_detection
        
        return keyframes
    
    def _calculate_detection_score(self, person: Dict[str, Any]) -> float:
        """
        计算检测的评分（用于选择最佳 Keyframe）
        
        评分规则：
        - 有正脸（method='face'）：+100
        - 置信度：* 10
        - bbox 面积：* 0.01（鼓励选择画面大的）
        
        Args:
            person: 人物检测信息
        
        Returns:
            评分（越高越好）
        """
        score = 0.0
        
        # 方法加分
        method = person.get('method', 'unknown')
        if method == 'face':
            score += 100
        elif method == 'body':
            score += 50
        
        # 置信度加分
        confidence = person.get('confidence', 0.0)
        score += confidence * 10
        
        # bbox 面积加分
        bbox = person.get('bbox')
        if bbox:
            x1, y1, x2, y2 = bbox
            area = (x2 - x1) * (y2 - y1)
            score += area * 0.01
        
        return score

