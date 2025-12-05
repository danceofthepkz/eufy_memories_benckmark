"""
Phase 6 测试脚本
测试用户检索与 RAG 功能
"""

import sys
import logging
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from workflow.phase6_usr_retrieval import User_Retrieval_Pipeline

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_query_examples():
    """测试示例查询"""
    logger.info("=" * 60)
    logger.info("Phase 6: User Retrieval & RAG 测试")
    logger.info("=" * 60)
    
    # 初始化 Pipeline
    project_root = Path('.')
    pipeline = User_Retrieval_Pipeline(
        videos_base_dir=str(project_root / 'memories_ai_benchmark' / 'videos')
    )
    
    # 测试查询列表
    test_queries = [
        "9月1日那天，爸爸回家的时候穿什么衣服？",
        "2025年9月1日有什么活动？",
        "9月1日有陌生人出现吗？",
        "今天有什么事件？",
    ]
    
    for idx, query in enumerate(test_queries, 1):
        logger.info(f"\n{'='*60}")
        logger.info(f"测试查询 #{idx}: {query}")
        logger.info(f"{'='*60}\n")
        
        try:
            result = pipeline.answer(query)
            
            logger.info(f"\n📝 回答:")
            logger.info(f"   {result['answer']}")
            logger.info(f"\n📊 统计:")
            logger.info(f"   证据数量: {result['evidence_count']}")
            logger.info(f"   包含图片: {result['has_images']}")
            if result['has_images']:
                logger.info(f"   图片数量: {len(result['images'])}")
                for img_url in result['images'][:3]:  # 只显示前3张
                    logger.info(f"     - {img_url}")
            
            logger.info(f"\n🔍 查询对象:")
            logger.info(f"   {result['query_obj']}")
            
        except Exception as e:
            logger.error(f"❌ 查询失败: {e}")
            import traceback
            traceback.print_exc()


def main():
    """主函数"""
    test_query_examples()


if __name__ == '__main__':
    main()

