"""
第四阶段主 Pipeline: Persistence_Pipeline
整合所有模块，实现完整的结构化落库流程
"""

import logging
from typing import List, Dict, Any, Optional
import uuid

from .quality_selector import QualitySelector
from .vector_adapter import VectorAdapter
from .transaction_manager import TransactionManager, EventDAO, AppearanceDAO

logger = logging.getLogger(__name__)


class Persistence_Pipeline:
    """第四阶段：结构化落库 Pipeline"""
    
    def __init__(self, db_config: Optional[Dict[str, str]] = None):
        """
        初始化 Persistence Pipeline
        
        Args:
            db_config: 数据库配置字典（如果为None，从环境变量读取）
        """
        logger.info("=" * 60)
        logger.info("初始化 Persistence Pipeline (第四阶段)")
        logger.info("=" * 60)
        
        # 初始化各个模块
        self.selector = QualitySelector()                    # 模块 1
        self.adapter = VectorAdapter()                        # 模块 2
        self.tx_manager = TransactionManager(db_config)      # 模块 3
        self.event_dao = EventDAO(self.tx_manager)            # 模块 4
        self.appearance_dao = AppearanceDAO(self.tx_manager)  # 模块 4
        
        logger.info("✅ Persistence Pipeline 初始化完成")
    
    def save_event(self, global_event: Dict[str, Any]) -> Optional[uuid.UUID]:
        """
        将一个完整的 Global_Event 对象持久化到数据库
        
        流程：
        1. 开启事务
        2. 插入事件主表 (event_logs)
        3. 按人物分组，选择最佳检测
        4. 插入人物出场快照表 (event_appearances)
        5. 提交事务
        
        Args:
            global_event: Global_Event 对象（来自 Phase 3）
                必须包含：
                - start_time: datetime
                - end_time: datetime
                - cameras: List[str]
                - people: Set[int]
                - clips: List[Dict]
                - summary_text: str (LLM 生成的描述)
        
        Returns:
            事件 UUID（如果成功），否则返回 None
        """
        logger.info("=" * 60)
        logger.info("开始持久化事件")
        logger.info("=" * 60)
        
        # 验证必要字段
        if not self._validate_event(global_event):
            logger.error("❌ Global_Event 对象验证失败")
            return None
        
        summary_text = global_event.get('summary_text', '')
        if not summary_text:
            logger.warning("⚠️  事件没有 summary_text，使用默认描述")
            summary_text = "该事件已记录"
        
        try:
            # 开启事务
            with self.tx_manager.begin() as cursor:
                # --- A. 插入事件主表 ---
                logger.info("[步骤 1] 插入事件主表...")
                event_id = self.event_dao.insert_event(
                    cursor,
                    global_event,
                    summary_text
                )
                
                # --- B. 按人物分组，选择最佳检测 ---
                logger.info("[步骤 2] 按人物分组并选择最佳检测...")
                grouped_detections = self.selector.group_by_person(global_event)
                
                if not grouped_detections:
                    logger.warning("⚠️  事件中没有检测到任何人物")
                    return event_id
                
                # --- C. 处理陌生人，创建 persons 记录 ---
                logger.info("[步骤 3] 处理陌生人并创建 persons 记录...")
                stranger_person_ids = {}  # {stranger_key: person_id}
                
                for person_key in list(grouped_detections.keys()):
                    # 判断是否为陌生人
                    if isinstance(person_key, str) and person_key.startswith('stranger_'):
                        detection_list = grouped_detections[person_key]
                        # 为陌生人创建或查找 persons 记录
                        person_id = self._get_or_create_stranger_person(
                            cursor, person_key, detection_list, global_event
                        )
                        if person_id:
                            stranger_person_ids[person_key] = person_id
                            # 更新 grouped_detections，将 stranger_key 替换为实际的 person_id
                            grouped_detections[person_id] = grouped_detections.pop(person_key)
                            logger.info(f"✅ 陌生人 {person_key} → Person ID {person_id}")
                        else:
                            logger.warning(f"⚠️  无法为陌生人 {person_key} 创建 persons 记录，跳过")
                            grouped_detections.pop(person_key)
                
                # --- D. 插入人物出场快照表 ---
                logger.info("[步骤 4] 插入人物出场快照表...")
                appearances = []
                
                for person_id, detection_list in grouped_detections.items():
                    # 选择最佳检测
                    best_detection = self.selector.select_best(detection_list)
                    
                    if not best_detection:
                        logger.warning(f"⚠️  人物 {person_id} 没有有效的检测记录")
                        continue
                    
                    # 获取身体特征向量
                    body_embedding = best_detection.get('body_embedding')
                    if body_embedding is None:
                        logger.warning(f"⚠️  人物 {person_id} 的最佳检测没有 body_embedding")
                        continue
                    
                    # 转换向量格式
                    try:
                        body_embedding_pgvector = self.adapter.to_pgvector_body(body_embedding)
                    except Exception as e:
                        logger.error(f"❌ 向量转换失败 (person_id={person_id}): {e}")
                        continue
                    
                    # 获取匹配方法
                    match_method = best_detection.get('method', 'unknown')
                    # 标准化匹配方法名称
                    if match_method == 'face':
                        match_method = 'face'
                    elif match_method == 'body':
                        match_method = 'body_reid'
                    elif match_method == 'new':
                        match_method = 'new'
                    elif match_method in ['refined_from_suspected', 'refined_from_stranger', 'refined_from_context']:
                        # 处理 Phase 2 IdentityRefiner 优化的方法
                        # 这些通常基于身体特征，标记为 body_reid_refined
                        match_method = 'body_reid_refined'
                    else:
                        match_method = 'unknown'
                    
                    # 更新人物角色（如果 Phase 3 已经推断）
                    people_info = global_event.get('people_info', {})
                    if person_id in people_info:
                        inferred_role = people_info[person_id].get('role', None)
                        role_source = people_info[person_id].get('role_source', None)
                        
                        if inferred_role and role_source == 'behavior_inference':
                            # 映射角色名称到数据库值
                            db_role = self._map_role_to_db(inferred_role)
                            
                            # 更新 persons 表的角色
                            try:
                                cursor.execute("""
                                    UPDATE persons 
                                    SET role = %s, last_seen = %s, notes = COALESCE(notes || ' ', '') || %s
                                    WHERE id = %s
                                """, (
                                    db_role, 
                                    global_event.get('start_time'),
                                    f"[行为推断: {inferred_role}]",
                                    person_id
                                ))
                                logger.info(f"   更新人物 {person_id} 的角色: {inferred_role} → {db_role}")
                            except Exception as e:
                                logger.warning(f"   ⚠️  更新人物 {person_id} 角色失败: {e}")
                    
                    # 添加到列表
                    appearances.append({
                        'event_id': event_id,
                        'person_id': person_id,
                        'match_method': match_method,
                        'body_embedding_pgvector': body_embedding_pgvector
                    })
                
                # 批量插入
                if appearances:
                    self.appearance_dao.batch_insert_appearances(cursor, appearances)
                    logger.info(f"✅ 成功插入 {len(appearances)} 条人物出场记录")
                else:
                    logger.warning("⚠️  没有有效的人物出场记录需要插入")
            
            logger.info("=" * 60)
            logger.info(f"✅ 事件持久化成功: event_id={event_id}")
            logger.info("=" * 60)
            
            return event_id
            
        except Exception as e:
            logger.error(f"❌ 事件持久化失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def save_events(self, global_events: List[Dict[str, Any]]) -> List[uuid.UUID]:
        """
        批量保存多个事件
        
        Args:
            global_events: Global_Event 对象列表
        
        Returns:
            成功保存的事件 UUID 列表
        """
        logger.info("=" * 60)
        logger.info(f"开始批量持久化 {len(global_events)} 个事件")
        logger.info("=" * 60)
        
        saved_ids = []
        
        for idx, event in enumerate(global_events, 1):
            logger.info(f"\n[{idx}/{len(global_events)}] 处理事件...")
            
            event_id = self.save_event(event)
            if event_id:
                saved_ids.append(event_id)
        
        logger.info("\n" + "=" * 60)
        logger.info(f"✅ 批量持久化完成: 成功 {len(saved_ids)}/{len(global_events)}")
        logger.info("=" * 60)
        
        return saved_ids
    
    def _validate_event(self, global_event: Dict[str, Any]) -> bool:
        """
        验证 Global_Event 对象是否包含必要字段
        
        Args:
            global_event: Global_Event 对象
        
        Returns:
            如果验证通过返回 True，否则返回 False
        """
        required_fields = ['start_time', 'cameras', 'people', 'clips']
        
        for field in required_fields:
            if field not in global_event:
                logger.error(f"❌ 缺少必要字段: {field}")
                return False
        
        # 验证 clips 不为空
        clips = global_event.get('clips', [])
        if not clips:
            logger.warning("⚠️  clips 列表为空")
        
        return True
    
    def _get_or_create_stranger_person(self, cursor, stranger_key: str, 
                                       detection_list: List[Dict[str, Any]], 
                                       global_event: Dict[str, Any]) -> Optional[int]:
        """
        为陌生人获取或创建 persons 记录
        
        策略：
        1. 选择最佳检测（用于获取 body_embedding）
        2. 生成陌生人名称（基于事件时间和标识）
        3. 在 persons 表中创建新记录（role='unknown'）
        4. 返回新创建的 person_id
        
        Args:
            cursor: 数据库游标
            stranger_key: 陌生人唯一标识（如 'stranger_hash_xxx'）
            detection_list: 该陌生人的检测记录列表
            global_event: Global_Event 对象
        
        Returns:
            person_id (int) 或 None（如果创建失败）
        """
        # 选择最佳检测（用于获取 body_embedding）
        best_detection = self.selector.select_best(detection_list)
        if not best_detection:
            logger.warning(f"⚠️  陌生人 {stranger_key} 没有有效的检测记录")
            return None
        
        body_embedding = best_detection.get('body_embedding')
        if body_embedding is None:
            # 没有 body_embedding，无法创建记录
            logger.warning(f"⚠️  陌生人 {stranger_key} 没有 body_embedding，无法创建记录")
            return None
        
        # 生成陌生人名称（基于事件时间和标识）
        event_time = global_event.get('start_time')
        if event_time:
            timestamp_str = event_time.strftime('%Y%m%d_%H%M%S')
        else:
            timestamp_str = 'unknown'
        
        # 提取标识的后缀（如 'hash_xxx' 或 'unknown_0'）
        key_suffix = stranger_key.replace('stranger_', '')
        stranger_name = f"Stranger_{timestamp_str}_{key_suffix[:8]}"
        
        # 转换 body_embedding 格式
        try:
            body_embedding_str = self.adapter.to_pgvector_body(body_embedding)
        except Exception as e:
            logger.error(f"❌ 向量转换失败 (stranger_key={stranger_key}): {e}")
            return None
        
        # 获取推断的角色（如果 Phase 3 已经推断）
        inferred_role = 'unknown'
        people_info = global_event.get('people_info', {})
        if -1 in people_info:
            inferred_role_raw = people_info[-1].get('role', 'unknown')
            role_source = people_info[-1].get('role_source', None)
            # 如果角色是通过行为推断的，映射到数据库支持的角色
            if role_source == 'behavior_inference':
                inferred_role = self._map_role_to_db(inferred_role_raw)
            else:
                # 否则保持原角色，但需要映射
                inferred_role = self._map_role_to_db(inferred_role_raw)
        
        # 创建 persons 记录
        try:
            cursor.execute("""
                INSERT INTO persons (name, role, current_body_embedding, body_update_time, first_seen, last_seen)
                VALUES (%s, %s, %s::vector, %s, %s, %s)
                RETURNING id
            """, (
                stranger_name,
                inferred_role,
                body_embedding_str,
                event_time,
                event_time,
                event_time
            ))
            
            person_id = cursor.fetchone()[0]
            logger.info(f"✅ 为陌生人创建 persons 记录: {stranger_name} (ID: {person_id})")
            
            return person_id
            
        except Exception as e:
            logger.error(f"❌ 创建陌生人 persons 记录失败 (stranger_key={stranger_key}): {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _map_role_to_db(self, inferred_role: str) -> str:
        """
        将推断的角色映射到数据库支持的角色
        
        数据库支持的角色：'owner', 'visitor', 'unknown'
        
        Args:
            inferred_role: 推断的角色（如 'delivery', 'service', 'visitor' 等）
        
        Returns:
            数据库角色：'owner', 'visitor', 'unknown'
        """
        # 角色映射规则
        role_mapping = {
            'owner': 'owner',
            'family': 'owner',  # family 映射为 owner
            'visitor': 'visitor',
            'delivery': 'visitor',  # 快递员映射为 visitor（可以扩展数据库支持 delivery）
            'service': 'visitor',  # 服务人员映射为 visitor（可以扩展数据库支持 service）
            'stranger': 'unknown',
            'unknown': 'unknown'
        }
        
        return role_mapping.get(inferred_role, 'unknown')

