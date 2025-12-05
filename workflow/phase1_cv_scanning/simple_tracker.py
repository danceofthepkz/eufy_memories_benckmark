"""
简单跟踪器模块 (Simple Tracker)
基于 IoU (Intersection over Union) 的帧内人物跟踪
用于优化：当人物稳定出现在画面中时，跳过重复的特征提取和身份识别
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def calculate_iou(bbox1: Tuple[int, int, int, int], bbox2: Tuple[int, int, int, int]) -> float:
    """
    计算两个边界框的 IoU (Intersection over Union)
    
    Args:
        bbox1: (x1, y1, x2, y2)
        bbox2: (x1, y1, x2, y2)
        
    Returns:
        IoU 值 (0-1)
    """
    x1_1, y1_1, x2_1, y2_1 = bbox1
    x1_2, y1_2, x2_2, y2_2 = bbox2
    
    # 计算交集
    x1_i = max(x1_1, x1_2)
    y1_i = max(y1_1, y1_2)
    x2_i = min(x2_1, x2_2)
    y2_i = min(y2_1, y2_2)
    
    if x2_i <= x1_i or y2_i <= y1_i:
        return 0.0
    
    intersection = (x2_i - x1_i) * (y2_i - y1_i)
    
    # 计算并集
    area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
    area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
    union = area1 + area2 - intersection
    
    if union == 0:
        return 0.0
    
    return intersection / union


class TrackedPerson:
    """跟踪中的人物对象"""
    
    def __init__(self, track_id: int, bbox: Tuple[int, int, int, int], 
                 identity: Dict, frame_idx: int):
        """
        Args:
            track_id: 跟踪ID
            bbox: 边界框 (x1, y1, x2, y2)
            identity: 身份信息 {person_id, role, method, ...}
            frame_idx: 当前帧索引
        """
        self.track_id = track_id
        self.bbox = bbox
        self.identity = identity
        self.last_frame_idx = frame_idx
        self.first_frame_idx = frame_idx
        self.skip_count = 0  # 跳过的帧数
        self.total_detections = 1  # 总检测次数


class SimpleTracker:
    """
    简单跟踪器
    基于 IoU 匹配检测框，实现帧内人物跟踪
    """
    
    def __init__(self, 
                 iou_threshold: float = 0.7,
                 revalidate_interval: int = 5,
                 max_age: int = 3):
        """
        初始化跟踪器
        
        Args:
            iou_threshold: IoU 阈值，超过此值认为是同一个人
            revalidate_interval: 重新验证间隔（帧数），每 N 帧重新检测一次
            max_age: 跟踪最大年龄（帧数），超过此值未匹配则清除
        """
        self.iou_threshold = iou_threshold
        self.revalidate_interval = revalidate_interval
        self.max_age = max_age
        
        self.tracks: Dict[int, TrackedPerson] = {}  # {track_id: TrackedPerson}
        self.next_track_id = 1
        
        logger.debug(f"初始化跟踪器: IoU阈值={iou_threshold}, "
                    f"重新验证间隔={revalidate_interval}帧, "
                    f"最大年龄={max_age}帧")
    
    def match(self, bbox: Tuple[int, int, int, int], 
              current_frame_idx: int) -> Optional[int]:
        """
        尝试将检测框匹配到已有跟踪
        
        Args:
            bbox: 检测框 (x1, y1, x2, y2)
            current_frame_idx: 当前帧索引
            
        Returns:
            匹配的 track_id，如果没有匹配则返回 None
        """
        best_match_id = None
        best_iou = 0.0
        
        for track_id, track in self.tracks.items():
            # 检查跟踪是否过期
            age = current_frame_idx - track.last_frame_idx
            if age > self.max_age:
                continue
            
            # 计算 IoU
            iou = calculate_iou(bbox, track.bbox)
            
            if iou > best_iou and iou >= self.iou_threshold:
                best_iou = iou
                best_match_id = track_id
        
        return best_match_id
    
    def create_track(self, bbox: Tuple[int, int, int, int], 
                     identity: Dict, frame_idx: int) -> int:
        """
        创建新的跟踪
        
        Args:
            bbox: 检测框
            identity: 身份信息
            frame_idx: 当前帧索引
            
        Returns:
            新的 track_id
        """
        track_id = self.next_track_id
        self.next_track_id += 1
        
        self.tracks[track_id] = TrackedPerson(
            track_id=track_id,
            bbox=bbox,
            identity=identity,
            frame_idx=frame_idx
        )
        
        logger.debug(f"创建新跟踪: track_id={track_id}, "
                    f"person_id={identity.get('person_id')}, "
                    f"frame={frame_idx}")
        
        return track_id
    
    def update_track(self, track_id: int, bbox: Tuple[int, int, int, int],
                     identity: Optional[Dict], frame_idx: int, 
                     skip_detection: bool = False):
        """
        更新跟踪信息
        
        Args:
            track_id: 跟踪ID
            bbox: 新的检测框
            identity: 新的身份信息（如果 skip_detection=True 则为 None）
            frame_idx: 当前帧索引
            skip_detection: 是否跳过了检测（复用上一帧的身份）
        """
        if track_id not in self.tracks:
            logger.warning(f"尝试更新不存在的跟踪: track_id={track_id}")
            return
        
        track = self.tracks[track_id]
        track.bbox = bbox
        track.last_frame_idx = frame_idx
        track.total_detections += 1
        
        if skip_detection:
            track.skip_count += 1
            # 保持原有身份信息
        else:
            # 更新身份信息
            if identity:
                track.identity = identity
            track.skip_count = 0
    
    def should_revalidate(self, track_id: int, current_frame_idx: int) -> bool:
        """
        判断是否需要重新验证（重新进行特征提取和身份识别）
        
        Args:
            track_id: 跟踪ID
            current_frame_idx: 当前帧索引
            
        Returns:
            True 如果需要重新验证
        """
        if track_id not in self.tracks:
            return True
        
        track = self.tracks[track_id]
        frames_since_last_detection = current_frame_idx - track.last_frame_idx + track.skip_count
        
        # 如果跳过的帧数达到重新验证间隔，需要重新检测
        return frames_since_last_detection >= self.revalidate_interval
    
    def cleanup(self, current_frame_idx: int):
        """
        清理过期的跟踪
        
        Args:
            current_frame_idx: 当前帧索引
        """
        expired_tracks = []
        
        for track_id, track in self.tracks.items():
            age = current_frame_idx - track.last_frame_idx
            if age > self.max_age:
                expired_tracks.append(track_id)
        
        for track_id in expired_tracks:
            track = self.tracks.pop(track_id)
            logger.debug(f"清除过期跟踪: track_id={track_id}, "
                        f"存活帧数={track.last_frame_idx - track.first_frame_idx + 1}, "
                        f"跳过检测={track.skip_count}/{track.total_detections}")
    
    def get_track_info(self, track_id: int) -> Optional[Dict]:
        """
        获取跟踪信息
        
        Args:
            track_id: 跟踪ID
            
        Returns:
            跟踪信息字典，如果不存在则返回 None
        """
        if track_id not in self.tracks:
            return None
        
        track = self.tracks[track_id]
        return {
            'track_id': track.track_id,
            'person_id': track.identity.get('person_id'),
            'role': track.identity.get('role'),
            'method': track.identity.get('method'),
            'bbox': track.bbox,
            'first_frame': track.first_frame_idx,
            'last_frame': track.last_frame_idx,
            'skip_count': track.skip_count,
            'total_detections': track.total_detections,
            'skip_ratio': track.skip_count / track.total_detections if track.total_detections > 0 else 0
        }
    
    def get_stats(self) -> Dict:
        """
        获取跟踪统计信息
        
        Returns:
            统计信息字典
        """
        if not self.tracks:
            return {
                'total_tracks': 0,
                'active_tracks': 0,
                'total_skips': 0,
                'total_detections': 0
            }
        
        total_skips = sum(track.skip_count for track in self.tracks.values())
        total_detections = sum(track.total_detections for track in self.tracks.values())
        
        return {
            'total_tracks': len(self.tracks),
            'active_tracks': len(self.tracks),
            'total_skips': total_skips,
            'total_detections': total_detections,
            'skip_ratio': total_skips / total_detections if total_detections > 0 else 0
        }
    
    def reset(self):
        """重置跟踪器（用于处理新视频）"""
        self.tracks.clear()
        self.next_track_id = 1
        logger.debug("跟踪器已重置")

