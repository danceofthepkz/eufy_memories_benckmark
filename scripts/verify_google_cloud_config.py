#!/usr/bin/env python3
"""
验证 Google Cloud Service Account 配置脚本
用于测试 Gemini API 是否配置正确
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def check_environment_variables():
    """检查必需的环境变量"""
    print("🔍 检查环境变量...")
    
    required_vars = {
        'GOOGLE_APPLICATION_CREDENTIALS': 'Service Account JSON 文件路径',
        'GOOGLE_CLOUD_PROJECT': 'Google Cloud 项目ID'
    }
    
    optional_vars = {
        'GOOGLE_CLOUD_LOCATION': 'Vertex AI 区域（默认: us-central1）'
    }
    
    all_ok = True
    
    # 检查必需变量
    for var, desc in required_vars.items():
        value = os.getenv(var)
        if value:
            print(f"  ✅ {var}: {value}")
            if var == 'GOOGLE_APPLICATION_CREDENTIALS':
                if not os.path.exists(value):
                    print(f"     ⚠️  警告: 文件不存在: {value}")
                    all_ok = False
        else:
            print(f"  ❌ {var}: 未设置 ({desc})")
            all_ok = False
    
    # 检查可选变量
    for var, desc in optional_vars.items():
        value = os.getenv(var)
        if value:
            print(f"  ✅ {var}: {value}")
        else:
            print(f"  ⚠️  {var}: 未设置 ({desc})")
    
    return all_ok

def test_vertex_ai_connection():
    """测试 Vertex AI 连接"""
    print("\n🔍 测试 Vertex AI 连接...")
    
    try:
        import vertexai
        from vertexai.generative_models import GenerativeModel
        
        project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
        location = os.getenv('GOOGLE_CLOUD_LOCATION', 'us-central1')
        
        if not project_id:
            print("  ❌ 无法测试: GOOGLE_CLOUD_PROJECT 未设置")
            return False
        
        print(f"  初始化 Vertex AI (项目: {project_id}, 区域: {location})...")
        vertexai.init(project=project_id, location=location)
        
        print("  创建模型实例 (gemini-2.5-flash-lite)...")
        model = GenerativeModel("gemini-2.5-flash-lite")
        
        print("  发送测试请求...")
        response = model.generate_content("Hello! 请回复'配置成功'")
        
        print(f"  ✅ 连接成功!")
        print(f"  模型回复: {response.text}")
        return True
        
    except FileNotFoundError as e:
        print(f"  ❌ Service Account 文件未找到: {e}")
        return False
    except PermissionDenied as e:
        print(f"  ❌ 权限不足: {e}")
        print("     请确保 Service Account 具有 'Vertex AI User' 角色")
        return False
    except Exception as e:
        print(f"  ❌ 连接失败: {type(e).__name__}: {e}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("Google Cloud Service Account 配置验证")
    print("=" * 60)
    print()
    
    # 尝试从 .env 文件加载环境变量
    try:
        from dotenv import load_dotenv
        env_path = project_root / '.env'
        if env_path.exists():
            print(f"📄 从 .env 文件加载环境变量: {env_path}")
            load_dotenv(env_path)
            print()
    except ImportError:
        print("⚠️  python-dotenv 未安装，跳过 .env 文件加载")
        print()
    except Exception as e:
        print(f"⚠️  加载 .env 文件时出错: {e}")
        print()
    
    # 检查环境变量
    env_ok = check_environment_variables()
    
    if not env_ok:
        print("\n❌ 环境变量配置不完整，请检查配置后重试")
        print("\n💡 提示:")
        print("   1. 运行: source setup_env.sh")
        print("   2. 或创建 .env 文件（参考 .env.example）")
        print("   3. 确保 gen-lang-sa.json 文件存在")
        return 1
    
    # 测试连接
    connection_ok = test_vertex_ai_connection()
    
    print("\n" + "=" * 60)
    if connection_ok:
        print("✅ 配置验证成功！Gemini 服务已就绪")
        return 0
    else:
        print("❌ 配置验证失败，请检查错误信息")
        return 1

if __name__ == "__main__":
    sys.exit(main())








