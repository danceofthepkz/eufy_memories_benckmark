#!/usr/bin/env python3
"""
Phase 1 + Phase 2 + Phase 3 + Phase 4 + Phase 5 + Phase 6 完整集成测试
展示完整的处理流程：视频处理 → 事件融合 → LLM 生成日志 → 数据库持久化 → 每日总结生成 → 用户检索
"""

import sys
import logging
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from workflow import (
    CV_Pipeline,
    Event_Fusion_Pipeline,
    LLM_Reasoning_Pipeline,
    Persistence_Pipeline,
    Daily_Summary_Pipeline,
    User_Retrieval_Pipeline
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """主函数：演示 Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 的完整流程"""
    logger.info("=" * 60)
    logger.info("Phase 1-6 完整集成测试")
    logger.info("=" * 60)
    
    # ========== Phase 1-5: 数据处理流程 ==========
    logger.info("\n" + "=" * 60)
    logger.info("Phase 1-5: 数据处理流程")
    logger.info("=" * 60)
    
    project_root = Path('.')
    
    # Phase 1
    logger.info("\n[Phase 1] 视觉扫描与特征提取...")
    try:
        cv_pipeline = CV_Pipeline(
            dataset_json_path=str(project_root / 'memories_ai_benchmark' / 'long_mem_dataset.json'),
            videos_base_dir=str(project_root / 'memories_ai_benchmark' / 'videos'),
            yolo_model='yolov8n.pt',
            face_model_name='buffalo_l',
            reid_model_name='osnet_x1_0',
            enable_tracking=True
        )
        clip_objs = cv_pipeline.process_all_clips(max_clips=5)
        logger.info(f"✅ Phase 1 完成: {len(clip_objs)} 个 Clip_Obj")
    except Exception as e:
        logger.error(f"❌ Phase 1 失败: {e}")
        return
    
    # Phase 2
    logger.info("\n[Phase 2] 时空事件合并...")
    try:
        fusion_pipeline = Event_Fusion_Pipeline(time_threshold=60)
        global_events = fusion_pipeline.run(clip_objs)
        logger.info(f"✅ Phase 2 完成: {len(global_events)} 个全局事件")
    except Exception as e:
        logger.error(f"❌ Phase 2 失败: {e}")
        return
    
    # Phase 3
    logger.info("\n[Phase 3] LLM 语义生成...")
    try:
        llm_pipeline = LLM_Reasoning_Pipeline()
        processed_events = llm_pipeline.process_events(global_events)
        logger.info(f"✅ Phase 3 完成: {len(processed_events)} 个事件已生成日志")
    except Exception as e:
        logger.error(f"❌ Phase 3 失败: {e}")
        return
    
    # Phase 4
    logger.info("\n[Phase 4] 结构化落库...")
    try:
        persistence_pipeline = Persistence_Pipeline()
        saved_event_ids = persistence_pipeline.save_events(processed_events)
        logger.info(f"✅ Phase 4 完成: {len(saved_event_ids)} 个事件已保存到数据库")
    except Exception as e:
        logger.error(f"❌ Phase 4 失败: {e}")
        return
    
    # Phase 5
    logger.info("\n[Phase 5] 每日总结生成...")
    try:
        summary_pipeline = Daily_Summary_Pipeline()
        if processed_events:
            first_event_date = processed_events[0]['start_time'].strftime('%Y-%m-%d')
            summary_pipeline.run_for_date(first_event_date, force_update=True)
            logger.info(f"✅ Phase 5 完成: 日期 {first_event_date} 的总结已生成")
    except Exception as e:
        logger.error(f"❌ Phase 5 失败: {e}")
        return
    
    # ========== Phase 6: 用户检索 ==========
    logger.info("\n" + "=" * 60)
    logger.info("Phase 6: 用户检索与 RAG")
    logger.info("=" * 60)
    
    try:
        retrieval_pipeline = User_Retrieval_Pipeline(
            videos_base_dir=str(project_root / 'memories_ai_benchmark' / 'videos')
        )
        logger.info("✅ Phase 6 Pipeline 初始化成功")
    except Exception as e:
        logger.error(f"❌ Phase 6 Pipeline 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 测试查询
    test_queries = [
        "9月1日那天，爸爸回家的时候穿什么衣服？",
        "2025年9月1日有什么活动？",
    ]
    
    for idx, query in enumerate(test_queries, 1):
        logger.info(f"\n[查询 #{idx}] {query}")
        try:
            result = retrieval_pipeline.answer(query)
            
            logger.info(f"\n📝 回答:")
            logger.info(f"   {result['answer']}")
            logger.info(f"\n📊 统计:")
            logger.info(f"   证据数量: {result['evidence_count']}")
            logger.info(f"   包含图片: {result['has_images']}")
            if result['has_images']:
                logger.info(f"   图片数量: {len(result['images'])}")
                
        except Exception as e:
            logger.error(f"❌ 查询失败: {e}")
            import traceback
            traceback.print_exc()
    
    # ========== 完成 ==========
    logger.info("\n" + "=" * 60)
    logger.info("✅ 完整流程测试完成！")
    logger.info("=" * 60)
    logger.info("\n💡 数据流:")
    logger.info("   Phase 1: 视频 → Clip_Obj")
    logger.info("   Phase 2: Clip_Obj → Global_Event")
    logger.info("   Phase 3: Global_Event → 自然语言日志")
    logger.info("   Phase 4: Global_Event → PostgreSQL 数据库")
    logger.info("   Phase 5: event_logs 表 → 每日总结 → daily_summaries 表")
    logger.info("   Phase 6: 用户问题 → 数据库检索 → RAG 回答")


if __name__ == '__main__':
    main()

