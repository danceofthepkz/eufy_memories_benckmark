"""
模块 4: RAG 合成引擎 (RAG Synthesis Engine)
职责：结合用户问题和检索到的证据，生成最终回答
"""

import logging
from typing import Dict, Any, List, Optional

from ..phase3_agent_interaction import LLMGateway

logger = logging.getLogger(__name__)


class RAGSynthesisEngine:
    """RAG 合成引擎"""
    
    def __init__(self, 
                 model_name: str = 'gemini-2.5-flash-lite',
                 temperature: float = 0.3,
                 max_output_tokens: int = 512):
        """
        初始化 RAG 合成引擎
        
        Args:
            model_name: Gemini 模型名称
            temperature: 温度参数
            max_output_tokens: 最大输出 token 数
        """
        self.llm_gateway = LLMGateway(
            model_name=model_name,
            temperature=temperature,
            max_output_tokens=max_output_tokens
        )
        
        logger.info(f"✅ RAGSynthesisEngine 初始化完成: {model_name}")
    
    def synthesize(self, user_query: str, 
                   retrieved_evidence: List[Dict[str, Any]],
                   query_obj: Dict[str, Any]) -> Dict[str, Any]:
        """
        合成最终回答
        
        Args:
            user_query: 用户原始问题
            retrieved_evidence: 检索到的证据列表
            query_obj: 查询对象（来自 QueryParser）
        
        Returns:
            回答字典: {
                'answer': str,  # 最终回答文本
                'evidence_count': int,  # 使用的证据数量
                'has_images': bool,  # 是否包含图片
                'images': List[str]  # 图片 URL 列表
            }
        """
        if not retrieved_evidence:
            return self._generate_no_result_answer(user_query)
        
        # 构建 Prompt
        system_prompt = self._build_system_prompt(query_obj)
        user_prompt = self._build_user_prompt(user_query, retrieved_evidence, query_obj)
        
        # 调用 LLM
        logger.info(f"🤖 调用 LLM 生成回答...")
        try:
            answer_text = self.llm_gateway.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt
            )
            
            # 提取图片信息
            images = []
            for evidence in retrieved_evidence:
                if evidence.get('type') == 'detail':
                    for appearance in evidence.get('appearances', []):
                        if appearance.get('snapshot_url'):
                            images.append(appearance['snapshot_url'])
            
            result = {
                'answer': answer_text.strip(),
                'evidence_count': len(retrieved_evidence),
                'has_images': len(images) > 0,
                'images': images
            }
            
            logger.info(f"✅ RAG 合成完成: {len(answer_text)} 字符, {len(images)} 张图片")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ LLM 调用失败: {e}")
            return self._generate_fallback_answer(user_query, retrieved_evidence)
    
    def _build_system_prompt(self, query_obj: Dict[str, Any]) -> str:
        """
        构建 System Prompt
        
        Args:
            query_obj: 查询对象
        
        Returns:
            System Prompt 字符串
        """
        intent = query_obj.get('intent', 'general')
        
        base_prompt = """你是一个智能家庭安防系统的问答助手。你的任务是根据检索到的数据库记录，回答用户的问题。

要求：
1. 必须使用中文回答
2. 基于检索到的证据，不要编造信息
3. 如果检索到的信息不足，明确说明
4. 回答要简洁、准确、人性化
5. 如果涉及时间，使用具体的时间格式（如"2025年9月1日 18:00"）
"""
        
        # 根据意图添加特定要求
        if intent == 'describe_appearance':
            base_prompt += "\n6. 如果用户询问衣着，基于检索到的 body_embedding 特征描述（如果可用），或说明无法从当前数据中确定具体衣着。"
        elif intent == 'query_time':
            base_prompt += "\n6. 如果用户询问时间，提供具体的时间信息。"
        elif intent == 'query_location':
            base_prompt += "\n6. 如果用户询问位置，提供具体的摄像头位置信息。"
        
        return base_prompt
    
    def _build_user_prompt(self, user_query: str,
                          retrieved_evidence: List[Dict[str, Any]],
                          query_obj: Dict[str, Any]) -> str:
        """
        构建 User Prompt
        
        Args:
            user_query: 用户查询
            retrieved_evidence: 检索到的证据
            query_obj: 查询对象
        
        Returns:
            User Prompt 字符串
        """
        prompt_parts = []
        
        prompt_parts.append(f"用户问题：{user_query}\n")
        prompt_parts.append("检索到的证据：\n")
        
        # 格式化证据
        for idx, evidence in enumerate(retrieved_evidence[:5], 1):  # 最多使用前5条证据
            if evidence.get('type') == 'summary':
                prompt_parts.append(f"\n[{idx}] 每日总结:")
                prompt_parts.append(f"   日期: {evidence.get('summary_date')}")
                prompt_parts.append(f"   内容: {evidence.get('summary_text')}")
            elif evidence.get('type') == 'detail':
                prompt_parts.append(f"\n[{idx}] 事件记录:")
                prompt_parts.append(f"   时间: {evidence.get('start_time')}")
                prompt_parts.append(f"   位置: {evidence.get('camera_location')}")
                prompt_parts.append(f"   描述: {evidence.get('llm_description')}")
                
                # 添加人物信息
                appearances = evidence.get('appearances', [])
                if appearances:
                    prompt_parts.append(f"   涉及人物:")
                    for app in appearances:
                        person_name = app.get('person_name', f"Person_{app.get('person_id')}")
                        match_method = app.get('match_method', 'unknown')
                        prompt_parts.append(f"     - {person_name} (识别方式: {match_method})")
        
        prompt_parts.append("\n请根据以上证据，回答用户的问题。")
        
        return "\n".join(prompt_parts)
    
    def _generate_no_result_answer(self, user_query: str) -> Dict[str, Any]:
        """
        生成无结果回答
        
        Args:
            user_query: 用户查询
        
        Returns:
            回答字典
        """
        answer = f"抱歉，我没有找到与您的问题相关的记录。请尝试调整查询条件，比如：\n- 检查日期是否正确\n- 确认人物名称\n- 使用不同的关键词"
        
        return {
            'answer': answer,
            'evidence_count': 0,
            'has_images': False,
            'images': []
        }
    
    def _generate_fallback_answer(self, user_query: str,
                                 retrieved_evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        生成兜底回答（当 LLM 调用失败时）
        
        Args:
            user_query: 用户查询
            retrieved_evidence: 检索到的证据
        
        Returns:
            回答字典
        """
        if not retrieved_evidence:
            return self._generate_no_result_answer(user_query)
        
        # 简单格式化证据
        evidence_summary = []
        for evidence in retrieved_evidence[:3]:
            if evidence.get('type') == 'detail':
                time_str = evidence.get('start_time', '未知时间')
                desc = evidence.get('llm_description', '无描述')
                evidence_summary.append(f"- {time_str}: {desc[:50]}...")
        
        answer = f"根据检索到的 {len(retrieved_evidence)} 条记录，相关信息如下：\n" + "\n".join(evidence_summary)
        
        return {
            'answer': answer,
            'evidence_count': len(retrieved_evidence),
            'has_images': False,
            'images': []
        }

