"""
模块 2: 提示词工程引擎 (Prompt Template Engine)
职责：组装 System Prompt 和 User Prompt，控制 LLM 的"人设"和"输出格式"
"""

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class PromptEngine:
    """提示词工程引擎"""
    
    # 摄像头位置语义映射
    CAM_MAP = {
        'doorbell': '门口',
        'outdoor_high': '庭院/车道',
        'outdoor_side': '侧院',
        'indoor_living': '客厅',
        'indoor_hall': '门厅',
        'indoor_kitchen': '厨房',
        'indoor_bedroom': '卧室',
    }
    
    def __init__(self):
        """初始化提示词引擎"""
        pass
    
    def build_full_prompt(self, global_event: Dict[str, Any], 
                         prompt_context: Optional[str] = None) -> Dict[str, str]:
        """
        构建完整的 Prompt（System Prompt + User Prompt）
        
        Args:
            global_event: Global_Event 对象
            prompt_context: Prompt 上下文文本（如果提供，优先使用；否则从 global_event 中提取）
        
        Returns:
            {
                'system_prompt': str,
                'user_prompt': str
            }
        """
        # 获取 Prompt 上下文（优先使用提供的，否则从 global_event 中提取）
        if prompt_context is None:
            prompt_context = global_event.get('prompt_text', '')
        
        # 构建 System Prompt
        system_prompt = self._build_system_prompt(global_event)
        
        # 构建 User Prompt
        user_prompt = self._build_user_prompt(prompt_context, global_event)
        
        logger.debug(f"✅ Prompt 构建完成: System={len(system_prompt)}字符, "
                    f"User={len(user_prompt)}字符")
        
        return {
            'system_prompt': system_prompt,
            'user_prompt': user_prompt
        }
    
    def _build_system_prompt(self, global_event: Dict[str, Any]) -> str:
        """
        构建 System Prompt（定义 LLM 的角色和规则）
        
        Args:
            global_event: Global_Event 对象
        
        Returns:
            System Prompt 字符串
        """
        # 检测事件类型
        event_type = self._detect_event_type(global_event)
        
        # 基础 System Prompt
        base_prompt = """你是一个智能家庭监控系统的日志生成助手。你的任务是根据监控视频的时间线信息，生成一条详细、准确的中文日志。

规则：
1. 必须使用中文
2. 时间误差不能超过1分钟
3. 如果是陌生人，必须描述衣着特征（如果信息可用）
4. 保持客观、详细，避免主观判断
5. 关注空间转移（如从"庭院"到"正门"意味着"回家"），详细描述人物的移动路径
6. 如果多个摄像头同时检测到同一人，合并为一条日志，但要说明在不同位置的出现
7. 输出格式：时间 + 详细的事件描述（50-200字）
8. 必须包含以下信息：
   - 人物的具体行为（出现、移动、停留、做什么等）
   - 位置变化（从哪个位置到哪个位置）
   - 时间顺序（先做什么，后做什么）
   - 如果有多个摄像头，说明在不同位置的活动
   - 【重要】详细描述人物在做什么（例如：拿着包裹、按门铃、等待、离开等）
9. 禁止使用"详情见视频"、"详见视频"等通用描述，必须基于时间线信息生成具体描述
10. 【重要】严格基于提供的时间线信息生成日志，不要推断或添加时间线中未明确提到的人物或事件
11. 如果时间线中只提到"家人"，不要添加"陌生人"的描述；如果时间线中只提到"陌生人"，不要添加"家人"的描述
12. 【行为描述要求】必须详细描述人物的具体行为，例如：
    - 如果看到人物拿着包裹或快递，明确说明"拿着包裹"、"拿着快递"等
    - 如果看到人物按门铃或敲门，明确说明"按门铃"、"敲门"等
    - 如果看到人物在等待，明确说明"等待"、"停留"等
    - 如果看到人物离开，明确说明"离开"、"离去"等
"""
        
        # 根据事件类型添加特定规则
        if event_type == 'family_only':
            base_prompt += "\n注意：本次事件涉及家人，请使用友好的语气。"
        elif event_type == 'stranger':
            base_prompt += "\n注意：本次事件涉及陌生人，请详细描述并保持警惕性。"
        elif event_type == 'mixed':
            base_prompt += "\n注意：本次事件涉及家人和陌生人，请区分描述。"
        
        return base_prompt
    
    def _build_user_prompt(self, prompt_context: str, 
                          global_event: Dict[str, Any]) -> str:
        """
        构建 User Prompt（包含具体的事件信息）
        
        Args:
            prompt_context: Prompt 上下文文本（时间线）
            global_event: Global_Event 对象
        
        Returns:
            User Prompt 字符串
        """
        # 基础 User Prompt
        user_prompt = prompt_context
        
        # 添加额外上下文信息（如果有）
        additional_info = []
        
        # 添加人物信息（更详细）
        people_info = global_event.get('people_info', {})
        if people_info:
            people_list = []
            for person_id, info in people_info.items():
                role = info.get('role', 'unknown')
                method = info.get('method', 'unknown')
                cameras_seen = info.get('cameras', [])
                
                if role == 'family':
                    camera_names = [self.CAM_MAP.get(cam, cam) for cam in cameras_seen]
                    camera_str = '、'.join(camera_names) if camera_names else '未知位置'
                    people_list.append(f"家人(ID:{person_id})，在{camera_str}出现")
                elif role == 'stranger':
                    people_list.append(f"陌生人")
            
            if people_list:
                additional_info.append(f"涉及人物: {'；'.join(people_list)}")
        
        # 添加摄像头信息（语义映射）
        cameras = global_event.get('cameras', [])
        if cameras:
            camera_names = [self.CAM_MAP.get(cam, cam) for cam in cameras]
            if len(camera_names) > 1:
                additional_info.append(f"摄像头位置: {' → '.join(camera_names)}（按时间顺序）")
            else:
                additional_info.append(f"摄像头位置: {camera_names[0]}")
        
        # 添加时间跨度信息
        duration = global_event.get('duration', 0)
        if duration > 0:
            if duration < 60:
                additional_info.append(f"事件持续时间: {duration:.0f}秒")
            else:
                additional_info.append(f"事件持续时间: {duration/60:.1f}分钟")
        
        # 添加Clip数量信息（帮助理解事件的复杂程度）
        clip_count = global_event.get('clip_count', 0)
        if clip_count > 1:
            additional_info.append(f"该事件包含{clip_count}个视频片段，请综合描述所有片段中的活动")
        
        # 组合 User Prompt
        if additional_info:
            user_prompt += "\n\n补充信息：\n" + "\n".join(f"- {info}" for info in additional_info)
        
        # 添加生成要求
        user_prompt += "\n\n请根据以上时间线信息，生成一条详细的中文日志，描述事件的完整过程，包括人物的具体行为、位置变化和时间顺序。"
        user_prompt += "\n【重要提示】："
        user_prompt += "\n- 严格基于时间线信息生成，不要推断或添加时间线中未明确提到的人物"
        user_prompt += "\n- 如果时间线中只提到家人，不要添加陌生人的描述"
        user_prompt += "\n- 如果时间线中只提到陌生人，不要添加家人的描述"
        user_prompt += "\n- 不要使用\"详情见视频\"等通用描述，必须基于时间线生成具体描述"
        user_prompt += "\n- 【行为描述】必须详细描述人物在做什么，例如："
        user_prompt += "\n  * 如果看到人物拿着物品，明确说明拿着什么（包裹、快递、工具箱等）"
        user_prompt += "\n  * 如果看到人物在操作，明确说明在做什么（按门铃、敲门、等待、离开等）"
        user_prompt += "\n  * 如果看到人物有特定动作，明确说明动作内容"
        
        return user_prompt
    
    def _detect_event_type(self, global_event: Dict[str, Any]) -> str:
        """
        检测事件类型
        
        Args:
            global_event: Global_Event 对象
        
        Returns:
            事件类型：'family_only', 'stranger', 'mixed'
        """
        people_info = global_event.get('people_info', {})
        
        has_family = False
        has_stranger = False
        
        for person_id, info in people_info.items():
            role = info.get('role', 'unknown')
            if role == 'family':
                has_family = True
            elif role == 'stranger':
                has_stranger = True
        
        if has_family and has_stranger:
            return 'mixed'
        elif has_stranger:
            return 'stranger'
        else:
            return 'family_only'

