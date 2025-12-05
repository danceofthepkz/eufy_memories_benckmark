#!/usr/bin/env python3
"""
测试脚本：验证第一阶段 Pipeline 的功能
"""

import sys
import os
import logging
from pathlib import Path

# 添加项目根目录到路径（从 workflow/phase1_cv_scanning/ 向上两级到项目根）
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from workflow import CV_Pipeline

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """主测试函数"""
    logger.info("=" * 60)
    logger.info("第一阶段 Pipeline 测试")
    logger.info("=" * 60)
    
    # 检查数据文件是否存在
    dataset_json = project_root / 'memories_ai_benchmark' / 'long_mem_dataset.json'
    videos_dir = project_root / 'memories_ai_benchmark' / 'videos'
    
    if not dataset_json.exists():
        logger.error(f"❌ 数据集文件不存在: {dataset_json}")
        return
    
    if not videos_dir.exists():
        logger.error(f"❌ 视频目录不存在: {videos_dir}")
        return
    
    # 初始化 Pipeline
    try:
        pipeline = CV_Pipeline(
            dataset_json_path=str(dataset_json),
            videos_base_dir=str(videos_dir),
            yolo_model='yolov8n.pt',
            face_model_name='buffalo_l',
            reid_model_name='osnet_x1_0'  # 使用真正的 ReID 模型
        )
        logger.info("✅ Pipeline 初始化成功")
    except Exception as e:
        logger.error(f"❌ Pipeline 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 测试处理前3个视频
    logger.info("\n" + "=" * 60)
    logger.info("开始处理视频（测试：前3个）")
    logger.info("=" * 60)
    
    try:
        clip_objs = pipeline.process_all_clips(max_clips=3)
        
        logger.info("\n" + "=" * 60)
        logger.info("处理结果统计")
        logger.info("=" * 60)
        
        for idx, clip_obj in enumerate(clip_objs, 1):
            logger.info(f"\n📹 Clip {idx}:")
            logger.info(f"   摄像头: {clip_obj['cam']}")
            logger.info(f"   时间: {clip_obj['time']}")
            logger.info(f"   帧数: {len(clip_obj['people_detected'])}")
            
            total_detections = sum(len(p) for p in clip_obj['people_detected'])
            logger.info(f"   检测次数: {total_detections}")
            
            # 统计身份信息
            family_count = 0
            stranger_count = 0
            for frame_people in clip_obj['people_detected']:
                for person in frame_people:
                    if person.get('role') == 'family':
                        family_count += 1
                    elif person.get('role') == 'stranger':
                        stranger_count += 1
            
            logger.info(f"   家人: {family_count}, 陌生人: {stranger_count}")
        
        logger.info(f"\n✅ 测试完成: 成功处理 {len(clip_objs)} 个视频片段")
        
    except Exception as e:
        logger.error(f"❌ 处理失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()

