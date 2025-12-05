"""
模块 1: 时间流预处理模块 (Stream Sorter & Validator)
职责：确保输入的数据流是严格按时间顺序排列的
"""

from typing import List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class StreamSorter:
    """时间流预处理模块"""
    
    def __init__(self):
        """初始化排序器"""
        pass
    
    def sort_and_validate(self, clip_objs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        对 Clip_Obj 列表进行排序和验证
        
        Args:
            clip_objs: 第一阶段输出的 Clip_Obj 列表（可能无序）
                [
                    {
                        'time': datetime,
                        'cam': str,
                        'people_detected': List[List[Dict]]
                    },
                    ...
                ]
        
        Returns:
            排序后的有效 Clip_Obj 列表
        """
        if not clip_objs:
            logger.warning("⚠️  输入 Clip_Obj 列表为空")
            return []
        
        logger.info(f"📋 开始排序和验证: {len(clip_objs)} 个 Clip_Obj")
        
        # 1. 验证和清洗
        valid_clips = []
        invalid_count = 0
        
        for idx, clip in enumerate(clip_objs):
            if not self._is_valid_clip(clip):
                invalid_count += 1
                logger.warning(f"⚠️  跳过无效 Clip #{idx}: 缺少必要字段")
                continue
            
            valid_clips.append(clip)
        
        if invalid_count > 0:
            logger.warning(f"⚠️  清洗完成: 移除了 {invalid_count} 个无效 Clip")
        
        # 2. 排序：基于时间戳升序排列
        sorted_clips = sorted(valid_clips, key=lambda x: x['time'])
        
        logger.info(f"✅ 排序完成: {len(sorted_clips)} 个有效 Clip")
        
        # 3. 输出时间范围信息
        if sorted_clips:
            first_time = sorted_clips[0]['time']
            last_time = sorted_clips[-1]['time']
            time_span = last_time - first_time
            
            logger.info(f"   时间范围: {first_time} ~ {last_time}")
            logger.info(f"   时间跨度: {time_span.total_seconds():.0f} 秒 ({time_span.total_seconds()/3600:.2f} 小时)")
        
        return sorted_clips
    
    def _is_valid_clip(self, clip: Dict[str, Any]) -> bool:
        """
        验证 Clip_Obj 是否有效
        
        Args:
            clip: Clip_Obj 字典
        
        Returns:
            True 如果有效，False 如果无效
        """
        # 检查必要字段
        required_fields = ['time', 'cam', 'people_detected']
        
        for field in required_fields:
            if field not in clip:
                return False
        
        # 检查时间字段类型
        if not isinstance(clip['time'], datetime):
            return False
        
        # 检查 people_detected 是否为列表
        if not isinstance(clip['people_detected'], list):
            return False
        
        return True

