#!/usr/bin/env python3
"""
测试脚本：验证 Phase 0 (系统初始化) 的功能
"""

import sys
import os
import logging
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from workflow import Phase0Initialization

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """主测试函数"""
    logger.info("=" * 60)
    logger.info("Phase 0: 系统初始化测试")
    logger.info("=" * 60)
    
    # 检查 lib 目录是否存在
    lib_path = project_root / 'memories_ai_benchmark' / 'lib'
    
    if not lib_path.exists():
        logger.error(f"❌ lib 目录不存在: {lib_path}")
        logger.info("💡 请确保 memories_ai_benchmark/lib/ 目录存在并包含家人照片")
        return
    
    # 初始化 Phase 0
    try:
        phase0 = Phase0Initialization(face_model_name='buffalo_l')
        logger.info("✅ Phase 0 初始化成功")
    except Exception as e:
        logger.error(f"❌ Phase 0 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 执行初始化流程
    try:
        success = phase0.run(str(lib_path))
        
        if success:
            logger.info("\n" + "=" * 60)
            logger.info("✅ Phase 0 测试完成！")
            logger.info("=" * 60)
            logger.info("\n💡 现在可以运行 Phase 1 开始处理视频了")
        else:
            logger.error("\n❌ Phase 0 测试失败")
            
    except Exception as e:
        logger.error(f"❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()

