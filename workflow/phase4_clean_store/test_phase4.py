#!/usr/bin/env python3
"""
Phase 4 测试脚本
测试结构化落库功能
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from workflow.phase4_clean_store import Persistence_Pipeline
import numpy as np

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def create_mock_global_event() -> dict:
    """创建模拟的 Global_Event 对象"""
    
    # 创建模拟的身体特征向量（2048维）
    def create_mock_body_embedding() -> np.ndarray:
        return np.random.rand(2048).astype(np.float32)
    
    # 创建模拟的 Clip
    clip1 = {
        'time': datetime(2025, 9, 1, 9, 0, 0),
        'cam': 'doorbell',
        'video_duration': 26.47,
        'video_path': '/path/to/video1.mp4',
        'people_detected': [
            [  # 第1帧
                {
                    'person_id': 21,
                    'role': 'family',
                    'method': 'face',
                    'confidence': 0.95,
                    'bbox': (100, 100, 200, 300),
                    'body_embedding': create_mock_body_embedding()
                },
                {
                    'person_id': 22,
                    'role': 'family',
                    'method': 'body',
                    'confidence': 0.85,
                    'bbox': (300, 150, 400, 350),
                    'body_embedding': create_mock_body_embedding()
                }
            ],
            [  # 第2帧
                {
                    'person_id': 21,
                    'role': 'family',
                    'method': 'face',
                    'confidence': 0.92,
                    'bbox': (110, 110, 210, 310),
                    'body_embedding': create_mock_body_embedding()
                }
            ]
        ]
    }
    
    clip2 = {
        'time': datetime(2025, 9, 1, 9, 0, 15),
        'cam': 'outdoor_high',
        'video_duration': 26.33,
        'video_path': '/path/to/video2.mp4',
        'people_detected': [
            [
                {
                    'person_id': 21,
                    'role': 'family',
                    'method': 'body',
                    'confidence': 0.88,
                    'bbox': (150, 120, 250, 320),
                    'body_embedding': create_mock_body_embedding()
                }
            ]
        ]
    }
    
    # 创建 Global_Event
    global_event = {
        'start_time': datetime(2025, 9, 1, 9, 0, 0),
        'end_time': datetime(2025, 9, 1, 9, 0, 30),
        'duration': 30.0,
        'cameras': ['doorbell', 'outdoor_high'],
        'people': {21, 22},
        'people_info': {
            21: {
                'person_id': 21,
                'role': 'family',
                'method': 'face',
                'first_seen': datetime(2025, 9, 1, 9, 0, 0),
                'last_seen': datetime(2025, 9, 1, 9, 0, 15),
                'cameras': ['doorbell', 'outdoor_high']
            },
            22: {
                'person_id': 22,
                'role': 'family',
                'method': 'body',
                'first_seen': datetime(2025, 9, 1, 9, 0, 0),
                'last_seen': datetime(2025, 9, 1, 9, 0, 0),
                'cameras': ['doorbell']
            }
        },
        'clips': [clip1, clip2],
        'keyframes': {},
        'clip_count': 2,
        'summary_text': '09:00，家人(Person_21)和家人(Person_22)出现在门口，随后Person_21移动到庭院。'
    }
    
    return global_event


def test_phase4():
    """测试 Phase 4"""
    logger.info("=" * 60)
    logger.info("Phase 4: 结构化落库测试")
    logger.info("=" * 60)
    
    # 创建模拟数据
    logger.info("\n📝 创建模拟 Global_Event 数据...")
    global_event = create_mock_global_event()
    logger.info(f"✅ 创建完成: 时间={global_event['start_time']}, "
               f"摄像头={global_event['cameras']}, "
               f"人物={list(global_event['people'])}")
    
    # 初始化 Pipeline
    logger.info("\n🔧 初始化 Persistence Pipeline...")
    try:
        pipeline = Persistence_Pipeline()
        logger.info("✅ Pipeline 初始化成功")
    except Exception as e:
        logger.error(f"❌ Pipeline 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 保存事件
    logger.info("\n" + "=" * 60)
    logger.info("开始保存事件到数据库")
    logger.info("=" * 60)
    
    try:
        event_id = pipeline.save_event(global_event)
        
        if event_id:
            logger.info(f"\n✅ 测试成功: 事件已保存，event_id={event_id}")
            return True
        else:
            logger.error("\n❌ 测试失败: 事件保存失败")
            return False
            
    except Exception as e:
        logger.error(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = test_phase4()
    sys.exit(0 if success else 1)

