"""
第四阶段：结构化落库 (Phase 4: Persistence)
将 Phase 3 生成的 Global_Event 对象持久化到 PostgreSQL 数据库
"""

from .quality_selector import QualitySelector
from .vector_adapter import VectorAdapter
from .transaction_manager import TransactionManager, EventDAO, AppearanceDAO
from .persistence_pipeline import Persistence_Pipeline

__all__ = [
    'QualitySelector',
    'VectorAdapter',
    'TransactionManager',
    'EventDAO',
    'AppearanceDAO',
    'Persistence_Pipeline'
]

