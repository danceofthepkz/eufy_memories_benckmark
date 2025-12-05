"""
模块 6: 结果暂存模块 (Result Buffer)
职责：打包结果，暂存内存，等待下一阶段合并
"""

from typing import List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ResultBuffer:
    """结果暂存模块"""
    
    def __init__(self):
        """初始化结果缓冲区"""
        pass
    
    def create_clip_obj(self, timestamp: datetime, camera: str, 
                       people_detected: List[List[Dict]],
                       video_duration: float = None,
                       video_path: str = None) -> Dict[str, Any]:
        """
        构造结构化数据：Clip_Obj
        
        Args:
            timestamp: 视频时间戳
            camera: 摄像头位置
            people_detected: 每帧检测到的人物列表
                [
                    [  # 第1帧
                        {'person_id': 1, 'role': 'family', 'method': 'face', ...},
                        {'person_id': None, 'role': 'stranger', 'method': 'new', ...}
                    ],
                    [  # 第2帧
                        ...
                    ],
                    ...
                ]
            video_duration: 视频时长（秒），可选
            video_path: 视频路径，可选
        
        Returns:
            Clip_Obj: {
                'time': datetime,
                'cam': str,
                'people_detected': List[List[Dict]],
                'video_duration': float,  # 视频时长（秒）
                'video_path': str  # 视频路径
            }
        """
        clip_obj = {
            'time': timestamp,
            'cam': camera,
            'people_detected': people_detected
        }
        
        # 添加视频时长和路径（如果提供）
        if video_duration is not None:
            clip_obj['video_duration'] = video_duration
        if video_path is not None:
            clip_obj['video_path'] = video_path
        
        # 统计信息
        total_detections = sum(len(frame_people) for frame_people in people_detected)
        unique_people = set()
        for frame_people in people_detected:
            for person in frame_people:
                if person.get('person_id'):
                    unique_people.add(person['person_id'])
        
        logger.info(f"📦 创建 Clip_Obj: {camera} @ {timestamp}, "
                   f"{len(people_detected)} 帧, {total_detections} 次检测, "
                   f"{len(unique_people)} 个不同人物")
        
        return clip_obj
    
    def aggregate_clip_results(self, frame_results: List[Dict]) -> List[List[Dict]]:
        """
        将本视频内所有帧、所有人的识别结果聚合
        
        Args:
            frame_results: 每帧的识别结果列表
                [
                    {  # 第1帧
                        'person_id': 1,
                        'role': 'family',
                        'method': 'face',
                        'bbox': (x1, y1, x2, y2),
                        'confidence': 0.9,
                        ...
                    },
                    ...
                ]
        
        Returns:
            聚合后的结果（按帧组织）
        """
        # 这里可以添加聚合逻辑，比如去重、合并等
        # 目前简单返回按帧组织的结果
        return [[result] for result in frame_results]

