"""
Workflow 模块
包含 Phase 0 (初始化)、Phase 1 (视觉扫描与特征提取)、Phase 2 (时空事件合并)、Phase 3 (LLM 语义生成)、Phase 4 (结构化落库)、Phase 5 (每日总结) 和 Phase 6 (用户检索与 RAG)
"""

# Phase 0: 系统初始化
from .phase0_initialization import (
    LibraryLoader,
    RegistryManager,
    Phase0Initialization
)

# Phase 1: 视觉扫描与特征提取
from .phase1_cv_scanning import (
    DataLoader,
    FrameSampler,
    YoloDetector,
    FeatureEncoder,
    IdentityArbiter,
    ResultBuffer,
    CV_Pipeline
)

# Phase 2: 时空事件合并
from .phase2_event_fusion import (
    StreamSorter,
    FusionPolicy,
    SessionManager,
    EventAggregator,
    ContextBuilder,
    Event_Fusion_Pipeline
)

# Phase 3: LLM 语义生成
from .phase3_agent_interaction import (
    PromptEngine,
    LLMGateway,
    ResponseValidator,
    LLM_Reasoning_Pipeline
)

# Phase 4: 结构化落库
from .phase4_clean_store import (
    QualitySelector,
    VectorAdapter,
    TransactionManager,
    EventDAO,
    AppearanceDAO,
    Persistence_Pipeline
)

# Phase 5: 每日总结
from .phase5_summarize import (
    QueryEngine,
    NarrativeAggregator,
    InsightEngine,
    ArchivePersister,
    Daily_Summary_Pipeline
)

# Phase 6: 用户检索与 RAG
from .phase6_usr_retrieval import (
    QueryParser,
    RetrievalEngine,
    EvidenceMaterializer,
    RAGSynthesisEngine,
    User_Retrieval_Pipeline
)

__all__ = [
    # Phase 0
    'LibraryLoader',
    'RegistryManager',
    'Phase0Initialization',
    # Phase 1
    'DataLoader',
    'FrameSampler',
    'YoloDetector',
    'FeatureEncoder',
    'IdentityArbiter',
    'ResultBuffer',
    'CV_Pipeline',
    # Phase 2
    'StreamSorter',
    'FusionPolicy',
    'SessionManager',
    'EventAggregator',
    'ContextBuilder',
    'Event_Fusion_Pipeline',
    # Phase 3
    'PromptEngine',
    'LLMGateway',
    'ResponseValidator',
    'LLM_Reasoning_Pipeline',
    # Phase 4
    'QualitySelector',
    'VectorAdapter',
    'TransactionManager',
    'EventDAO',
    'AppearanceDAO',
    'Persistence_Pipeline',
    # Phase 5
    'QueryEngine',
    'NarrativeAggregator',
    'InsightEngine',
    'ArchivePersister',
    'Daily_Summary_Pipeline',
    # Phase 6
    'QueryParser',
    'RetrievalEngine',
    'EvidenceMaterializer',
    'RAGSynthesisEngine',
    'User_Retrieval_Pipeline',
]
