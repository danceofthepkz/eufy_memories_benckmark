#!/usr/bin/env python3
"""
测试数据库连接脚本
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def test_connection():
    """测试数据库连接"""
    try:
        conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=os.getenv('POSTGRES_PORT', '5432'),
            database=os.getenv('POSTGRES_DB', 'neweufy'),
            user=os.getenv('POSTGRES_USER', 'postgres'),
            password=os.getenv('POSTGRES_PASSWORD', '')
        )
        
        cur = conn.cursor()
        
        # 测试基本连接
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        print(f"✅ 数据库连接成功！")
        print(f"   PostgreSQL 版本: {version.split(',')[0]}")
        
        # 检查 pgvector 扩展
        cur.execute("SELECT * FROM pg_extension WHERE extname = 'vector';")
        if cur.fetchone():
            print(f"✅ pgvector 扩展已启用")
        else:
            print(f"⚠️  pgvector 扩展未启用")
        
        # 检查表
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        tables = cur.fetchall()
        
        if tables:
            print(f"\n📊 数据库中的表 ({len(tables)} 个):")
            for table in tables:
                print(f"   - {table[0]}")
        else:
            print(f"\n⚠️  数据库中没有表，请运行: python database/init_database.py")
        
        cur.close()
        conn.close()
        
        return True
        
    except psycopg2.OperationalError as e:
        print(f"❌ 数据库连接失败: {e}")
        print("\n💡 请检查:")
        print("   1. PostgreSQL 服务是否运行")
        print("   2. 数据库配置是否正确（POSTGRES_HOST, POSTGRES_PORT, etc.）")
        print("   3. 用户名和密码是否正确")
        return False
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("数据库连接测试")
    print("=" * 60)
    print()
    
    success = test_connection()
    sys.exit(0 if success else 1)

