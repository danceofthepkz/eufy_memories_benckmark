"""
主 Pipeline: 用户检索 Pipeline
整合所有模块，实现完整的用户检索与 RAG 流程
"""

import logging
from typing import Dict, Any, Optional

from .query_parser import QueryParser
from .retrieval_engine import RetrievalEngine
from .evidence_materializer import EvidenceMaterializer
from .rag_synthesis_engine import RAGSynthesisEngine

logger = logging.getLogger(__name__)


class User_Retrieval_Pipeline:
    """用户检索 Pipeline"""
    
    def __init__(self,
                 db_config: Optional[Dict[str, str]] = None,
                 videos_base_dir: Optional[str] = None,
                 snapshots_dir: Optional[str] = None,
                 model_name: str = 'gemini-2.5-flash-lite',
                 temperature: float = 0.3,
                 max_output_tokens: int = 512):
        """
        初始化用户检索 Pipeline
        
        Args:
            db_config: 数据库连接配置
            videos_base_dir: 视频文件基础目录
            snapshots_dir: 快照保存目录
            model_name: LLM 模型名称
            temperature: LLM 温度参数
            max_output_tokens: LLM 最大输出 token 数
        """
        logger.info("=" * 60)
        logger.info("初始化 User Retrieval Pipeline (第六阶段)")
        logger.info("=" * 60)
        
        self.query_parser = QueryParser(db_config)
        self.retrieval_engine = RetrievalEngine(db_config)
        self.evidence_materializer = EvidenceMaterializer(
            videos_base_dir=videos_base_dir,
            snapshots_dir=snapshots_dir
        )
        self.rag_synthesis_engine = RAGSynthesisEngine(
            model_name=model_name,
            temperature=temperature,
            max_output_tokens=max_output_tokens
        )
        
        logger.info("✅ User Retrieval Pipeline 初始化完成")
    
    def answer(self, user_query: str) -> Dict[str, Any]:
        """
        回答用户问题
        
        Args:
            user_query: 用户的自然语言问题
        
        Returns:
            回答字典: {
                'answer': str,  # 最终回答文本
                'evidence_count': int,  # 使用的证据数量
                'has_images': bool,  # 是否包含图片
                'images': List[str],  # 图片 URL 列表
                'query_obj': Dict,  # 解析后的查询对象
                'retrieved_records': List[Dict]  # 检索到的原始记录
            }
        """
        logger.info("=" * 60)
        logger.info(f"处理用户查询: {user_query}")
        logger.info("=" * 60)
        
        # 1. 解析查询（模块 1）
        logger.info("[步骤 1] 解析用户查询...")
        query_obj = self.query_parser.parse(user_query)
        logger.info(f"✅ 查询解析完成: {query_obj}")
        
        # 2. 检索数据（模块 2）
        logger.info("[步骤 2] 检索数据库...")
        retrieved_records = self.retrieval_engine.retrieve(query_obj)
        logger.info(f"✅ 检索完成: 找到 {len(retrieved_records)} 条记录")
        
        if not retrieved_records:
            logger.warning("⚠️  未找到相关记录")
            answer_result = self.rag_synthesis_engine._generate_no_result_answer(user_query)
            return {
                **answer_result,
                'query_obj': query_obj,
                'retrieved_records': []
            }
        
        # 3. 实物化证据（模块 3）
        logger.info("[步骤 3] 提取图片证据...")
        materialized_records = self.evidence_materializer.materialize(retrieved_records)
        logger.info(f"✅ 证据实物化完成")
        
        # 4. RAG 合成回答（模块 4）
        logger.info("[步骤 4] 生成最终回答...")
        answer_result = self.rag_synthesis_engine.synthesize(
            user_query=user_query,
            retrieved_evidence=materialized_records,
            query_obj=query_obj
        )
        logger.info(f"✅ 回答生成完成: {len(answer_result['answer'])} 字符")
        
        logger.info("=" * 60)
        logger.info("✅ 用户查询处理完成")
        logger.info("=" * 60)
        
        return {
            **answer_result,
            'query_obj': query_obj,
            'retrieved_records': materialized_records
        }

