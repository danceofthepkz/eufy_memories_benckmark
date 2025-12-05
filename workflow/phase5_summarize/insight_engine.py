"""
模块 3: 高维洞察引擎 (High-Dimensional Insight Engine)
职责：使用 LLM 生成每日总结
"""

import logging
from typing import Optional
from datetime import datetime

from ..phase3_agent_interaction import LLMGateway

logger = logging.getLogger(__name__)


class InsightEngine:
    """高维洞察引擎"""
    
    def __init__(self, 
                 model_name: str = 'gemini-2.5-flash-lite',
                 temperature: float = 0.3,
                 max_output_tokens: int = 512):
        """
        初始化洞察引擎
        
        Args:
            model_name: Gemini 模型名称
            temperature: 温度参数（0.0-1.0），越低越客观
            max_output_tokens: 最大输出 token 数
        """
        self.llm_gateway = LLMGateway(
            model_name=model_name,
            temperature=temperature,
            max_output_tokens=max_output_tokens
        )
        
        logger.info(f"✅ InsightEngine 初始化完成: {model_name}")
    
    def analyze(self, timeline_text: str, target_date: str) -> str:
        """
        分析时间线并生成每日总结
        
        Args:
            timeline_text: 格式化的时间线文本
            target_date: 目标日期，格式为 'YYYY-MM-DD'
        
        Returns:
            生成的总结文本
        """
        if not timeline_text or not timeline_text.strip():
            logger.warning("⚠️  时间线文本为空，返回默认总结")
            return f"{target_date}，当日无事件记录。"
        
        # 构建 System Prompt
        system_prompt = self._build_system_prompt()
        
        # 构建 User Prompt
        user_prompt = self._build_user_prompt(timeline_text, target_date)
        
        # 调用 LLM
        logger.info(f"🤖 调用 LLM 生成 {target_date} 的每日总结...")
        try:
            summary = self.llm_gateway.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt
            )
            
            logger.info(f"✅ LLM 总结生成完成: {len(summary)} 字符")
            return summary.strip()
            
        except Exception as e:
            logger.error(f"❌ LLM 调用失败: {e}")
            # 返回兜底总结
            return self._generate_fallback(timeline_text, target_date)
    
    def _build_system_prompt(self) -> str:
        """
        构建 System Prompt
        
        Returns:
            System Prompt 字符串
        """
        return """你是一个专业的家庭安防分析师。你的任务是根据提供的事件日志，生成每日活动总结。

要求：
1. **规律分析**：识别家人的出门和回家时间
2. **安全提醒**：明确提及任何与陌生人（未知人员）的互动
3. **异常标记**：突出敏感时段的活动（如 00:00 - 05:00）
4. **简洁性**：不要列举每个事件，而是将相似事件归类（如"多次进出车辆" → "装车活动"）
5. **客观性**：基于提供的时间线信息，不要推断或添加未明确提到的事件

输出格式（中文）：
- [家人动态]: ...
- [访客/陌生人]: ... (如果没有，说"无")
- [异常关注]: ... (如果没有，说"无")
"""
    
    def _build_user_prompt(self, timeline_text: str, target_date: str) -> str:
        """
        构建 User Prompt
        
        Args:
            timeline_text: 时间线文本
            target_date: 目标日期
        
        Returns:
            User Prompt 字符串
        """
        # 解析日期，获取中文格式
        try:
            date_obj = datetime.strptime(target_date, '%Y-%m-%d')
            date_str_cn = date_obj.strftime('%Y年%m月%d日')
        except:
            date_str_cn = target_date
        
        prompt = f"""以下是 {date_str_cn} ({target_date}) 的完整事件时间线：

{timeline_text}

请根据以上时间线信息，生成一条详细的每日活动总结。要求：
1. 提取家人的日常规律（出门时间、回家时间等）
2. 明确标记任何陌生人或访客的出现
3. 关注异常时段的活动
4. 使用简洁的语言，不要重复列举每个事件
5. 严格按照输出格式生成总结

输出格式（中文）：
- [家人动态]: ...
- [访客/陌生人]: ... (如果没有，说"无")
- [异常关注]: ... (如果没有，说"无")
"""
        
        return prompt
    
    def _generate_fallback(self, timeline_text: str, target_date: str) -> str:
        """
        生成兜底总结（当 LLM 调用失败时）
        
        Args:
            timeline_text: 时间线文本
            target_date: 目标日期
        
        Returns:
            兜底总结文本
        """
        event_count = timeline_text.count('\n') + 1 if timeline_text else 0
        
        try:
            date_obj = datetime.strptime(target_date, '%Y-%m-%d')
            date_str_cn = date_obj.strftime('%Y年%m月%d日')
        except:
            date_str_cn = target_date
        
        fallback = f"""{date_str_cn}，共记录 {event_count} 个事件。由于系统限制，无法生成详细总结，详情请查看事件日志。"""
        
        logger.warning(f"⚠️  使用兜底总结: {fallback}")
        return fallback

