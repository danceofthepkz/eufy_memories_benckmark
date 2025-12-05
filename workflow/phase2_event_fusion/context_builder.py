"""
模块 5: 多视角上下文构建器 (Multi-View Context Builder)
职责：将聚合后的数据转化为 LLM 能看懂的自然语言 Prompt 片段
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ContextBuilder:
    """多视角上下文构建器"""
    
    def __init__(self):
        """初始化上下文构建器"""
        pass
    
    def build(self, global_event: Dict[str, Any]) -> str:
        """
        构建 LLM Prompt 上下文
        
        Args:
            global_event: Global_Event 对象
        
        Returns:
            Prompt 文本字符串
        """
        if not global_event:
            return ""
        
        logger.debug(f"构建 Prompt 上下文: {len(global_event.get('clips', []))} 个 Clip")
        
        # 1. 构建时间线
        timeline_lines = []
        
        for clip in global_event.get('clips', []):
            clip_time = clip['time']
            camera = clip['cam']
            
            # 提取该 Clip 中的人物信息
            people_summary = self._summarize_clip_people(clip)
            
            if people_summary:
                timeline_lines.append(
                    f"- {clip_time.strftime('%H:%M:%S')} [{camera}]: {people_summary}"
                )
        
        # 2. 构建 Prompt
        prompt_parts = []
        
        # 时间线部分
        if timeline_lines:
            prompt_parts.append("Plaintext时间线：")
            prompt_parts.extend(timeline_lines)
        
        # 空间逻辑提示（可选）
        spatial_hint = self._detect_spatial_movement(global_event)
        if spatial_hint:
            prompt_parts.append(f"提示: {spatial_hint}")
        
        # 事件类型提示（温和提示，不强制）
        event_type = self._detect_event_type(global_event)
        if event_type and event_type != 'normal':
            # 只作为参考信息，不强制要求
            event_hint = self._get_event_type_hint(event_type)
            if event_hint:
                prompt_parts.append(f"提示: {event_hint}")
        
        # 任务说明（更详细的要求）
        prompt_parts.append("任务：根据以上时间线信息，生成一条详细的中文日志，描述这个事件的完整过程。")
        prompt_parts.append("要求：")
        prompt_parts.append("- 描述人物的具体行为（出现、移动、停留等）")
        prompt_parts.append("- 说明位置变化（如果涉及多个摄像头）")
        prompt_parts.append("- 体现时间顺序（先做什么，后做什么）")
        prompt_parts.append("- 不要使用\"详情见视频\"等通用描述，必须基于时间线生成具体描述")
        prompt_parts.append("- 根据观察到的人物动作、特征和活动模式，自然地判断和描述事件类型（如：快递配送、服务维修、访客等）")
        
        prompt_text = "\n".join(prompt_parts)
        
        logger.debug(f"✅ Prompt 构建完成: {len(prompt_text)} 字符")
        
        return prompt_text
    
    def _summarize_clip_people(self, clip: Dict[str, Any]) -> str:
        """
        总结 Clip 中的人物信息（更详细的描述，包含活动信息）
        
        Args:
            clip: Clip_Obj
        
        Returns:
            人物描述字符串，如 "家人(Person_21)在门口出现，持续停留约15秒，检测到移动迹象" 或 "陌生人出现并活动"
        """
        people_summary = []
        
        # 统计该 Clip 中的人物（去重）
        seen_people = {}
        # key: (person_id, role) -> {
        #   'detection_count': int,
        #   'first_frame': int,
        #   'last_frame': int,
        #   'bboxes': List[Tuple],  # 用于分析移动
        #   'frame_indices': List[int]
        # }
        
        for frame_idx, frame_people in enumerate(clip.get('people_detected', [])):
            for person in frame_people:
                person_id = person.get('person_id')
                role = person.get('role', 'stranger')
                bbox = person.get('bbox')
                
                # 避免重复
                key = (person_id, role)
                if key not in seen_people:
                    seen_people[key] = {
                        'detection_count': 0,
                        'first_frame': frame_idx,
                        'last_frame': frame_idx,
                        'bboxes': [],
                        'frame_indices': []
                    }
                
                info = seen_people[key]
                info['detection_count'] += 1
                info['last_frame'] = max(info['last_frame'], frame_idx)
                info['first_frame'] = min(info['first_frame'], frame_idx)
                if bbox:
                    info['bboxes'].append(bbox)
                info['frame_indices'].append(frame_idx)
        
        if not seen_people:
            return ""
        
        # 构建详细描述
        for key, info in seen_people.items():
            person_id, role = key
            detection_count = info['detection_count']
            first_frame = info['first_frame']
            last_frame = info['last_frame']
            frame_span = last_frame - first_frame + 1
            bboxes = info['bboxes']
            
            # 分析移动（基于 bbox 中心点的变化）
            has_movement = self._detect_movement(bboxes)
            
            # 分析活动强度
            activity_level = self._analyze_activity_level(detection_count, frame_span, has_movement)
            
            # 分析位置（基于摄像头和 bbox）
            position_hint = self._analyze_position(clip.get('cam', ''), bboxes)
            
            # 构建描述
            if role == 'family':
                person_name = self._get_person_name(person_id)
                desc = f"家人({person_name})"
            elif role == 'suspected_family':
                person_name = self._get_person_name(person_id) if person_id else "未知"
                desc = f"家人({person_name})"
            elif role == 'stranger':
                desc = "陌生人"
            else:
                desc = "未知人物"
            
            # 添加活动描述
            activity_desc = []
            
            # 位置信息
            if position_hint:
                activity_desc.append(position_hint)
            
            # 活动强度
            if activity_level == 'high':
                if has_movement:
                    activity_desc.append("持续活动并移动")
                else:
                    activity_desc.append("持续停留")
            elif activity_level == 'medium':
                if has_movement:
                    activity_desc.append("活动并移动")
                else:
                    activity_desc.append("短暂停留")
            else:
                activity_desc.append("短暂出现")
            
            # 持续时间（如果帧跨度较大）
            if frame_span > 5:
                # 假设每帧约 1 秒（根据采样率）
                estimated_duration = frame_span
                if estimated_duration >= 10:
                    activity_desc.append(f"约{estimated_duration}秒")
            
            if activity_desc:
                desc += f"，{''.join(activity_desc)}"
            else:
                desc += "出现"
            
            people_summary.append(desc)
        
        # 去重并格式化
        unique_summary = list(set(people_summary))
        
        if len(unique_summary) == 1:
            return unique_summary[0]
        else:
            return '、'.join(unique_summary)
    
    def _detect_movement(self, bboxes: List[Tuple]) -> bool:
        """
        检测是否有移动（基于 bbox 中心点的变化）
        
        Args:
            bboxes: bbox 列表 [(x1, y1, x2, y2), ...]
        
        Returns:
            True 如果检测到明显移动
        """
        if len(bboxes) < 2:
            return False
        
        # 计算中心点
        centers = []
        for bbox in bboxes:
            if len(bbox) >= 4:
                x1, y1, x2, y2 = bbox[:4]
                center_x = (x1 + x2) / 2
                center_y = (y1 + y2) / 2
                centers.append((center_x, center_y))
        
        if len(centers) < 2:
            return False
        
        # 计算中心点的变化范围
        x_coords = [c[0] for c in centers]
        y_coords = [c[1] for c in centers]
        
        x_range = max(x_coords) - min(x_coords)
        y_range = max(y_coords) - min(y_coords)
        
        # 如果中心点变化超过 bbox 宽高的 20%，认为有移动
        if len(bboxes) > 0 and len(bboxes[0]) >= 4:
            x1, y1, x2, y2 = bboxes[0][:4]
            width = x2 - x1
            height = y2 - y1
            
            if width > 0 and height > 0:
                x_threshold = width * 0.2
                y_threshold = height * 0.2
                
                if x_range > x_threshold or y_range > y_threshold:
                    return True
        
        return False
    
    def _analyze_activity_level(self, detection_count: int, frame_span: int, has_movement: bool) -> str:
        """
        分析活动强度
        
        Args:
            detection_count: 检测次数
            frame_span: 帧跨度
            has_movement: 是否有移动
        
        Returns:
            'high', 'medium', 'low'
        """
        # 检测密度 = 检测次数 / 帧跨度
        if frame_span > 0:
            density = detection_count / frame_span
        else:
            density = 0
        
        if density > 0.8 and detection_count > 10:
            return 'high'
        elif density > 0.5 and detection_count > 5:
            return 'medium'
        else:
            return 'low'
    
    def _analyze_position(self, camera: str, bboxes: List[Tuple]) -> Optional[str]:
        """
        分析位置信息（基于摄像头和 bbox）
        
        Args:
            camera: 摄像头名称
            bboxes: bbox 列表
        
        Returns:
            位置描述字符串，如 "在门口"、"在画面中心" 等
        """
        if not bboxes:
            return None
        
        # 摄像头位置映射
        camera_positions = {
            'doorbell': '门口',
            'outdoor_high': '庭院',
            'outdoor_side': '侧院',
            'indoor_living': '客厅',
            'indoor_hall': '门厅',
            'indoor_kitchen': '厨房',
            'indoor_bedroom': '卧室',
        }
        
        position = camera_positions.get(camera, camera)
        
        # 分析 bbox 位置（如果有多帧数据）
        if len(bboxes) > 0:
            # 可以进一步分析 bbox 在画面中的位置（中心、边缘等）
            # 这里先简单返回摄像头位置
            return f"在{position}"
        
        return None
    
    def _get_person_name(self, person_id: int) -> str:
        """
        获取人物名称（简化版，实际应该查询数据库）
        
        Args:
            person_id: 人物ID
        
        Returns:
            人物名称
        """
        # TODO: 实际应该查询数据库获取名称
        # 这里先返回通用名称
        if person_id:
            return f"Person_{person_id}"
        return "Unknown"
    
    def _detect_spatial_movement(self, global_event: Dict[str, Any]) -> Optional[str]:
        """
        检测空间移动逻辑（如从室外到室内）
        
        Args:
            global_event: Global_Event 对象
        
        Returns:
            空间提示字符串，如果没有则返回 None
        """
        cameras = global_event.get('cameras', [])
        
        if len(cameras) < 2:
            return None
        
        # 简单的空间逻辑检测
        # 假设摄像头名称包含 "outdoor"、"indoor"、"doorbell" 等关键词
        
        outdoor_keywords = ['outdoor', 'doorbell', 'gate', 'yard']
        indoor_keywords = ['indoor', 'living', 'room', 'hall']
        
        has_outdoor = any(any(kw in cam.lower() for kw in outdoor_keywords) 
                         for cam in cameras)
        has_indoor = any(any(kw in cam.lower() for kw in indoor_keywords) 
                        for cam in cameras)
        
        if has_outdoor and has_indoor:
            return "人物从室外移动到室内"
        
        return None
    
    def _detect_event_type(self, global_event: Dict[str, Any]) -> Optional[str]:
        """
        检测事件类型（基于人物行为模式、位置、活动特征等）
        
        Args:
            global_event: Global_Event 对象
        
        Returns:
            事件类型：'delivery', 'service', 'dangerous', 'visitor', 'normal' 或 None
        """
        cameras = global_event.get('cameras', [])
        people_info = global_event.get('people_info', {})
        clips = global_event.get('clips', [])
        duration = global_event.get('duration', 0)
        
        # 1. 检测危险行为（持枪、可疑行为等）
        # 基于位置、活动模式、持续时间等特征
        if self._is_dangerous_event(clips, people_info, cameras):
            return 'dangerous'
        
        # 2. 检测快递/配送事件
        if self._is_delivery_event(clips, people_info, cameras, duration):
            return 'delivery'
        
        # 3. 检测服务事件（维修、清洁等）
        if self._is_service_event(clips, people_info, cameras, duration):
            return 'service'
        
        # 4. 检测访客事件
        if self._is_visitor_event(clips, people_info, cameras):
            return 'visitor'
        
        # 5. 默认：正常活动
        return 'normal'
    
    def _is_dangerous_event(self, clips: List[Dict], people_info: Dict, cameras: List[str]) -> bool:
        """
        检测是否为危险事件（持枪、可疑行为等）
        
        特征：
        - 陌生人出现在敏感位置（门口、室内）
        - 活动模式异常（快速移动、长时间停留、反复出现）
        - 可能有武器特征（需要进一步分析，这里先基于行为模式）
        """
        # 检查是否有陌生人在敏感位置
        has_stranger = False
        for person_id, info in people_info.items():
            if person_id == -1 or info.get('role') in ['stranger', 'unknown']:
                has_stranger = True
                break
        
        if not has_stranger:
            return False
        
        # 检查是否在敏感位置（门口、室内）
        sensitive_cameras = ['doorbell', 'indoor_living', 'indoor_hall', 'indoor_kitchen', 'indoor_bedroom']
        has_sensitive_location = any(cam in sensitive_cameras for cam in cameras)
        
        if not has_sensitive_location:
            return False
        
        # 检查活动模式（快速移动、异常停留等）
        # 这里可以进一步分析，目前先基于位置和陌生人判断
        # TODO: 可以添加更复杂的模式检测（如：快速移动、反复出现等）
        
        return False  # 暂时不启用，需要更多数据支持
    
    def _is_delivery_event(self, clips: List[Dict], people_info: Dict, 
                          cameras: List[str], duration: float) -> bool:
        """
        检测是否为快递/配送事件
        
        特征：
        - 陌生人出现在门口（doorbell 摄像头）
        - 短暂停留（通常 < 2 分钟）
        - 活动模式：出现 → 停留 → 离开
        - 可能拿着物品（需要从描述中推断，这里先基于模式）
        """
        # 检查是否在门口
        has_doorbell = 'doorbell' in cameras
        
        if not has_doorbell:
            return False
        
        # 检查是否有陌生人
        has_stranger = False
        for person_id, info in people_info.items():
            if person_id == -1 or info.get('role') in ['stranger', 'unknown']:
                has_stranger = True
                break
        
        if not has_stranger:
            return False
        
        # 检查持续时间（快递通常是短暂的）
        if duration > 0 and duration < 120:  # 小于 2 分钟
            return True
        
        # 检查活动模式：短暂停留
        if len(clips) <= 3:  # 只有少数几个 clip，可能是短暂停留
            return True
        
        return False
    
    def _is_service_event(self, clips: List[Dict], people_info: Dict, 
                         cameras: List[str], duration: float) -> bool:
        """
        检测是否为服务事件（维修、清洁等）
        
        特征：
        - 陌生人出现
        - 持续时间较长（> 5 分钟）
        - 可能涉及多个位置（室内、室外）
        - 活动模式：进入 → 长时间停留 → 离开
        """
        # 检查是否有陌生人
        has_stranger = False
        for person_id, info in people_info.items():
            if person_id == -1 or info.get('role') in ['stranger', 'unknown']:
                has_stranger = True
                break
        
        if not has_stranger:
            return False
        
        # 检查持续时间（服务通常是较长的）
        if duration > 300:  # 大于 5 分钟
            return True
        
        # 检查是否涉及多个位置（室内 + 室外）
        indoor_cams = ['indoor_living', 'indoor_hall', 'indoor_kitchen', 'indoor_bedroom']
        outdoor_cams = ['doorbell', 'outdoor_high', 'outdoor_side']
        
        has_indoor = any(cam in indoor_cams for cam in cameras)
        has_outdoor = any(cam in outdoor_cams for cam in cameras)
        
        if has_indoor and has_outdoor:
            return True
        
        return False
    
    def _is_visitor_event(self, clips: List[Dict], people_info: Dict, cameras: List[str]) -> bool:
        """
        检测是否为访客事件
        
        特征：
        - 陌生人出现
        - 在门口停留并进入
        - 持续时间中等（2-10 分钟）
        """
        # 检查是否有陌生人
        has_stranger = False
        for person_id, info in people_info.items():
            if person_id == -1 or info.get('role') in ['stranger', 'unknown']:
                has_stranger = True
                break
        
        if not has_stranger:
            return False
        
        # 检查是否从门口进入室内
        indoor_cams = ['indoor_living', 'indoor_hall', 'indoor_kitchen', 'indoor_bedroom']
        has_doorbell = 'doorbell' in cameras
        has_indoor = any(cam in indoor_cams for cam in cameras)
        
        if has_doorbell and has_indoor:
            return True
        
        return False
    
    def _get_event_type_description(self, event_type: str) -> str:
        """
        获取事件类型的描述
        
        Args:
            event_type: 事件类型
        
        Returns:
            事件类型描述
        """
        descriptions = {
            'delivery': '快递/配送事件（人物在门口短暂停留，可能拿着包裹）',
            'service': '服务事件（维修、清洁等，人物长时间停留）',
            'dangerous': '危险事件（持枪、可疑行为等，需要特别注意）',
            'visitor': '访客事件（陌生人进入室内）',
            'normal': '正常活动事件'
        }
        
        return descriptions.get(event_type, '未知事件类型')
    
    def _get_event_type_hint(self, event_type: str) -> Optional[str]:
        """
        获取事件类型的温和提示（仅作为参考信息，不强制）
        
        Args:
            event_type: 事件类型
        
        Returns:
            温和的提示信息，如果不需要提示则返回 None
        """
        # 只对非正常事件提供提示，且提示要温和
        hints = {
            'delivery': '注意观察人物是否拿着物品、在门口短暂停留等特征',
            'service': '注意观察人物是否携带工具、长时间停留等特征',
            'dangerous': '注意观察人物行为是否异常、是否有可疑动作等特征',
            'visitor': '注意观察人物是否从门口进入室内等特征',
        }
        
        # 返回温和的提示，不强制要求
        hint = hints.get(event_type)
        if hint:
            return f"根据观察到的人物动作和活动模式，{hint}，自然地判断事件类型"
        
        return None

