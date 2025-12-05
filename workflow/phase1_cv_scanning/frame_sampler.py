"""
模块 2: 视频流采样模块 (Frame Sampler)
职责：控制处理频率，防止算力浪费
"""

import cv2
import numpy as np
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)


class FrameSampler:
    """视频流采样模块"""
    
    def __init__(self):
        """初始化采样器"""
        pass
    
    def get_frames(self, video_path: str, fps: float = 1.0) -> Tuple[List[np.ndarray], float]:
        """
        从视频中采样帧
        
        Args:
            video_path: 视频文件路径
            fps: 目标采样帧率（每秒提取多少帧），默认 1.0（每秒1帧）
            
        Returns:
            (原始帧图片数组, 视频时长（秒）)
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"❌ 无法打开视频: {video_path}")
            return [], 0.0
        
        # 读取视频 FPS 和总帧数
        video_fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # 计算视频时长（秒）
        video_duration = total_frames / video_fps if video_fps > 0 else 0.0
        
        # 计算跳帧步长
        # 例如：30fps 的视频，要每秒取1帧，则每隔 30 帧取 1 帧
        skip_step = int(video_fps / fps) if video_fps > 0 and fps > 0 else 30
        
        logger.info(f"📹 视频信息: FPS={video_fps:.2f}, 总帧数={total_frames}, "
                   f"时长={video_duration:.2f}秒, 采样间隔={skip_step}")
        
        frames = []
        frame_count = 0
        
        while True:
            success, frame = cap.read()
            if not success:
                break
            
            # 跳帧逻辑：每隔 skip_step 帧取 1 帧
            if frame_count % skip_step == 0:
                frames.append(frame.copy())
            
            frame_count += 1
        
        cap.release()
        
        logger.info(f"✅ 采样完成: 提取了 {len(frames)} 帧（目标: {fps} fps）")
        
        return frames, video_duration

