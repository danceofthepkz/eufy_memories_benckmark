"""
角色分类器：根据 LLM 描述的行为推断人物角色
"""

import re
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class RoleClassifier:
    """基于行为的角色分类器"""
    
    # 角色定义（与数据库 schema 对应）
    # 注意：数据库中的 role 字段支持 'owner', 'visitor', 'unknown'
    # 但我们可以使用更细分的角色进行推断，然后在 Phase 4 映射到数据库值
    ROLES = {
        'owner': '家人',
        'visitor': '访客',
        'delivery': '快递员/配送员',
        'service': '服务人员（维修、清洁等）',
        'unknown': '陌生人',
        'stranger': '陌生人'  # 与 unknown 同义
    }
    
    # 行为关键词映射到角色
    BEHAVIOR_PATTERNS = {
        'delivery': [
            r'快递', r'包裹', r'配送', r'送货', r'送餐', r'外卖',
            r'快递员', r'配送员', r'送货员', r'送餐员',
            r'拿着.*包裹', r'拿着.*快递', r'拿着.*盒子', r'拿着.*箱子',
            r'投递', r'签收', r'快递单', r'配送单',
            r'送.*包裹', r'送.*快递'  # 增强匹配
        ],
        'service': [
            r'维修', r'清洁', r'保洁', r'安装', r'检修',
            r'维修工', r'清洁工', r'安装工', r'检修工',
            r'工具箱', r'维修工具', r'清洁工具'
        ],
        'visitor': [
            r'访客', r'拜访', r'来访', r'客人', r'朋友',
            r'敲门', r'按门铃', r'等待', r'进入'
        ],
        'owner': [
            r'家人', r'主人', r'住户', r'居民'
        ]
    }
    
    def __init__(self):
        """初始化角色分类器"""
        # 编译正则表达式
        self.compiled_patterns = {}
        for role, patterns in self.BEHAVIOR_PATTERNS.items():
            self.compiled_patterns[role] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]
    
    def classify_from_description(self, description: str, 
                                  current_role: str = 'unknown') -> str:
        """
        从描述中推断角色
        
        Args:
            description: LLM 生成的描述文本
            current_role: 当前角色（默认 'unknown'）
        
        Returns:
            推断的角色：'owner', 'visitor', 'delivery', 'service', 'unknown'
        """
        if not description:
            return current_role
        
        # 统计每个角色的匹配次数
        role_scores = {}
        
        for role, patterns in self.compiled_patterns.items():
            score = 0
            for pattern in patterns:
                matches = pattern.findall(description)
                score += len(matches)
            
            if score > 0:
                role_scores[role] = score
        
        # 如果找到匹配，选择得分最高的角色
        if role_scores:
            best_role = max(role_scores.items(), key=lambda x: x[1])[0]
            logger.info(f"   根据行为推断角色: {current_role} → {best_role} (得分: {role_scores[best_role]})")
            return best_role
        
        # 如果没有匹配，保持原角色
        return current_role
    
    def extract_person_behaviors(self, description: str, 
                                people_info: Dict[int, Dict]) -> Dict[int, Dict[str, Any]]:
        """
        从描述中提取每个人物的行为信息
        
        Args:
            description: LLM 生成的描述文本
            people_info: 人物信息字典
        
        Returns:
            每个人物的行为信息：
            {
                person_id: {
                    'behavior': str,  # 行为描述
                    'inferred_role': str,  # 推断的角色
                    'original_role': str  # 原始角色
                }
            }
        """
        behaviors = {}
        
        # 尝试从描述中提取每个人物的行为
        # 这里使用简单的关键词匹配，未来可以改进为更复杂的 NLP 方法
        
        for person_id, info in people_info.items():
            original_role = info.get('role', 'unknown')
            
            # 如果描述中提到该人物，尝试提取行为
            # 简化处理：如果描述中包含该人物的信息，使用整个描述作为行为
            if person_id != -1:  # 排除陌生人标记
                # 检查描述中是否提到该人物
                person_mention_patterns = [
                    rf'Person_{person_id}',
                    rf'人物{person_id}',
                    rf'ID:{person_id}',
                    rf'家人\(Person_{person_id}\)',
                ]
                
                mentioned = False
                for pattern in person_mention_patterns:
                    if re.search(pattern, description, re.IGNORECASE):
                        mentioned = True
                        break
                
                if mentioned:
                    # 推断角色
                    inferred_role = self.classify_from_description(description, original_role)
                    
                    behaviors[person_id] = {
                        'behavior': description,  # 简化：使用整个描述
                        'inferred_role': inferred_role,
                        'original_role': original_role
                    }
        
        # 处理陌生人（person_id = -1 或 None）
        # 如果 people_info 中有 -1，说明有陌生人
        if -1 in people_info:
            # 检查描述中是否提到陌生人或相关行为
            stranger_patterns = [
                r'陌生人', r'陌生', r'未知', r'不明身份', r'人员', r'人物'
            ]
            
            mentioned = False
            for pattern in stranger_patterns:
                if re.search(pattern, description, re.IGNORECASE):
                    mentioned = True
                    break
            
            # 如果描述中提到陌生人，或者描述中包含行为关键词，都进行推断
            if mentioned or any(
                re.search(pattern, description, re.IGNORECASE)
                for role_patterns in self.BEHAVIOR_PATTERNS.values()
                for pattern in role_patterns
            ):
                inferred_role = self.classify_from_description(description, 'unknown')
                
                behaviors[-1] = {
                    'behavior': description,
                    'inferred_role': inferred_role,
                    'original_role': 'unknown'
                }
        
        return behaviors
    
    def _has_strong_delivery_keywords(self, description: str) -> bool:
        """
        检查描述中是否包含明确的快递/服务关键词
        
        Args:
            description: LLM 生成的描述文本
        
        Returns:
            如果包含明确的快递/服务关键词，返回 True
        """
        # 强关键词：明确指向快递/服务的行为
        strong_patterns = [
            r'拿着.*包裹', r'拿着.*快递', r'拿着.*盒子', r'拿着.*箱子',
            r'送.*包裹', r'送.*快递', r'送.*外卖',
            r'快递员', r'配送员', r'送货员',
            r'投递', r'签收', r'快递单', r'配送单',
            r'维修', r'清洁', r'工具箱'
        ]
        
        for pattern in strong_patterns:
            if re.search(pattern, description, re.IGNORECASE):
                return True
        
        return False
    
    def update_people_roles(self, global_event: Dict[str, Any], 
                           behaviors: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
        """
        更新 Global_Event 中的人物角色
        
        特殊处理：即使被判定为家人，如果行为明确指向快递/服务，也会更新角色
        
        Args:
            global_event: Global_Event 对象
            behaviors: 人物行为信息字典
        
        Returns:
            更新后的 Global_Event 对象
        """
        people_info = global_event.get('people_info', {})
        summary_text = global_event.get('summary_text', '')
        
        for person_id, behavior_info in behaviors.items():
            original_role = behavior_info.get('original_role', 'unknown')
            inferred_role = behavior_info.get('inferred_role', original_role)
            behavior_desc = behavior_info.get('behavior', summary_text)
            
            # 处理陌生人（person_id = -1）
            if person_id == -1:
                # 更新陌生人标记的角色
                if -1 in people_info:
                    people_info[-1]['role'] = inferred_role
                    people_info[-1]['role_source'] = 'behavior_inference'
                    people_info[-1]['behavior'] = behavior_desc
                    logger.info(f"   更新陌生人角色: {original_role} → {inferred_role}")
            elif person_id in people_info:
                # 如果推断的角色与原角色不同，更新
                if inferred_role != original_role:
                    # 特殊处理：如果原角色是 family，但行为明确指向快递/服务，允许覆盖
                    if original_role == 'family' and inferred_role in ['delivery', 'service']:
                        if self._has_strong_delivery_keywords(behavior_desc):
                            people_info[person_id]['role'] = inferred_role
                            people_info[person_id]['role_source'] = 'behavior_override'  # 标记为行为覆盖
                            people_info[person_id]['behavior'] = behavior_desc
                            logger.info(f"   ⚠️  覆盖家人角色: Person {person_id}: {original_role} → {inferred_role} (行为明确)")
                        else:
                            # 行为不够明确，不覆盖
                            logger.debug(f"   跳过角色更新: Person {person_id} (行为不够明确)")
                    else:
                        # 正常更新（非 family → delivery/service 的情况）
                        people_info[person_id]['role'] = inferred_role
                        people_info[person_id]['role_source'] = 'behavior_inference'
                        people_info[person_id]['behavior'] = behavior_desc
                        logger.info(f"   更新角色: Person {person_id}: {original_role} → {inferred_role}")
        
        global_event['people_info'] = people_info
        return global_event

