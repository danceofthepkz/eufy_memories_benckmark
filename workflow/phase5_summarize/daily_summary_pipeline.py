"""
主 Pipeline: 每日总结生成 Pipeline
整合所有模块，实现完整的每日总结生成流程
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from .query_engine import QueryEngine
from .narrative_aggregator import NarrativeAggregator
from .insight_engine import InsightEngine
from .archive_persister import ArchivePersister

logger = logging.getLogger(__name__)


class Daily_Summary_Pipeline:
    """每日总结生成 Pipeline"""
    
    def __init__(self, 
                 db_config: Optional[Dict[str, str]] = None,
                 model_name: str = 'gemini-2.5-flash-lite',
                 temperature: float = 0.3,
                 max_output_tokens: int = 512):
        """
        初始化每日总结 Pipeline
        
        Args:
            db_config: 数据库连接配置
            model_name: LLM 模型名称
            temperature: LLM 温度参数
            max_output_tokens: LLM 最大输出 token 数
        """
        logger.info("=" * 60)
        logger.info("初始化 Daily Summary Pipeline (第五阶段)")
        logger.info("=" * 60)
        
        self.query_engine = QueryEngine(db_config)
        self.aggregator = NarrativeAggregator()
        self.insight_engine = InsightEngine(
            model_name=model_name,
            temperature=temperature,
            max_output_tokens=max_output_tokens
        )
        self.persister = ArchivePersister(db_config)
        
        logger.info("✅ Daily Summary Pipeline 初始化完成")
    
    def run_for_date(self, target_date: str, force_update: bool = False) -> Optional[int]:
        """
        处理指定日期的总结
        
        Args:
            target_date: 目标日期，格式为 'YYYY-MM-DD' (如 '2025-09-01')
            force_update: 如果为 True，即使已存在总结也会重新生成
        
        Returns:
            保存的记录ID（如果成功），否则返回 None
        """
        logger.info("=" * 60)
        logger.info(f"开始处理日期: {target_date}")
        logger.info("=" * 60)
        
        # 检查是否已存在总结
        if not force_update:
            existing_summary = self.persister.get_summary(target_date)
            if existing_summary:
                logger.info(f"✅ 日期 {target_date} 已有总结，跳过生成（使用 force_update=True 强制更新）")
                logger.info(f"   现有总结: {existing_summary['summary_text'][:100]}...")
                return existing_summary['id']
        
        # 1. 查询数据（模块 1）
        logger.info("[步骤 1] 查询数据库事件...")
        events = self.query_engine.fetch_events(target_date)
        
        if not events:
            logger.warning(f"⚠️  日期 {target_date} 没有事件记录")
            return None
        
        logger.info(f"✅ 找到 {len(events)} 个事件")
        
        # 2. 格式化时间线（模块 2）
        logger.info("[步骤 2] 格式化时间线...")
        timeline_text = self.aggregator.format_timeline(events)
        
        # 检查 token 限制
        if not self.aggregator.check_token_limit(timeline_text):
            logger.warning("⚠️  时间线文本过长，可能会影响 LLM 处理")
        
        logger.info(f"✅ 时间线格式化完成: {len(timeline_text)} 字符")
        
        # 3. LLM 生成总结（模块 3）
        logger.info("[步骤 3] 调用 LLM 生成总结...")
        summary_text = self.insight_engine.analyze(timeline_text, target_date)
        
        logger.info(f"✅ LLM 总结生成完成: {len(summary_text)} 字符")
        logger.info(f"   总结预览: {summary_text[:150]}...")
        
        # 4. 保存到数据库（模块 4）
        logger.info("[步骤 4] 保存总结到数据库...")
        record_id = self.persister.save(
            summary_date=target_date,
            summary_text=summary_text,
            total_events=len(events)
        )
        
        logger.info("=" * 60)
        logger.info(f"✅ 日期 {target_date} 处理完成: record_id={record_id}")
        logger.info("=" * 60)
        
        return record_id
    
    def run_batch(self, date_list: Optional[List[str]] = None, force_update: bool = False) -> Dict[str, int]:
        """
        批量处理多个日期的总结
        
        Args:
            date_list: 日期列表。如果为 None，则处理数据库中所有有事件的日期
            force_update: 如果为 True，即使已存在总结也会重新生成
        
        Returns:
            处理结果字典：{date: record_id, ...}
        """
        logger.info("=" * 60)
        logger.info("开始批量处理每日总结")
        logger.info("=" * 60)
        
        # 如果没有指定日期列表，则获取所有日期
        if date_list is None:
            date_list = self.query_engine.get_distinct_dates()
        
        logger.info(f"📅 将处理 {len(date_list)} 个日期")
        
        results = {}
        success_count = 0
        skip_count = 0
        
        for idx, target_date in enumerate(date_list, 1):
            logger.info(f"\n[{idx}/{len(date_list)}] 处理日期: {target_date}")
            
            try:
                record_id = self.run_for_date(target_date, force_update=force_update)
                
                if record_id:
                    results[target_date] = record_id
                    success_count += 1
                else:
                    skip_count += 1
                    
            except Exception as e:
                logger.error(f"❌ 处理日期 {target_date} 失败: {e}")
                import traceback
                traceback.print_exc()
                skip_count += 1
        
        logger.info("\n" + "=" * 60)
        logger.info("批量处理完成")
        logger.info("=" * 60)
        logger.info(f"✅ 成功: {success_count} 个日期")
        logger.info(f"⏭️  跳过: {skip_count} 个日期")
        logger.info("=" * 60)
        
        return results

