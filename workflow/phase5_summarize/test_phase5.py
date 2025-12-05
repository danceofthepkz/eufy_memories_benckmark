"""
Phase 5 测试脚本
测试每日总结生成功能
"""

import sys
import logging
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from workflow.phase5_summarize import Daily_Summary_Pipeline

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_single_date():
    """测试单个日期的总结生成"""
    logger.info("=" * 60)
    logger.info("测试单个日期总结生成")
    logger.info("=" * 60)
    
    # 初始化 Pipeline
    pipeline = Daily_Summary_Pipeline()
    
    # 测试日期（使用数据库中实际存在的日期）
    # 如果数据库中没有数据，可以先运行 Phase 1-4 生成一些事件
    test_date = "2025-09-01"
    
    try:
        record_id = pipeline.run_for_date(test_date, force_update=True)
        
        if record_id:
            logger.info(f"\n✅ 测试成功: record_id={record_id}")
            
            # 查询生成的总结
            summary = pipeline.persister.get_summary(test_date)
            if summary:
                logger.info(f"\n📝 生成的总结:")
                logger.info(f"   日期: {summary['summary_date']}")
                logger.info(f"   事件数: {summary['total_events']}")
                logger.info(f"   总结内容:")
                logger.info(f"   {summary['summary_text']}")
        else:
            logger.warning(f"⚠️  日期 {test_date} 没有事件记录")
            
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_batch_processing():
    """测试批量处理"""
    logger.info("=" * 60)
    logger.info("测试批量处理")
    logger.info("=" * 60)
    
    # 初始化 Pipeline
    pipeline = Daily_Summary_Pipeline()
    
    try:
        # 批量处理所有日期
        results = pipeline.run_batch(force_update=False)  # 不强制更新已存在的总结
        
        logger.info(f"\n✅ 批量处理完成: {len(results)} 个日期")
        for date_str, record_id in results.items():
            logger.info(f"   {date_str}: record_id={record_id}")
            
    except Exception as e:
        logger.error(f"❌ 批量处理失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("Phase 5: Daily Summary 测试")
    logger.info("=" * 60)
    
    # 测试单个日期
    test_single_date()
    
    # 如果需要测试批量处理，取消下面的注释
    # test_batch_processing()


if __name__ == '__main__':
    main()

