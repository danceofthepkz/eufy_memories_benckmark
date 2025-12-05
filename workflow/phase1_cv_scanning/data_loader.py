"""
模块 1: 数据加载与对齐模块 (Data Loader & Aligner)
职责：负责把 JSON 元数据和物理视频文件对应起来
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class DataLoader:
    """数据加载与对齐模块"""
    
    def __init__(self, dataset_json_path: str, videos_base_dir: str):
        """
        初始化数据加载器
        
        Args:
            dataset_json_path: long_mem_dataset.json 的路径
            videos_base_dir: 视频文件的基础目录
        """
        self.dataset_json_path = Path(dataset_json_path)
        self.videos_base_dir = Path(videos_base_dir)
        self.dataset = None
        self._load_dataset()
    
    def _load_dataset(self):
        """加载 JSON 数据集"""
        try:
            with open(self.dataset_json_path, 'r', encoding='utf-8') as f:
                self.dataset = json.load(f)
            logger.info(f"✅ 成功加载数据集: {len(self.dataset)} 条记录")
        except Exception as e:
            logger.error(f"❌ 加载数据集失败: {e}")
            self.dataset = []
    
    def parse(self, json_record: Dict) -> Optional[Tuple[str, datetime, str]]:
        """
        解析 JSON 记录，返回视频路径和时间戳
        
        Args:
            json_record: JSON 记录，包含 video_path, camera, time
            
        Returns:
            (video_path, timestamp, camera) 或 None（如果文件不存在）
        """
        video_path = json_record.get('video_path')
        camera = json_record.get('camera', 'unknown')
        time_str = json_record.get('time')
        
        if not video_path or not time_str:
            logger.warning(f"⚠️  记录缺少必要字段: {json_record}")
            return None
        
        # 构建完整视频路径
        full_video_path = self.videos_base_dir / video_path
        
        # 验证视频文件是否存在
        if not full_video_path.exists():
            logger.warning(f"⚠️  视频文件不存在: {full_video_path}")
            return None
        
        # 解析时间字符串 "2025-09-01 09:00:00" 为 DateTime 对象
        try:
            timestamp = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        except ValueError as e:
            logger.error(f"❌ 时间解析失败: {time_str}, 错误: {e}")
            return None
        
        logger.debug(f"✅ 解析成功: {video_path} @ {timestamp} ({camera})")
        
        return str(full_video_path), timestamp, camera
    
    def get_all_records(self):
        """获取所有 JSON 记录"""
        return self.dataset if self.dataset else []
    
    def get_record_by_index(self, index: int) -> Optional[Dict]:
        """根据索引获取记录"""
        if self.dataset and 0 <= index < len(self.dataset):
            return self.dataset[index]
        return None

