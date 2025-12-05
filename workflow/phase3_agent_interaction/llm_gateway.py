"""
模块 3: LLM 客户端网关 (LLM Client Gateway)
职责：与 Google Gemini API 进行稳定的交互
"""

import os
import logging
from typing import Optional, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

import logging

logger = logging.getLogger(__name__)

# 尝试导入 Vertex AI
try:
    import vertexai
    from vertexai.generative_models import GenerativeModel
    VERTEX_AI_AVAILABLE = True
except ImportError:
    VERTEX_AI_AVAILABLE = False
    logger.warning("⚠️  vertexai 未安装，将无法使用 Gemini API")


class LLMGateway:
    """LLM 客户端网关"""
    
    def __init__(self, 
                 model_name: str = 'gemini-2.5-flash-lite',
                 temperature: float = 0.2,
                 max_output_tokens: int = 256,
                 project_id: Optional[str] = None,
                 location: str = 'us-central1'):
        """
        初始化 LLM 网关
        
        Args:
            model_name: Gemini 模型名称
            temperature: 温度参数（0.0-1.0），越低越客观
            max_output_tokens: 最大输出 token 数
            project_id: Google Cloud 项目ID（如果为None，从环境变量读取）
            location: Vertex AI 区域
        """
        self.model_name = model_name
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        
        # 获取项目ID
        if project_id is None:
            project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
            if not project_id:
                raise ValueError("无法确定项目ID，请设置 GOOGLE_CLOUD_PROJECT 环境变量")
        
        self.project_id = project_id
        self.location = location
        
        # 初始化 Vertex AI
        if VERTEX_AI_AVAILABLE:
            try:
                vertexai.init(project=project_id, location=location)
                self.model = GenerativeModel(model_name)
                logger.info(f"✅ LLM 网关初始化成功: {model_name} (项目: {project_id}, 区域: {location})")
            except Exception as e:
                logger.error(f"❌ Vertex AI 初始化失败: {e}")
                raise
        else:
            logger.error("❌ vertexai 未安装，无法初始化 LLM 网关")
            raise ImportError("请安装 google-cloud-aiplatform: pip install google-cloud-aiplatform")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,))
    )
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """
        调用 LLM 生成文本
        
        Args:
            system_prompt: System Prompt
            user_prompt: User Prompt
        
        Returns:
            生成的文本
        """
        if not VERTEX_AI_AVAILABLE:
            raise ImportError("vertexai 未安装")
        
        try:
            # 组合完整的 Prompt
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            
            logger.debug(f"📤 发送请求到 Gemini API (模型: {self.model_name})")
            logger.debug(f"   Prompt 长度: {len(full_prompt)} 字符")
            
            # 调用模型
            generation_config = {
                'temperature': self.temperature,
                'max_output_tokens': self.max_output_tokens,
            }
            
            response = self.model.generate_content(
                full_prompt,
                generation_config=generation_config
            )
            
            # 提取文本
            if hasattr(response, 'text') and response.text:
                generated_text = response.text.strip()
                logger.debug(f"📥 收到响应: {len(generated_text)} 字符")
                return generated_text
            else:
                logger.warning("⚠️  API 响应为空")
                return ""
                
        except Exception as e:
            logger.error(f"❌ LLM API 调用失败: {e}")
            raise
    
    def generate_simple(self, prompt: str) -> str:
        """
        简化版生成方法（只使用 User Prompt，无 System Prompt）
        
        Args:
            prompt: 完整的 Prompt 文本
        
        Returns:
            生成的文本
        """
        return self.generate("", prompt)

