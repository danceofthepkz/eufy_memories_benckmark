"""
第二阶段主 Pipeline: Event_Fusion_Pipeline
整合所有5个模块，实现完整的时空事件合并流程
"""

import logging
from typing import List, Dict, Any, Optional

from .stream_sorter import StreamSorter
from .fusion_policy import FusionPolicy
from .session_manager import SessionManager
from .event_aggregator import EventAggregator
from .context_builder import ContextBuilder
from .identity_refiner import IdentityRefiner

logger = logging.getLogger(__name__)


class Event_Fusion_Pipeline:
    """第二阶段：时空事件合并 Pipeline"""
    
    def __init__(self, time_threshold: int = 60):
        """
        初始化 Event Fusion Pipeline
        
        Args:
            time_threshold: 时间阈值（秒），超过此值认为不属于同一事件
        """
        logger.info("=" * 60)
        logger.info("初始化 Event Fusion Pipeline (第二阶段)")
        logger.info("=" * 60)
        
        # 初始化各个模块
        self.sorter = StreamSorter()                    # 模块 1
        self.policy = FusionPolicy(time_threshold)      # 模块 2
        self.session_manager = SessionManager(self.policy)  # 模块 3
        self.aggregator = EventAggregator()             # 模块 4
        self.identity_refiner = IdentityRefiner()       # 模块 4.5: 身份一致性检查
        self.context_builder = ContextBuilder()        # 模块 5
        
        logger.info(f"✅ Event Fusion Pipeline 初始化完成 (时间阈值: {time_threshold}秒)")
    
    def run(self, raw_clips: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        运行事件融合流程
        
        Args:
            raw_clips: 第一阶段输出的 Clip_Obj 列表（可能无序）
                [
                    {
                        'time': datetime,
                        'cam': str,
                        'people_detected': List[List[Dict]]
                    },
                    ...
                ]
        
        Returns:
            Global_Event 列表：
            [
                {
                    'start_time': datetime,
                    'end_time': datetime,
                    'duration': float,
                    'cameras': List[str],
                    'people': Set[int],
                    'people_info': Dict[int, Dict],
                    'clips': List[Dict],
                    'keyframes': Dict[int, Dict],
                    'prompt_text': str
                },
                ...
            ]
        """
        logger.info("=" * 60)
        logger.info("开始事件融合流程")
        logger.info("=" * 60)
        
        if not raw_clips:
            logger.warning("⚠️  输入 Clip 列表为空")
            return []
        
        # 1. 模块 1: 时间流预处理（排序和验证）
        logger.info("\n[模块 1] 时间流预处理...")
        sorted_clips = self.sorter.sort_and_validate(raw_clips)
        
        if not sorted_clips:
            logger.warning("⚠️  排序后没有有效 Clip")
            return []
        
        # 2. 模块 3: 滑动窗口会话管理（遍历并分组）
        logger.info("\n[模块 2-3] 事件分组...")
        self.session_manager.reset()
        
        event_clips_list = []  # List[List[Clip_Obj]]
        
        for clip in sorted_clips:
            completed_events = self.session_manager.process_clip(clip)
            if completed_events:
                event_clips_list.extend(completed_events)
        
        # 处理最后一个事件
        final_event = self.session_manager.finalize()
        if final_event:
            event_clips_list.extend(final_event)
        
        logger.info(f"✅ 事件分组完成: {len(event_clips_list)} 个事件")
        
        # 3. 模块 4: 全局事件聚合（打包每个事件）
        logger.info("\n[模块 4] 事件聚合...")
        global_events = []
        
        for idx, event_clips in enumerate(event_clips_list, 1):
            logger.info(f"\n处理事件 #{idx}: {len(event_clips)} 个 Clip")
            
            # 打包事件
            global_event = self.aggregator.pack(event_clips)
            
            if not global_event:
                logger.warning(f"⚠️  事件 #{idx} 打包失败")
                continue
            
            # 4.5. 身份一致性检查（新增模块）
            logger.info(f"[模块 4.5] 身份一致性检查...")
            global_event = self.identity_refiner.refine_event_identities(global_event)
            
            # 4. 模块 5: 构建 Prompt 上下文
            logger.info(f"[模块 5] 构建 Prompt 上下文...")
            prompt_text = self.context_builder.build(global_event)
            global_event['prompt_text'] = prompt_text
            
            global_events.append(global_event)
        
        logger.info("\n" + "=" * 60)
        logger.info(f"✅ 事件融合完成: {len(global_events)} 个全局事件")
        logger.info("=" * 60)
        
        # 输出统计信息
        if global_events:
            total_duration = sum(event['duration'] for event in global_events)
            total_clips = sum(event['clip_count'] for event in global_events)
            avg_clips_per_event = total_clips / len(global_events)
            
            logger.info(f"\n📊 统计信息:")
            logger.info(f"   总事件数: {len(global_events)}")
            logger.info(f"   总 Clip 数: {total_clips}")
            logger.info(f"   平均每个事件 Clip 数: {avg_clips_per_event:.1f}")
            logger.info(f"   总时间跨度: {total_duration:.0f} 秒 ({total_duration/3600:.2f} 小时)")
        
        return global_events
    
    def get_event_summary(self, global_event: Dict[str, Any]) -> str:
        """
        获取事件的简要摘要（用于日志输出）
        
        Args:
            global_event: Global_Event 对象
        
        Returns:
            摘要字符串
        """
        start_time = global_event['start_time']
        end_time = global_event['end_time']
        duration = global_event['duration']
        cameras = global_event['cameras']
        people_count = len(global_event['people'])
        clip_count = global_event['clip_count']
        
        return (f"事件: {start_time.strftime('%H:%M:%S')} ~ {end_time.strftime('%H:%M:%S')} "
                f"({duration:.0f}秒), "
                f"{len(cameras)} 个摄像头, {people_count} 个人物, {clip_count} 个 Clip")

