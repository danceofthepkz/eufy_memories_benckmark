"""
模块 4: 响应清洗与校验器 (Response Parser & Validator)
职责：确保 LLM 生成的内容符合数据库入库要求
"""

import re
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ResponseValidator:
    """响应清洗与校验器"""
    
    def __init__(self):
        """初始化校验器"""
        pass
    
    def validate_and_clean(self, raw_response: str, 
                          global_event: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证和清洗 LLM 响应
        
        Args:
            raw_response: LLM 原始响应文本
            global_event: Global_Event 对象（用于验证）
        
        Returns:
            {
                'summary_text': str,  # 清洗后的文本
                'is_valid': bool,     # 是否有效
                'warnings': List[str] # 警告信息
            }
        """
        if not raw_response or not raw_response.strip():
            logger.warning("⚠️  LLM 响应为空，使用兜底生成")
            return self._generate_fallback(global_event)
        
        # 1. 格式清洗
        cleaned_text = self._clean_format(raw_response)
        
        # 2. 幻觉检测
        warnings = []
        is_valid = True
        
        hallucination_check = self._check_hallucination(cleaned_text, global_event)
        if not hallucination_check['is_valid']:
            warnings.extend(hallucination_check['warnings'])
            is_valid = False
        
        # 3. 如果检测到严重问题，使用兜底生成
        if not is_valid and len(warnings) > 0:
            logger.warning(f"⚠️  检测到幻觉，使用兜底生成。警告: {warnings}")
            return self._generate_fallback(global_event)
        
        logger.debug(f"✅ 响应验证完成: {len(cleaned_text)} 字符, "
                    f"有效={is_valid}, 警告数={len(warnings)}")
        
        return {
            'summary_text': cleaned_text,
            'is_valid': is_valid,
            'warnings': warnings
        }
    
    def _clean_format(self, text: str) -> str:
        """
        清洗格式（去除 Markdown、多余换行等）
        
        Args:
            text: 原始文本
        
        Returns:
            清洗后的文本
        """
        # 去除 Markdown 符号
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # **bold**
        text = re.sub(r'\*([^*]+)\*', r'\1', text)      # *italic*
        text = re.sub(r'`([^`]+)`', r'\1', text)        # `code`
        
        # 去除多余的换行符（保留单个换行）
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # 去除首尾空白
        text = text.strip()
        
        return text
    
    def _check_hallucination(self, text: str, 
                            global_event: Dict[str, Any]) -> Dict[str, Any]:
        """
        幻觉检测（基于时间线信息检查）
        
        检查规则：
        1. 如果时间线中没有"陌生人"，但输出里出现了"陌生人"或"入侵"等，标记为异常
        2. 如果时间线中没有"家人"，但输出里出现了"家人"等，标记为异常
        
        Args:
            text: 清洗后的文本
            global_event: Global_Event 对象
        
        Returns:
            {
                'is_valid': bool,
                'warnings': List[str]
            }
        """
        warnings = []
        
        # 从时间线文本中提取实际出现的人物类型
        prompt_text = global_event.get('prompt_text', '')
        timeline_has_family = '家人' in prompt_text
        timeline_has_stranger = '陌生人' in prompt_text
        
        # 检查1：如果时间线中没有家人，但输出提到家人
        if not timeline_has_family:
            family_keywords = ['家人', '爸爸', '妈妈', '主人', '住户']
            for keyword in family_keywords:
                if keyword in text:
                    # 检查是否是负面表述
                    keyword_pos = text.find(keyword)
                    if keyword_pos > 0:
                        context_before = text[max(0, keyword_pos-5):keyword_pos]
                        negative_patterns = ['未', '没有', '无', '不']
                        if not any(neg in context_before for neg in negative_patterns):
                            warnings.append("时间线中没有家人，但输出提到了家人")
                            break
        
        # 检查2：如果时间线中没有陌生人，但输出提到陌生人或入侵
        if not timeline_has_stranger:
            stranger_keywords = ['陌生人', '入侵', '可疑', '未授权', '闯入', '非法']
            for keyword in stranger_keywords:
                if keyword in text:
                    # 检查是否是负面表述（如"未检测到陌生人"）
                    keyword_pos = text.find(keyword)
                    if keyword_pos > 0:
                        context_before = text[max(0, keyword_pos-5):keyword_pos]
                        negative_patterns = ['未', '没有', '无', '不']
                        if not any(neg in context_before for neg in negative_patterns):
                            warnings.append("时间线中没有陌生人，但输出提到了陌生人或入侵")
                            break
        
        is_valid = len(warnings) == 0
        
        return {
            'is_valid': is_valid,
            'warnings': warnings
        }
    
    def _generate_fallback(self, global_event: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成兜底日志（当 API 失败或检测到严重问题时）
        
        Args:
            global_event: Global_Event 对象
        
        Returns:
            兜底日志字典
        """
        start_time = global_event.get('start_time')
        cameras = global_event.get('cameras', [])
        people_count = len(global_event.get('people', set()))
        
        # 格式化时间
        if start_time:
            time_str = start_time.strftime('%H:%M')
        else:
            time_str = "未知时间"
        
        # 格式化摄像头
        if cameras:
            camera_str = '、'.join(cameras[:2])  # 最多显示2个
            if len(cameras) > 2:
                camera_str += f"等{len(cameras)}个位置"
        else:
            camera_str = "监控区域"
        
        # 生成兜底文本（更详细的描述）
        people_info = global_event.get('people_info', {})
        duration = global_event.get('duration', 0)
        
        # 摄像头位置映射
        CAM_MAP = {
            'doorbell': '门口',
            'outdoor_high': '庭院/车道',
            'outdoor_side': '侧院',
            'indoor_living': '客厅',
            'indoor_hall': '门厅',
            'indoor_kitchen': '厨房',
            'indoor_bedroom': '卧室',
        }
        
        if people_count > 0:
            # 尝试获取人物信息
            people_details = []
            for person_id, info in people_info.items():
                role = info.get('role', 'unknown')
                cameras_seen = info.get('cameras', [])
                
                if role == 'family':
                    if cameras_seen:
                        camera_name = CAM_MAP.get(cameras_seen[0], cameras_seen[0])
                        people_details.append(f"家人(Person_{person_id})在{camera_name}")
                    else:
                        people_details.append(f"家人(Person_{person_id})")
                elif role == 'stranger':
                    people_details.append("陌生人")
            
            if people_details:
                people_str = '，'.join(people_details)
                if duration > 0:
                    if duration < 60:
                        duration_str = f"{duration:.0f}秒"
                    else:
                        duration_str = f"{duration/60:.1f}分钟"
                    fallback_text = f"{time_str}，{people_str}出现，活动持续约{duration_str}。"
                else:
                    fallback_text = f"{time_str}，{people_str}出现。"
            else:
                fallback_text = f"{time_str}，在{camera_str}检测到{people_count}个人员活动。"
        else:
            fallback_text = f"{time_str}，在{camera_str}未检测到人员活动。"
        
        logger.info(f"📝 生成兜底日志: {fallback_text}")
        
        return {
            'summary_text': fallback_text,
            'is_valid': True,
            'warnings': ['使用了兜底生成']
        }

