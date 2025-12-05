#!/usr/bin/env python3
"""
Phase 1 + Phase 2 + Phase 3 + Phase 4 + Phase 5 完整集成测试
展示完整的处理流程：视频处理 → 事件融合 → LLM 生成日志 → 数据库持久化 → 每日总结生成
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
    Daily_Summary_Pipeline
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """主函数：演示 Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 的完整流程"""
    logger.info("=" * 60)
    logger.info("Phase 1 + Phase 2 + Phase 3 + Phase 4 + Phase 5 完整集成测试")
    logger.info("=" * 60)
    
    # ========== Phase 1: 视觉扫描与特征提取 ==========
    logger.info("\n" + "=" * 60)
    logger.info("Phase 1: 视觉扫描与特征提取")
    logger.info("=" * 60)
    
    project_root = Path('.')
    try:
        cv_pipeline = CV_Pipeline(
            dataset_json_path=str(project_root / 'memories_ai_benchmark' / 'long_mem_dataset.json'),
            videos_base_dir=str(project_root / 'memories_ai_benchmark' / 'videos'),
            yolo_model='yolov8n.pt',
            face_model_name='buffalo_l',
            reid_model_name='osnet_x1_0',
            enable_tracking=True
        )
        logger.info("✅ Phase 1 Pipeline 初始化成功")
    except Exception as e:
        logger.error(f"❌ Phase 1 Pipeline 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 处理视频（限制数量以加快测试）
    logger.info("\n开始处理视频...")
    try:
        clip_objs = cv_pipeline.process_all_clips(max_clips=10)
        logger.info(f"✅ Phase 1 完成: 生成了 {len(clip_objs)} 个 Clip_Obj")
    except Exception as e:
        logger.error(f"❌ Phase 1 处理失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # ========== Phase 2: 时空事件合并 ==========
    logger.info("\n" + "=" * 60)
    logger.info("Phase 2: 时空事件合并")
    logger.info("=" * 60)
    
    try:
        fusion_pipeline = Event_Fusion_Pipeline(time_threshold=60)
        logger.info("✅ Phase 2 Pipeline 初始化成功")
    except Exception as e:
        logger.error(f"❌ Phase 2 Pipeline 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    logger.info("\n开始事件融合...")
    try:
        global_events = fusion_pipeline.run(clip_objs)
        logger.info(f"✅ Phase 2 完成: 生成了 {len(global_events)} 个全局事件")
        
        for idx, event in enumerate(global_events, 1):
            logger.info(f"   事件 #{idx}: {len(event.get('clips', []))} 个 Clip, "
                       f"{len(event.get('people', set()))} 个人物")
    except Exception as e:
        logger.error(f"❌ Phase 2 处理失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # ========== Phase 3: LLM 语义生成 ==========
    logger.info("\n" + "=" * 60)
    logger.info("Phase 3: LLM 语义生成")
    logger.info("=" * 60)
    
    try:
        llm_pipeline = LLM_Reasoning_Pipeline()
        logger.info("✅ Phase 3 Pipeline 初始化成功")
    except Exception as e:
        logger.error(f"❌ Phase 3 Pipeline 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    logger.info("\n开始生成事件日志...")
    try:
        processed_events = llm_pipeline.process_events(global_events)
        logger.info(f"✅ Phase 3 完成: {len(processed_events)} 个事件已生成日志")
        
        # 显示部分生成的日志
        for idx, event in enumerate(processed_events[:3], 1):  # 只显示前3个
            if event.get('summary_text'):
                logger.info(f"\n   事件 #{idx} 日志:")
                logger.info(f"   {event['summary_text'][:150]}...")
    except Exception as e:
        logger.error(f"❌ Phase 3 处理失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # ========== Phase 4: 结构化落库 ==========
    logger.info("\n" + "=" * 60)
    logger.info("Phase 4: 结构化落库")
    logger.info("=" * 60)
    
    try:
        persistence_pipeline = Persistence_Pipeline()
        logger.info("✅ Phase 4 Pipeline 初始化成功")
    except Exception as e:
        logger.error(f"❌ Phase 4 Pipeline 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    logger.info("\n开始保存事件到数据库...")
    try:
        saved_event_ids = persistence_pipeline.save_events(processed_events)
        logger.info(f"✅ Phase 4 完成: 成功保存 {len(saved_event_ids)} 个事件到数据库")
    except Exception as e:
        logger.error(f"❌ Phase 4 处理失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # ========== Phase 5: 每日总结生成 ==========
    logger.info("\n" + "=" * 60)
    logger.info("Phase 5: 每日总结生成")
    logger.info("=" * 60)
    
    try:
        summary_pipeline = Daily_Summary_Pipeline()
        logger.info("✅ Phase 5 Pipeline 初始化成功")
    except Exception as e:
        logger.error(f"❌ Phase 5 Pipeline 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    logger.info("\n开始生成每日总结...")
    try:
        # 获取处理的事件日期
        if processed_events:
            # 从第一个事件获取日期
            first_event_date = processed_events[0]['start_time'].strftime('%Y-%m-%d')
            logger.info(f"📅 处理日期: {first_event_date}")
            
            # 生成该日期的总结
            summary_record_id = summary_pipeline.run_for_date(first_event_date, force_update=True)
            
            if summary_record_id:
                logger.info(f"✅ Phase 5 完成: 成功生成日期 {first_event_date} 的总结 (record_id={summary_record_id})")
                
                # 查询并显示生成的总结
                summary = summary_pipeline.persister.get_summary(first_event_date)
                if summary:
                    logger.info(f"\n📝 生成的每日总结:")
                    logger.info(f"   日期: {summary['summary_date']}")
                    logger.info(f"   事件数: {summary['total_events']}")
                    logger.info(f"   总结内容:")
                    logger.info(f"   {summary['summary_text']}")
            else:
                logger.warning(f"⚠️  日期 {first_event_date} 没有事件记录，无法生成总结")
        else:
            logger.warning("⚠️  没有处理的事件，跳过 Phase 5")
            
    except Exception as e:
        logger.error(f"❌ Phase 5 处理失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # ========== 最终结果展示 ==========
    logger.info("\n" + "=" * 60)
    logger.info("完整流程结果")
    logger.info("=" * 60)
    
    logger.info(f"\n📊 处理统计:")
    logger.info(f"   Phase 1: {len(clip_objs)} 个 Clip_Obj")
    logger.info(f"   Phase 2: {len(global_events)} 个全局事件")
    logger.info(f"   Phase 3: {len(processed_events)} 个事件已生成日志")
    logger.info(f"   Phase 4: {len(saved_event_ids)} 个事件已保存到数据库")
    
    if processed_events:
        first_event_date = processed_events[0]['start_time'].strftime('%Y-%m-%d')
        summary = summary_pipeline.persister.get_summary(first_event_date)
        if summary:
            logger.info(f"   Phase 5: 日期 {first_event_date} 的总结已生成")
    
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
    logger.info("\n📝 下一步:")
    logger.info("   - Phase 6: 用户检索与 RAG")


if __name__ == '__main__':
    main()

