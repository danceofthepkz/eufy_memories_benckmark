"""
Phase 2: 时空事件合并 (Event Fusion)
将第一阶段的 Clip_Obj 合并为全局事件
"""

from .stream_sorter import StreamSorter
from .fusion_policy import FusionPolicy
from .session_manager import SessionManager
from .event_aggregator import EventAggregator
from .context_builder import ContextBuilder
from .identity_refiner import IdentityRefiner
from .event_fusion_pipeline import Event_Fusion_Pipeline

__all__ = [
    'StreamSorter',
    'FusionPolicy',
    'SessionManager',
    'EventAggregator',
    'ContextBuilder',
    'IdentityRefiner',
    'Event_Fusion_Pipeline',
]

