"""
模块 3: 滑动窗口会话管理器 (Session Window Manager)
职责：维护当前的"上下文状态"，管理事件缓冲
"""

from typing import List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SessionManager:
    """滑动窗口会话管理器"""
    
    def __init__(self, fusion_policy):
        """
        初始化会话管理器
        
        Args:
            fusion_policy: FusionPolicy 实例，用于判断 Clip 是否连接
        """
        self.fusion_policy = fusion_policy
        self.current_buffer: List[Dict[str, Any]] = []
        logger.debug("初始化会话管理器")
    
    def process_clip(self, clip: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        处理一个 Clip，返回完成的事件列表（如果有）
        
        Args:
            clip: Clip_Obj
        
        Returns:
            完成的事件列表（List[Clip_Obj]），如果没有完成的事件则返回空列表
        """
        completed_events = []
        
        if not self.current_buffer:
            # 第一个 Clip，直接加入 Buffer
            self.current_buffer.append(clip)
            logger.debug(f"开始新事件: {clip['time']} @ {clip['cam']}")
            return completed_events
        
        # 获取 Buffer 中的最后一个 Clip
        last_clip = self.current_buffer[-1]
        
        # 调用策略引擎判断是否连接
        if self.fusion_policy.is_connected(last_clip, clip):
            # Hit: 连接 → 加入 Buffer
            self.current_buffer.append(clip)
            logger.debug(f"事件延续: {clip['time']} @ {clip['cam']} "
                        f"(当前事件包含 {len(self.current_buffer)} 个 Clip)")
        else:
            # Miss: 断开 → 封存当前 Buffer，开始新事件
            completed_events.append(self.current_buffer.copy())
            logger.info(f"事件完成: {len(self.current_buffer)} 个 Clip, "
                       f"时间跨度 {self._get_time_span(self.current_buffer)}秒")
            
            # 创建新 Buffer
            self.current_buffer = [clip]
            logger.debug(f"开始新事件: {clip['time']} @ {clip['cam']}")
        
        return completed_events
    
    def finalize(self) -> List[Dict[str, Any]]:
        """
        完成处理，返回最后一个事件（如果有）
        
        Returns:
            最后一个事件（List[Clip_Obj]），如果没有则返回空列表
        """
        if not self.current_buffer:
            return []
        
        logger.info(f"最终事件: {len(self.current_buffer)} 个 Clip, "
                   f"时间跨度 {self._get_time_span(self.current_buffer)}秒")
        
        return [self.current_buffer.copy()]
    
    def _get_time_span(self, clips: List[Dict[str, Any]]) -> float:
        """
        计算事件的时间跨度（秒）
        
        Args:
            clips: Clip 列表
        
        Returns:
            时间跨度（秒）
        """
        if not clips:
            return 0.0
        
        start_time = clips[0]['time']
        end_time = clips[-1]['time']
        
        return (end_time - start_time).total_seconds()
    
    def reset(self):
        """重置管理器（用于处理新的数据流）"""
        self.current_buffer.clear()
        logger.debug("会话管理器已重置")

