#!/usr/bin/env python3
"""
测试脚本：验证第三阶段 Pipeline 的功能
"""

import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from workflow.phase3_agent_interaction import LLM_Reasoning_Pipeline

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def create_mock_global_events():
    """
    创建模拟的 Global_Event 数据（用于测试）
    
    Returns:
        List[Dict]: 模拟的 Global_Event 列表
    """
    base_time = datetime(2025, 9, 1, 9, 0, 0)
    
    events = [
        {
            'start_time': base_time,
            'end_time': base_time + timedelta(seconds=30),
            'duration': 30.0,
            'cameras': ['outdoor_high', 'doorbell', 'indoor_living'],
            'people': {1, 2},
            'people_info': {
                1: {
                    'person_id': 1,
                    'role': 'family',
                    'method': 'face',
                    'first_seen': base_time,
                    'last_seen': base_time + timedelta(seconds=30),
                    'cameras': ['outdoor_high', 'doorbell', 'indoor_living']
                },
                2: {
                    'person_id': 2,
                    'role': 'family',
                    'method': 'face',
                    'first_seen': base_time,
                    'last_seen': base_time + timedelta(seconds=30),
                    'cameras': ['outdoor_high', 'indoor_living']
                }
            },
            'clips': [
                {
                    'time': base_time,
                    'cam': 'outdoor_high',
                    'people_detected': [[
                        {'person_id': 1, 'role': 'family', 'method': 'face'},
                        {'person_id': 2, 'role': 'family', 'method': 'face'}
                    ]]
                },
                {
                    'time': base_time + timedelta(seconds=15),
                    'cam': 'doorbell',
                    'people_detected': [[
                        {'person_id': 1, 'role': 'family', 'method': 'body'}
                    ]]
                },
                {
                    'time': base_time + timedelta(seconds=30),
                    'cam': 'indoor_living',
                    'people_detected': [[
                        {'person_id': 1, 'role': 'family', 'method': 'face'},
                        {'person_id': 2, 'role': 'family', 'method': 'face'}
                    ]]
                }
            ],
            'keyframes': {},
            'prompt_text': """Plaintext时间线：
- 09:00:00 [outdoor_high]: 家人(Person_1)、家人(Person_2) 出现
- 09:00:15 [doorbell]: 家人(Person_1) 出现
- 09:00:30 [indoor_living]: 家人(Person_1)、家人(Person_2) 出现
提示: 人物从室外移动到室内
任务：生成一条连贯的中文日志，描述这个事件的完整过程。""",
            'clip_count': 3
        },
        {
            'start_time': base_time + timedelta(minutes=1, seconds=30),
            'end_time': base_time + timedelta(minutes=1, seconds=30),
            'duration': 0.0,
            'cameras': ['doorbell'],
            'people': set(),
            'people_info': {},
            'clips': [
                {
                    'time': base_time + timedelta(minutes=1, seconds=30),
                    'cam': 'doorbell',
                    'people_detected': [[
                        {'person_id': None, 'role': 'stranger', 'method': 'new'}
                    ]]
                }
            ],
            'keyframes': {},
            'prompt_text': """Plaintext时间线：
- 09:01:30 [doorbell]: 陌生人 出现
任务：生成一条连贯的中文日志，描述这个事件的完整过程。""",
            'clip_count': 1
        }
    ]
    
    return events


def main():
    """主测试函数"""
    logger.info("=" * 60)
    logger.info("第三阶段 Pipeline 测试")
    logger.info("=" * 60)
    
    # 创建模拟数据
    logger.info("\n📝 创建模拟 Global_Event 数据...")
    mock_events = create_mock_global_events()
    logger.info(f"✅ 创建了 {len(mock_events)} 个模拟事件")
    
    # 初始化 Pipeline
    try:
        pipeline = LLM_Reasoning_Pipeline(
            model_name='gemini-2.5-flash-lite',
            temperature=0.2,
            max_output_tokens=256
        )
        logger.info("✅ Pipeline 初始化成功")
    except Exception as e:
        logger.error(f"❌ Pipeline 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 运行 LLM 语义生成
    logger.info("\n" + "=" * 60)
    logger.info("开始运行 LLM 语义生成流程")
    logger.info("=" * 60)
    
    try:
        processed_events = pipeline.process_events(mock_events)
        
        logger.info("\n" + "=" * 60)
        logger.info("处理结果")
        logger.info("=" * 60)
        
        for idx, event in enumerate(processed_events, 1):
            logger.info(f"\n📝 事件 #{idx}:")
            logger.info(f"   时间: {event['start_time']} ~ {event['end_time']}")
            logger.info(f"   人物: {list(event['people'])} ({len(event['people'])} 个)")
            logger.info(f"   生成日志: {event.get('summary_text', 'N/A')}")
            logger.info(f"   有效: {event.get('llm_valid', False)}")
            if event.get('llm_warnings'):
                logger.warning(f"   ⚠️  警告: {event['llm_warnings']}")
        
        logger.info(f"\n✅ 测试完成: 成功处理 {len(processed_events)} 个事件")
        
    except Exception as e:
        logger.error(f"❌ 处理失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()

