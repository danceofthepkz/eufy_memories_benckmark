"""
模块 2: 叙事流聚合器 (Narrative Aggregator)
职责：将数据库取出的事件列表，转化为 LLM 易读的纯文本时间轴
"""

from typing import List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class NarrativeAggregator:
    """叙事流聚合器"""
    
    def __init__(self):
        """初始化聚合器"""
        logger.debug("✅ NarrativeAggregator 初始化完成")
    
    def format_timeline(self, events: List[Dict[str, Any]]) -> str:
        """
        将事件列表格式化为时间线文本
        
        Args:
            events: 事件列表，每个事件包含 start_time, camera_location, llm_description
        
        Returns:
            格式化的时间线文本字符串
        """
        if not events:
            return ""
        
        timeline_lines = []
        
        for event in events:
            start_time = event.get('start_time')
            camera_location = event.get('camera_location', '未知位置')
            llm_description = event.get('llm_description', '无描述')
            
            # 格式化时间
            if isinstance(start_time, datetime):
                time_str = start_time.strftime('%H:%M:%S')
            elif isinstance(start_time, str):
                time_str = start_time
            else:
                time_str = "未知时间"
            
            # 构建时间线条目
            timeline_line = f"- [{time_str}] [{camera_location}]: {llm_description}"
            timeline_lines.append(timeline_line)
        
        timeline_text = "\n".join(timeline_lines)
        
        logger.debug(f"✅ 时间线格式化完成: {len(events)} 个事件，{len(timeline_text)} 字符")
        
        return timeline_text
    
    def estimate_tokens(self, text: str) -> int:
        """
        估算文本的 token 数量（简单估算：1 token ≈ 4 字符）
        
        Args:
            text: 文本字符串
        
        Returns:
            估算的 token 数量
        """
        # 简单估算：中文字符和英文单词的平均 token 数
        # 这里使用 1 token ≈ 4 字符的粗略估算
        estimated_tokens = len(text) // 4
        return estimated_tokens
    
    def check_token_limit(self, text: str, max_tokens: int = 100000) -> bool:
        """
        检查文本是否超过 token 限制
        
        Args:
            text: 文本字符串
            max_tokens: 最大 token 数（Gemini 2.5 Flash Lite 的上下文窗口很大，这里设置一个安全值）
        
        Returns:
            True 如果未超过限制，False 如果超过
        """
        estimated_tokens = self.estimate_tokens(text)
        
        if estimated_tokens > max_tokens:
            logger.warning(f"⚠️  文本 token 数 ({estimated_tokens}) 超过限制 ({max_tokens})")
            return False
        
        logger.debug(f"✅ Token 检查通过: {estimated_tokens} tokens")
        return True

