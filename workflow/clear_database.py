#!/usr/bin/env python3
"""
清空数据库脚本
用于测试前清理所有数据，但保留表结构
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv
import logging

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_db_config():
    """从环境变量获取数据库配置"""
    return {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': os.getenv('POSTGRES_PORT', '5432'),
        'database': os.getenv('POSTGRES_DB', 'neweufy'),
        'user': os.getenv('POSTGRES_USER', 'postgres'),
        'password': os.getenv('POSTGRES_PASSWORD', 'eufy123')
    }


def clear_database(confirm: bool = False):
    """
    清空数据库中的所有数据（但保留表结构）
    
    Args:
        confirm: 是否确认清空（默认False，需要手动确认）
    """
    db_config = get_db_config()
    
    # 需要清空的表（按依赖顺序，先清空子表，再清空父表）
    tables = [
        'event_appearances',  # 子表
        'person_faces',       # 子表
        'daily_summaries',    # 独立表
        'event_logs',         # 主表
        'persons',            # 主表
    ]
    
    logger.info("=" * 60)
    logger.info("数据库清空脚本")
    logger.info("=" * 60)
    logger.info(f"数据库: {db_config['database']} @ {db_config['host']}:{db_config['port']}")
    logger.info(f"将清空以下表: {', '.join(tables)}")
    logger.info("")
    
    # 安全确认
    if not confirm:
        response = input("⚠️  确定要清空所有数据吗？(yes/no): ").strip().lower()
        if response != 'yes':
            logger.info("❌ 操作已取消")
            return False
    
    try:
        # 连接数据库
        conn = psycopg2.connect(**db_config)
        conn.autocommit = False  # 使用事务
        
        cur = conn.cursor()
        
        # 先统计每个表的记录数
        logger.info("📊 当前数据统计:")
        total_records = 0
        for table in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = cur.fetchone()[0]
                logger.info(f"   {table}: {count} 条记录")
                total_records += count
            except Exception as e:
                logger.warning(f"   {table}: 表不存在或无法查询 ({e})")
        
        logger.info(f"   总计: {total_records} 条记录")
        logger.info("")
        
        if total_records == 0:
            logger.info("✅ 数据库已经是空的，无需清空")
            cur.close()
            conn.close()
            return True
        
        # 开始清空
        logger.info("🗑️  开始清空数据...")
        
        for table in tables:
            try:
                # 使用 TRUNCATE 快速清空表（比 DELETE 快，且重置自增ID）
                # CASCADE 确保清空所有依赖的外键数据
                cur.execute(f"TRUNCATE TABLE {table} CASCADE")
                logger.info(f"   ✅ {table}: 已清空")
            except Exception as e:
                logger.warning(f"   ⚠️  {table}: 清空失败 ({e})")
        
        # 提交事务
        conn.commit()
        
        # 验证清空结果
        logger.info("")
        logger.info("📊 清空后数据统计:")
        all_empty = True
        for table in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = cur.fetchone()[0]
                if count > 0:
                    logger.warning(f"   ⚠️  {table}: 仍有 {count} 条记录")
                    all_empty = False
                else:
                    logger.info(f"   ✅ {table}: 0 条记录")
            except Exception as e:
                logger.warning(f"   ⚠️  {table}: 无法查询 ({e})")
        
        cur.close()
        conn.close()
        
        if all_empty:
            logger.info("")
            logger.info("✅ 数据库清空完成！")
            logger.info("   所有表结构已保留，可以重新开始测试")
            return True
        else:
            logger.warning("")
            logger.warning("⚠️  部分表可能未完全清空，请检查")
            return False
            
    except psycopg2.Error as e:
        logger.error(f"❌ 数据库操作失败: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False
    except Exception as e:
        logger.error(f"❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='清空数据库中的所有数据')
    parser.add_argument(
        '--yes', '-y',
        action='store_true',
        help='跳过确认，直接清空'
    )
    
    args = parser.parse_args()
    
    success = clear_database(confirm=args.yes)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

