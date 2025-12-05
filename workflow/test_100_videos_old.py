#!/usr/bin/env python3
"""
100个视频的强度测试脚本
测试完整的 Phase 1-5 流程，处理100个视频
包含性能监控和进度跟踪
"""

import sys
import logging
import time
from pathlib import Path
from datetime import datetime

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
        logger.info("🚀 开始性能测试：处理100个视频")
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
    从视频中提取人物特征，优先通过人脸匹配确认身份
    """
    from workflow.phase1_cv_scanning import (
        DataLoader,
        FrameSampler,
        YoloDetector,
        FeatureEncoder,
        IdentityArbiter
    )
    import psycopg2
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    logger.info("=" * 80)
    logger.info("创建初始身体特征缓存")
    logger.info("=" * 80)
    
    # 获取项目根目录
    project_root_local = Path('.')
    
    # 初始化组件
    dataset_json = project_root_local / 'memories_ai_benchmark' / 'long_mem_dataset.json'
    videos_dir = project_root_local / 'memories_ai_benchmark' / 'videos'
    
    loader = DataLoader(str(dataset_json), str(videos_dir))
    sampler = FrameSampler()
    detector = YoloDetector('yolov8n.pt', conf_threshold=0.3)
    encoder = FeatureEncoder(face_model_name='buffalo_l', reid_model_name='osnet_x1_0')
    arbiter = IdentityArbiter()
    
    # 获取所有家人ID
    db_config = {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': os.getenv('POSTGRES_PORT', '5432'),
        'database': os.getenv('POSTGRES_DB', 'neweufy'),
        'user': os.getenv('POSTGRES_USER', 'postgres'),
        'password': os.getenv('POSTGRES_PASSWORD', 'eufy123')
    }
    
    try:
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        cur.execute("SELECT id FROM persons WHERE role = 'owner' ORDER BY id")
        all_family_ids = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()
        logger.info(f"📋 需要为 {len(all_family_ids)} 个家人找到身体特征")
    except Exception as e:
        logger.error(f"❌ 无法获取家人列表: {e}")
        return False
    
    if not all_family_ids:
        logger.warning("⚠️  没有找到家人记录，跳过身体特征缓存")
        return False
    
    # 获取所有视频记录
    all_records = loader.get_all_records()
    records_to_process = all_records[:max_videos]
    logger.info(f"📹 将从前 {len(records_to_process)} 个视频中寻找有正脸的帧...")
    
    matched_persons = {}  # {person_id: {body_vec, ...}}
    
    for idx, record in enumerate(records_to_process, 1):
        if len(matched_persons) >= len(all_family_ids):
            logger.info(f"✅ 已为所有家人找到身体特征，提前结束")
            break
        
        video_path = record.get('video_path')
        if not video_path or not Path(video_path).exists():
            continue
        
        logger.info(f"[{idx}/{len(records_to_process)}] 处理视频: {Path(video_path).name}")
        
        # 采样帧
        frames, _ = sampler.get_frames(video_path, fps=1.0)
        if not frames:
            continue
        
        # 检测人物
        for frame_idx, frame in enumerate(frames):
            detections = detector.detect(frame)
            if not detections:
                continue
            
            # 提取特征并识别
            for det in detections:
                if det.class_id != 0:  # 只处理 person 类
                    continue
                
                # 提取特征
                vectors = encoder.encode(frame, det.bbox)
                if not vectors.get('face_vec') and not vectors.get('body_vec'):
                    continue
                
                # 识别身份
                identity = arbiter.identify(vectors, datetime.now())
                
                if identity.get('role') == 'family' and identity.get('person_id'):
                    person_id = identity['person_id']
                    
                    # 如果这个人还没有缓存，且有人脸匹配（确保身份正确）
                    if person_id not in matched_persons and identity.get('method') == 'face':
                        body_vec = vectors.get('body_vec')
                        if body_vec is not None:
                            matched_persons[person_id] = {
                                'body_vec': body_vec,
                                'match_method': 'face',
                                'video_path': video_path,
                                'frame_idx': frame_idx
                            }
                            logger.info(f"   ✅ 找到 Person_{person_id} 的身体特征（通过人脸确认）")
                            
                            if len(matched_persons) >= len(all_family_ids):
                                break
            
            if len(matched_persons) >= len(all_family_ids):
                break
    
    # 保存到数据库
    if matched_persons:
        logger.info(f"\n💾 保存 {len(matched_persons)} 个身体特征到数据库...")
        try:
            conn = psycopg2.connect(**db_config)
            conn.autocommit = False
            cur = conn.cursor()
            
            saved_count = 0
            for person_id, data in matched_persons.items():
                body_vec = data['body_vec']
                body_vec_str = '[' + ','.join(map(str, body_vec)) + ']'
                
                cur.execute("""
                    UPDATE persons
                    SET current_body_embedding = %s::vector,
                        body_update_time = %s,
                        last_seen = %s
                    WHERE id = %s
                """, (body_vec_str, datetime.now(), datetime.now(), person_id))
                
                saved_count += 1
            
            conn.commit()
            cur.close()
            conn.close()
            
            logger.info(f"✅ 成功保存 {saved_count} 个身体特征缓存")
            return True
        except Exception as e:
            logger.error(f"❌ 保存失败: {e}")
            return False
    else:
        logger.warning("⚠️  没有找到任何身体特征")
        return False


def main():
    """主函数：处理100个视频"""
    monitor = PerformanceMonitor()
    monitor.start()
    
    global project_root
    project_root = Path('.')
    
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
        lib_path = project_root / 'memories_ai_benchmark' / 'lib'
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
    
    # ========== Phase 1: 视觉扫描与特征提取 ==========
    monitor.start_phase("Phase 1: 视觉扫描与特征提取")
    
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
        
        # 处理100个视频
        clip_objs = cv_pipeline.process_all_clips(max_clips=100)
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
        
        # 显示事件统计
        logger.info(f"\n📊 事件统计:")
        for idx, event in enumerate(global_events[:10], 1):  # 只显示前10个
            logger.info(f"   事件 #{idx}: {len(event.get('clips', []))} 个 Clip, "
                       f"{len(event.get('people', set()))} 个人物")
        if len(global_events) > 10:
            logger.info(f"   ... 还有 {len(global_events) - 10} 个事件")
        
    except Exception as e:
        logger.error(f"❌ Phase 2 失败: {e}")
        import traceback
        traceback.print_exc()
        monitor.end_phase("Phase 2: 时空事件合并", 0)
        return
    
    if not global_events:
        logger.warning("⚠️  没有生成任何全局事件，终止测试")
        return
    
    # ========== Phase 3: LLM 语义生成 ==========
    monitor.start_phase("Phase 3: LLM 语义生成")
    
    try:
        llm_pipeline = LLM_Reasoning_Pipeline()
        logger.info("✅ Phase 3 Pipeline 初始化成功")
        
        processed_events = llm_pipeline.process_events(global_events)
        monitor.end_phase("Phase 3: LLM 语义生成", len(processed_events))
        
        # 显示部分生成的日志
        logger.info(f"\n📝 生成的日志示例（前3个）:")
        for idx, event in enumerate(processed_events[:3], 1):
            if event.get('summary_text'):
                logger.info(f"\n   事件 #{idx}:")
                logger.info(f"   {event['summary_text'][:200]}...")
        
    except Exception as e:
        logger.error(f"❌ Phase 3 失败: {e}")
        import traceback
        traceback.print_exc()
        monitor.end_phase("Phase 3: LLM 语义生成", 0)
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
    logger.info("✅ 100个视频处理测试完成！")
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

