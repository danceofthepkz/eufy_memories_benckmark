#!/usr/bin/env python3
"""
数据库初始化脚本
根据 sql方案.md 创建 PostgreSQL 数据库和表结构
"""

import os
import sys
import psycopg2
from psycopg2 import sql
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def get_db_config():
    """从环境变量获取数据库配置"""
    return {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': os.getenv('POSTGRES_PORT', '5432'),
        'database': os.getenv('POSTGRES_DB', 'neweufy'),
        'user': os.getenv('POSTGRES_USER', 'postgres'),
        'password': os.getenv('POSTGRES_PASSWORD', 'eufy123')
    }

def create_database_if_not_exists():
    """创建数据库（如果不存在）"""
    config = get_db_config()
    db_name = config.pop('database')
    
    # 连接到默认的 postgres 数据库
    try:
        conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            database='postgres',  # 连接到默认数据库
            user=config['user'],
            password=config['password']
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        # 检查数据库是否存在
        cur.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (db_name,)
        )
        
        if cur.fetchone():
            print(f"✅ 数据库 '{db_name}' 已存在")
        else:
            # 创建数据库
            cur.execute(
                sql.SQL("CREATE DATABASE {}").format(
                    sql.Identifier(db_name)
                )
            )
            print(f"✅ 数据库 '{db_name}' 创建成功")
        
        cur.close()
        conn.close()
        
    except psycopg2.Error as e:
        print(f"❌ 创建数据库时出错: {e}")
        sys.exit(1)

def init_database():
    """初始化数据库表结构"""
    config = get_db_config()
    
    # 创建数据库（如果不存在）
    create_database_if_not_exists()
    
    # 连接到目标数据库
    try:
        conn = psycopg2.connect(**config)
        conn.autocommit = False
        cur = conn.cursor()
        
        print("📄 读取 SQL 初始化脚本...")
        sql_file = Path(__file__).parent / 'init_database.sql'
        
        if not sql_file.exists():
            print(f"❌ SQL 文件不存在: {sql_file}")
            sys.exit(1)
        
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        print("🔧 执行 SQL 脚本...")
        cur.execute(sql_script)
        conn.commit()
        
        print("✅ 数据库表结构创建成功！")
        
        # 验证表是否创建成功
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        
        tables = cur.fetchall()
        print(f"\n📊 已创建的表 ({len(tables)} 个):")
        for table in tables:
            print(f"   - {table[0]}")
        
        # 检查 pgvector 扩展
        cur.execute("SELECT * FROM pg_extension WHERE extname = 'vector';")
        if cur.fetchone():
            print("\n✅ pgvector 扩展已启用")
        else:
            print("\n⚠️  pgvector 扩展未启用，请手动执行: CREATE EXTENSION vector;")
        
        cur.close()
        conn.close()
        
        print("\n🎉 数据库初始化完成！")
        
    except psycopg2.Error as e:
        print(f"❌ 初始化数据库时出错: {e}")
        if conn:
            conn.rollback()
        sys.exit(1)

if __name__ == "__main__":
    print("=" * 60)
    print("家庭智能安防系统 - 数据库初始化")
    print("=" * 60)
    print()
    
    init_database()

