"""
模块 3: 证据实物化模块 (Evidence Materializer)
职责：找到对应的图片，将数据库记录转化为可视化的证据
"""

import os
import cv2
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class EvidenceMaterializer:
    """证据实物化模块"""
    
    def __init__(self, videos_base_dir: Optional[str] = None, 
                 snapshots_dir: Optional[str] = None):
        """
        初始化证据实物化模块
        
        Args:
            videos_base_dir: 视频文件基础目录（用于回溯视频路径）
            snapshots_dir: 快照保存目录（如果为None，则使用临时目录）
        """
        self.videos_base_dir = videos_base_dir
        self.snapshots_dir = snapshots_dir or '/tmp/eufy_snapshots'
        
        # 创建快照目录
        os.makedirs(self.snapshots_dir, exist_ok=True)
        
        logger.debug(f"✅ EvidenceMaterializer 初始化完成 (snapshots_dir={self.snapshots_dir})")
    
    def materialize(self, retrieved_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        将检索结果实物化（添加图片路径/URL）
        
        Args:
            retrieved_records: 检索结果列表
        
        Returns:
            实物化后的结果列表，每个结果包含图片路径/URL
        """
        materialized_results = []
        
        for record in retrieved_records:
            if record.get('type') == 'summary':
                # 总结类型不需要图片
                materialized_results.append(record)
            elif record.get('type') == 'detail':
                # 详细事件需要提取图片
                materialized_record = self._materialize_event(record)
                materialized_results.append(materialized_record)
        
        logger.info(f"✅ 实物化完成: {len(materialized_results)} 条记录")
        
        return materialized_results
    
    def _materialize_event(self, event_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        为单个事件提取图片
        
        Args:
            event_record: 事件记录
        
        Returns:
            添加了图片信息的记录
        """
        event_id = event_record.get('event_id')
        video_filename = event_record.get('video_filename')
        start_time = event_record.get('start_time')
        appearances = event_record.get('appearances', [])
        
        # 为每个 appearance 提取图片
        materialized_appearances = []
        
        for appearance in appearances:
            appearance_id = appearance.get('appearance_id')
            person_id = appearance.get('person_id')
            
            # 尝试提取图片
            snapshot_path = self._extract_snapshot(
                video_filename=video_filename,
                timestamp=start_time,
                event_id=event_id,
                appearance_id=appearance_id,
                person_id=person_id
            )
            
            appearance_with_image = {
                **appearance,
                'snapshot_path': snapshot_path,
                'snapshot_url': self._generate_url(snapshot_path) if snapshot_path else None
            }
            
            materialized_appearances.append(appearance_with_image)
        
        event_record['appearances'] = materialized_appearances
        
        return event_record
    
    def _extract_snapshot(self, video_filename: Optional[str], 
                         timestamp: datetime,
                         event_id: str,
                         appearance_id: int,
                         person_id: Optional[int]) -> Optional[str]:
        """
        从视频中提取快照
        
        Args:
            video_filename: 视频文件名
            timestamp: 时间戳
            event_id: 事件ID
            appearance_id: 出场记录ID
            person_id: 人物ID
        
        Returns:
            快照文件路径或 None
        """
        if not video_filename:
            logger.warning("⚠️  视频文件名为空，无法提取快照")
            return None
        
        # 构建视频文件路径
        if self.videos_base_dir:
            video_path = Path(self.videos_base_dir) / video_filename
        else:
            video_path = Path(video_filename)
        
        # 如果文件不存在，尝试其他可能的路径
        if not video_path.exists():
            # 尝试直接在当前目录查找
            alt_path = Path(video_filename)
            if alt_path.exists():
                video_path = alt_path
            else:
                logger.debug(f"⚠️  视频文件不存在: {video_path}，跳过图片提取")
                return None
        
        try:
            # 打开视频
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                logger.warning(f"⚠️  无法打开视频: {video_path}")
                return None
            
            # 获取视频 FPS
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0:
                fps = 15.0  # 默认 FPS
            
            # 计算目标帧（使用事件开始时间）
            # 假设视频从 timestamp 开始，我们提取第一帧
            target_frame = 0
            
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            ret, frame = cap.read()
            
            if not ret or frame is None:
                logger.warning(f"⚠️  无法读取视频帧: {video_path}")
                cap.release()
                return None
            
            # 保存快照
            snapshot_filename = f"event_{event_id}_appearance_{appearance_id}_person_{person_id}.jpg"
            snapshot_path = Path(self.snapshots_dir) / snapshot_filename
            
            cv2.imwrite(str(snapshot_path), frame)
            cap.release()
            
            logger.debug(f"✅ 提取快照成功: {snapshot_path}")
            
            return str(snapshot_path)
            
        except Exception as e:
            logger.error(f"❌ 提取快照失败: {e}")
            return None
    
    def _generate_url(self, snapshot_path: str) -> str:
        """
        生成图片 URL（用于前端访问）
        
        Args:
            snapshot_path: 本地文件路径
        
        Returns:
            URL 字符串
        """
        # 简化实现：返回相对路径
        # 实际应用中可能需要配置静态文件服务器 URL
        filename = Path(snapshot_path).name
        return f"/static/snapshots/{filename}"

