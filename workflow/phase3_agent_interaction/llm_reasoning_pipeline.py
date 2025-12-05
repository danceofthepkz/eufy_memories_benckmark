"""
第三阶段主 Pipeline: LLM_Reasoning_Pipeline
整合所有4个模块，实现完整的 LLM 语义生成流程
"""

import logging
from typing import List, Dict, Any, Optional

from .prompt_engine import PromptEngine
from .llm_gateway import LLMGateway
from .response_validator import ResponseValidator
from .role_classifier import RoleClassifier

logger = logging.getLogger(__name__)


class LLM_Reasoning_Pipeline:
    """第三阶段：宏观语义生成 Pipeline"""
    
    def __init__(self,
                 model_name: str = 'gemini-2.5-flash-lite',
                 temperature: float = 0.2,
                 max_output_tokens: int = 256,
                 project_id: Optional[str] = None,
                 location: str = 'us-central1'):
        """
        初始化 LLM Reasoning Pipeline
        
        Args:
            model_name: Gemini 模型名称
            temperature: 温度参数（0.0-1.0），越低越客观
            max_output_tokens: 最大输出 token 数
            project_id: Google Cloud 项目ID（如果为None，从环境变量读取）
            location: Vertex AI 区域
        """
        logger.info("=" * 60)
        logger.info("初始化 LLM Reasoning Pipeline (第三阶段)")
        logger.info("=" * 60)
        
        # 初始化各个模块
        self.prompt_engine = PromptEngine()                    # 模块 2
        self.llm_gateway = LLMGateway(                        # 模块 3
            model_name=model_name,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            project_id=project_id,
            location=location
        )
        self.validator = ResponseValidator()                   # 模块 4
        self.role_classifier = RoleClassifier()                # 角色分类器
        
        logger.info(f"✅ LLM Reasoning Pipeline 初始化完成 "
                   f"(模型: {model_name}, 温度: {temperature})")
    
    def process_events(self, global_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        处理全局事件列表，为每个事件生成自然语言日志
        
        Args:
            global_events: Global_Event 列表（来自 Phase 2）
        
        Returns:
            处理后的 Global_Event 列表，每个事件包含 'summary_text' 字段
        """
        logger.info("=" * 60)
        logger.info("开始 LLM 语义生成流程")
        logger.info("=" * 60)
        
        if not global_events:
            logger.warning("⚠️  输入事件列表为空")
            return []
        
        logger.info(f"📋 需要处理 {len(global_events)} 个事件")
        
        processed_events = []
        
        for idx, event in enumerate(global_events, 1):
            logger.info(f"\n[{idx}/{len(global_events)}] 处理事件...")
            
            # 检查是否有人物出现
            people = event.get('people', [])
            people_info = event.get('people_info', {})
            
            # 检查是否有陌生人（即使没有 person_id）
            has_strangers = False
            if -1 in people_info:
                has_strangers = people_info[-1].get('has_strangers', False)
            
            if (not people or len(people) == 0) and not has_strangers:
                # 如果没有人出现（包括陌生人），直接返回固定回复，跳过LLM调用
                logger.info("   检测到无人出现，跳过LLM调用")
                event['summary_text'] = "该视频中无人出现"
                event['llm_valid'] = True
                event['llm_warnings'] = []
                
                logger.info(f"✅ 事件 #{idx} 处理完成")
                logger.info(f"   生成日志: {event['summary_text']}")
                
                processed_events.append(event)
                continue
            
            # 如果有陌生人但没有 person_id，记录日志
            if has_strangers:
                stranger_count = people_info[-1].get('stranger_count', 0)
                logger.info(f"   检测到 {stranger_count} 个陌生人（无 person_id），继续处理")
            
            try:
                # 1. 构建 Prompt（模块 2）
                logger.debug("[模块 2] 构建 Prompt...")
                prompts = self.prompt_engine.build_full_prompt(event)
                
                # 2. 调用 LLM（模块 3）
                logger.debug("[模块 3] 调用 LLM API...")
                raw_response = self.llm_gateway.generate(
                    system_prompt=prompts['system_prompt'],
                    user_prompt=prompts['user_prompt']
                )
                
                # 记录原始响应（用于调试）
                logger.debug(f"LLM 原始响应: {raw_response[:200]}...")
                
                # 3. 验证和清洗（模块 4）
                logger.debug("[模块 4] 验证和清洗响应...")
                validation_result = self.validator.validate_and_clean(raw_response, event)
                
                # 4. 根据行为推断角色（新增）
                logger.debug("[角色分类] 根据行为推断角色...")
                summary_text = validation_result['summary_text']
                people_info = event.get('people_info', {})
                
                # 提取人物行为并推断角色
                behaviors = self.role_classifier.extract_person_behaviors(
                    summary_text, people_info
                )
                
                # 更新人物角色
                if behaviors:
                    event = self.role_classifier.update_people_roles(event, behaviors)
                    logger.info(f"   已根据行为更新 {len(behaviors)} 个人物的角色")
                
                # 5. 添加结果到事件
                event['summary_text'] = summary_text
                event['llm_valid'] = validation_result['is_valid']
                event['llm_warnings'] = validation_result['warnings']
                
                logger.info(f"✅ 事件 #{idx} 处理完成")
                logger.info(f"   生成日志: {validation_result['summary_text']}")
                
                if validation_result['warnings']:
                    logger.warning(f"   ⚠️  警告: {validation_result['warnings']}")
                
                processed_events.append(event)
                
            except Exception as e:
                logger.error(f"❌ 事件 #{idx} 处理失败: {e}")
                import traceback
                traceback.print_exc()
                
                # 使用兜底生成
                logger.warning(f"   使用兜底生成...")
                fallback_result = self.validator._generate_fallback(event)
                event['summary_text'] = fallback_result['summary_text']
                event['llm_valid'] = False
                event['llm_warnings'] = ['处理失败，使用兜底生成']
                
                processed_events.append(event)
        
        logger.info("\n" + "=" * 60)
        logger.info(f"✅ LLM 语义生成完成: {len(processed_events)} 个事件")
        logger.info("=" * 60)
        
        # 统计信息
        valid_count = sum(1 for e in processed_events if e.get('llm_valid', False))
        logger.info(f"\n📊 统计信息:")
        logger.info(f"   总事件数: {len(processed_events)}")
        logger.info(f"   有效生成: {valid_count}")
        logger.info(f"   兜底生成: {len(processed_events) - valid_count}")
        
        return processed_events
    
    def process_one_event(self, global_event: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理单个事件（便捷方法）
        
        Args:
            global_event: Global_Event 对象
        
        Returns:
            处理后的 Global_Event 对象（包含 'summary_text' 字段）
        """
        results = self.process_events([global_event])
        return results[0] if results else global_event

