#!/usr/bin/env python3
"""
简单的 Gemini API 测试脚本
"""

import os
import vertexai
from vertexai.generative_models import GenerativeModel

# 设置环境变量（如果还没有设置）
if not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = './gen-lang-sa.json'
if not os.getenv('GOOGLE_CLOUD_PROJECT'):
    os.environ['GOOGLE_CLOUD_PROJECT'] = 'gen-lang-client-0057517563'

# 初始化 Vertex AI
project_id = os.getenv('GOOGLE_CLOUD_PROJECT', 'gen-lang-client-0057517563')
location = os.getenv('GOOGLE_CLOUD_LOCATION', 'us-central1')

print(f"初始化 Vertex AI (项目: {project_id}, 区域: {location})...")
vertexai.init(project=project_id, location=location)

# 创建模型实例
print("创建模型实例 (gemini-2.5-flash-lite)...")
model = GenerativeModel("gemini-2.5-flash-lite")

# 测试调用
print("\n发送测试请求...")
response = model.generate_content("请用中文简单介绍一下你自己")

print(f"\n✅ 模型回复:\n{response.text}\n")

