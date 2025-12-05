#!/usr/bin/env python3
"""
50个视频的强度测试脚本
测试完整的 Phase 1-5 流程，处理50个视频
包含性能监控和进度跟踪
"""

import sys
import logging
import time
from pathlib import Path
from datetime import datetime
import importlib.util

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from workflow import (
    Phase0Initialization,
    CV_Pipeline,
    Event_Fusion_Pipeline,
    LLM_Reasoning_Pipeline,
    Persistence_Pipeline,
    Daily_Summary_Pipeline
)
from workflow.clear_database import clear_database

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'/tmp/test_100_videos_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.start_time = None
        self.phase_times = {}
        self.current_phase = None
    
    def start(self):
        """开始计时"""
        self.start_time = time.time()
        logger.info("=" * 80)
        logger.info("🚀 开始性能测试：处理50个视频")
        logger.info("=" * 80)
    
    def start_phase(self, phase_name: str):
        """开始一个阶段"""
        self.current_phase = phase_name
        self.phase_times[phase_name] = {'start': time.time()}
        logger.info(f"\n{'='*80}")
        logger.info(f"📊 开始 {phase_name}")
        logger.info(f"{'='*80}")
    
    def end_phase(self, phase_name: str, result_count: int = None):
        """结束一个阶段"""
        if phase_name in self.phase_times:
            elapsed = time.time() - self.phase_times[phase_name]['start']
            self.phase_times[phase_name]['elapsed'] = elapsed
            self.phase_times[phase_name]['result_count'] = result_count
            
            logger.info(f"\n✅ {phase_name} 完成")
            logger.info(f"   耗时: {elapsed:.2f} 秒 ({elapsed/60:.2f} 分钟)")
            if result_count is not None:
                logger.info(f"   结果数量: {result_count}")
                if elapsed > 0:
                    logger.info(f"   处理速度: {result_count/elapsed:.2f} 个/秒")
    
    def print_summary(self):
        """打印性能总结"""
        total_time = time.time() - self.start_time
        
        logger.info("\n" + "=" * 80)
        logger.info("📊 性能测试总结")
        logger.info("=" * 80)
        
        logger.info(f"\n⏱️  总耗时: {total_time:.2f} 秒 ({total_time/60:.2f} 分钟)")
        
        logger.info(f"\n📈 各阶段耗时:")
        for phase_name, times in self.phase_times.items():
            elapsed = times.get('elapsed', 0)
            percentage = (elapsed / total_time * 100) if total_time > 0 else 0
            result_count = times.get('result_count', 'N/A')
            logger.info(f"   {phase_name:30s}: {elapsed:8.2f}秒 ({percentage:5.1f}%) - {result_count} 个结果")
        
        logger.info("\n" + "=" * 80)


def create_initial_body_cache(max_videos=10):
    """
    创建初始身体特征缓存
    调用独立的 create_initial_body_cache.py 脚本，确保通过人脸匹配确认身份后再提取身体特征
    """
    # 导入独立的 create_initial_body_cache 模块
    cache_script_path = project_root / 'workflow' / 'create_initial_body_cache.py'
    
    if not cache_script_path.exists():
        logger.error(f"❌ 找不到 create_initial_body_cache.py: {cache_script_path}")
        return False
    
    try:
        # 动态导入模块
        spec = importlib.util.spec_from_file_location("create_initial_body_cache", cache_script_path)
        cache_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cache_module)
        
        logger.info("=" * 80)
        logger.info("创建初始身体特征缓存（使用独立脚本）")
        logger.info("=" * 80)
        logger.info("\n策略:")
        logger.info("1. 从多个视频中寻找有正脸的帧，通过人脸匹配确认身份")
        logger.info("2. 确保人脸和身体特征对应的是同一个人")
        logger.info("3. 如果没有正脸，使用背影特征（但会给出警告）")
        logger.info("")
        
        # 调用 find_faces_in_videos 函数
        matched_persons = cache_module.find_faces_in_videos(max_videos=max_videos)
        
        # 为缺失的家人提取背影特征
        matched_persons = cache_module.extract_backs_for_missing(matched_persons, max_videos=5)
        
        if not matched_persons:
            logger.warning("⚠️  未能提取到身体特征")
            return False
        
        # 保存到数据库
        cache_module.save_to_database(matched_persons)
        
        logger.info("\n✅ 初始身体特征缓存创建完成")
        return True
        
    except Exception as e:
        logger.error(f"❌ 创建身体特征缓存失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数：处理50个视频"""
    monitor = PerformanceMonitor()
    monitor.start()
    
    project_root_local = Path('.')
    
    # ========== 初始化步骤：清空数据库 ==========
    monitor.start_phase("初始化: 清空数据库")
    try:
        success = clear_database(confirm=True)  # 自动确认，不需要交互
        if success:
            monitor.end_phase("初始化: 清空数据库", 1)
        else:
            logger.error("❌ 数据库清空失败")
            return
    except Exception as e:
        logger.error(f"❌ 数据库清空失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # ========== 初始化步骤：加载家人人脸底库 ==========
    monitor.start_phase("初始化: 加载家人人脸底库 (Phase 0)")
    try:
        lib_path = project_root_local / 'memories_ai_benchmark' / 'lib'
        if not lib_path.exists():
            logger.error(f"❌ 底库文件夹不存在: {lib_path}")
            logger.info("💡 提示: 请确保 memories_ai_benchmark/lib/ 文件夹存在并包含家人照片")
            return
        
        phase0 = Phase0Initialization()
        phase0.run(str(lib_path))
        monitor.end_phase("初始化: 加载家人人脸底库 (Phase 0)", 1)
        logger.info("✅ 家人人脸底库加载完成")
    except Exception as e:
        logger.error(f"❌ Phase 0 失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # ========== 初始化步骤：创建初始身体特征缓存 ==========
    monitor.start_phase("初始化: 创建初始身体特征缓存")
    try:
        success = create_initial_body_cache(max_videos=10)
        monitor.end_phase("初始化: 创建初始身体特征缓存", 1 if success else 0)
    except Exception as e:
        logger.error(f"❌ 创建身体特征缓存失败: {e}")
        import traceback
        traceback.print_exc()
        # 继续执行，不中断测试
    
    # ========== Phase 1: 视觉扫描与特征提取 ==========
    monitor.start_phase("Phase 1: 视觉扫描与特征提取")
    
    try:
        cv_pipeline = CV_Pipeline(
            dataset_json_path=str(project_root_local / 'memories_ai_benchmark' / 'long_mem_dataset.json'),
            videos_base_dir=str(project_root_local / 'memories_ai_benchmark' / 'videos'),
            yolo_model='yolov8n.pt',
            face_model_name='buffalo_l',
            reid_model_name='osnet_x1_0',
            enable_tracking=True
        )
        logger.info("✅ Phase 1 Pipeline 初始化成功")
        
        # 处理50个视频
        clip_objs = cv_pipeline.process_all_clips(max_clips=50)
        monitor.end_phase("Phase 1: 视觉扫描与特征提取", len(clip_objs))
        
    except Exception as e:
        logger.error(f"❌ Phase 1 失败: {e}")
        import traceback
        traceback.print_exc()
        monitor.end_phase("Phase 1: 视觉扫描与特征提取", 0)
        return
    
    if not clip_objs:
        logger.warning("⚠️  没有生成任何 Clip_Obj，终止测试")
        return
    
    # ========== Phase 2: 时空事件合并 ==========
    monitor.start_phase("Phase 2: 时空事件合并")
    
    try:
        fusion_pipeline = Event_Fusion_Pipeline(time_threshold=60)
        logger.info("✅ Phase 2 Pipeline 初始化成功")
        
        global_events = fusion_pipeline.run(clip_objs)
        monitor.end_phase("Phase 2: 时空事件合并", len(global_events))
        
    except Exception as e:
        logger.error(f"❌ Phase 2 失败: {e}")
        import traceback
        traceback.print_exc()
        monitor.end_phase("Phase 2: 时空事件合并", 0)
        return
    
    if not global_events:
        logger.warning("⚠️  没有生成任何全局事件，终止测试")
        return
    
    # ========== Phase 3: 宏观语义生成 ==========
    monitor.start_phase("Phase 3: 宏观语义生成")
    
    try:
        llm_pipeline = LLM_Reasoning_Pipeline()
        logger.info("✅ Phase 3 Pipeline 初始化成功")
        
        processed_events = llm_pipeline.process_events(global_events)
        monitor.end_phase("Phase 3: 宏观语义生成", len(processed_events))
        
    except Exception as e:
        logger.error(f"❌ Phase 3 失败: {e}")
        import traceback
        traceback.print_exc()
        monitor.end_phase("Phase 3: 宏观语义生成", 0)
        return
    
    # ========== Phase 4: 结构化落库 ==========
    monitor.start_phase("Phase 4: 结构化落库")
    
    try:
        persistence_pipeline = Persistence_Pipeline()
        logger.info("✅ Phase 4 Pipeline 初始化成功")
        
        saved_event_ids = persistence_pipeline.save_events(processed_events)
        monitor.end_phase("Phase 4: 结构化落库", len(saved_event_ids))
        
    except Exception as e:
        logger.error(f"❌ Phase 4 失败: {e}")
        import traceback
        traceback.print_exc()
        monitor.end_phase("Phase 4: 结构化落库", 0)
        return
    
    # ========== Phase 5: 每日总结生成 ==========
    monitor.start_phase("Phase 5: 每日总结生成")
    
    try:
        summary_pipeline = Daily_Summary_Pipeline()
        logger.info("✅ Phase 5 Pipeline 初始化成功")
        
        if processed_events:
            # 获取所有事件的日期
            dates = set()
            for event in processed_events:
                date_str = event['start_time'].strftime('%Y-%m-%d')
                dates.add(date_str)
            
            logger.info(f"📅 需要生成总结的日期: {sorted(dates)}")
            
            summary_count = 0
            for date_str in sorted(dates):
                summary_record_id = summary_pipeline.run_for_date(date_str, force_update=True)
                if summary_record_id:
                    summary_count += 1
                    logger.info(f"   ✅ 日期 {date_str} 的总结已生成")
            
            monitor.end_phase("Phase 5: 每日总结生成", summary_count)
        else:
            logger.warning("⚠️  没有处理的事件，跳过 Phase 5")
            monitor.end_phase("Phase 5: 每日总结生成", 0)
            
    except Exception as e:
        logger.error(f"❌ Phase 5 失败: {e}")
        import traceback
        traceback.print_exc()
        monitor.end_phase("Phase 5: 每日总结生成", 0)
    
    # ========== 最终总结 ==========
    monitor.print_summary()
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ 50个视频处理测试完成！")
    logger.info("=" * 80)
    
    logger.info(f"\n📊 处理统计:")
    logger.info(f"   Phase 1: {len(clip_objs)} 个 Clip_Obj")
    logger.info(f"   Phase 2: {len(global_events)} 个全局事件")
    logger.info(f"   Phase 3: {len(processed_events)} 个事件已生成日志")
    logger.info(f"   Phase 4: {len(saved_event_ids)} 个事件已保存到数据库")
    
    logger.info("\n💡 提示:")
    logger.info("   - 日志文件已保存到 /tmp/test_100_videos_*.log")
    logger.info("   - 可以使用 Phase 6 进行用户检索测试")


if __name__ == '__main__':
    main()

