#!/usr/bin/env python3
"""
测试脚本：验证第二阶段 Pipeline 的功能
"""

import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from workflow.phase2_event_fusion import Event_Fusion_Pipeline

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def create_mock_clips():
    """
    创建模拟的 Clip_Obj 数据（用于测试）
    
    Returns:
        List[Dict]: 模拟的 Clip_Obj 列表
    """
    base_time = datetime(2025, 9, 1, 9, 0, 0)
    
    clips = [
        # 事件1: Dad 回家（3个连续 Clip）
        {
            'time': base_time,
            'cam': 'outdoor_high',
            'people_detected': [
                [
                    {'person_id': 1, 'role': 'family', 'method': 'face', 
                     'bbox': (100, 100, 200, 300), 'confidence': 0.9}
                ]
            ]
        },
        {
            'time': base_time + timedelta(seconds=15),
            'cam': 'doorbell',
            'people_detected': [
                [
                    {'person_id': 1, 'role': 'family', 'method': 'body', 
                     'bbox': (150, 120, 250, 320), 'confidence': 0.85}
                ]
            ]
        },
        {
            'time': base_time + timedelta(seconds=30),
            'cam': 'indoor_living',
            'people_detected': [
                [
                    {'person_id': 1, 'role': 'family', 'method': 'face', 
                     'bbox': (200, 150, 300, 350), 'confidence': 0.95}
                ]
            ]
        },
        
        # 事件2: 陌生人路过（1个 Clip，时间间隔 > 60秒）
        {
            'time': base_time + timedelta(minutes=1, seconds=30),
            'cam': 'doorbell',
            'people_detected': [
                [
                    {'person_id': None, 'role': 'stranger', 'method': 'new', 
                     'bbox': (100, 100, 200, 300), 'confidence': 0.8}
                ]
            ]
        },
        
        # 事件3: Mom 和 Dad 一起出现（2个连续 Clip）
        {
            'time': base_time + timedelta(minutes=2),
            'cam': 'outdoor_high',
            'people_detected': [
                [
                    {'person_id': 1, 'role': 'family', 'method': 'face', 
                     'bbox': (100, 100, 200, 300), 'confidence': 0.9},
                    {'person_id': 2, 'role': 'family', 'method': 'face', 
                     'bbox': (300, 100, 400, 300), 'confidence': 0.88}
                ]
            ]
        },
        {
            'time': base_time + timedelta(minutes=2, seconds=20),
            'cam': 'indoor_living',
            'people_detected': [
                [
                    {'person_id': 1, 'role': 'family', 'method': 'body', 
                     'bbox': (150, 120, 250, 320), 'confidence': 0.85},
                    {'person_id': 2, 'role': 'family', 'method': 'body', 
                     'bbox': (350, 120, 450, 320), 'confidence': 0.83}
                ]
            ]
        },
    ]
    
    return clips


def main():
    """主测试函数"""
    logger.info("=" * 60)
    logger.info("第二阶段 Pipeline 测试")
    logger.info("=" * 60)
    
    # 创建模拟数据
    logger.info("\n📝 创建模拟 Clip 数据...")
    mock_clips = create_mock_clips()
    logger.info(f"✅ 创建了 {len(mock_clips)} 个模拟 Clip")
    
    # 初始化 Pipeline
    try:
        pipeline = Event_Fusion_Pipeline(time_threshold=60)
        logger.info("✅ Pipeline 初始化成功")
    except Exception as e:
        logger.error(f"❌ Pipeline 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 运行事件融合
    logger.info("\n" + "=" * 60)
    logger.info("开始运行事件融合流程")
    logger.info("=" * 60)
    
    try:
        global_events = pipeline.run(mock_clips)
        
        logger.info("\n" + "=" * 60)
        logger.info("处理结果")
        logger.info("=" * 60)
        
        for idx, event in enumerate(global_events, 1):
            logger.info(f"\n📦 全局事件 #{idx}:")
            logger.info(f"   开始时间: {event['start_time']}")
            logger.info(f"   结束时间: {event['end_time']}")
            logger.info(f"   持续时间: {event['duration']:.0f} 秒")
            logger.info(f"   摄像头: {', '.join(event['cameras'])}")
            logger.info(f"   人物数量: {len(event['people'])}")
            logger.info(f"   人物ID: {list(event['people'])}")
            logger.info(f"   Clip 数量: {event['clip_count']}")
            
            # 显示 Prompt
            if event.get('prompt_text'):
                logger.info(f"\n   Prompt 文本:")
                for line in event['prompt_text'].split('\n'):
                    logger.info(f"      {line}")
        
        logger.info(f"\n✅ 测试完成: 成功生成 {len(global_events)} 个全局事件")
        
    except Exception as e:
        logger.error(f"❌ 处理失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()

