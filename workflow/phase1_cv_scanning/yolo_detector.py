"""
模块 3: 多目标检测模块 (ROI Detector)
职责：找出画面里所有的人，并把他们抠出来
"""

import cv2
import numpy as np
from ultralytics import YOLO
from typing import List, Tuple, Dict
import logging

logger = logging.getLogger(__name__)


class PersonCrop:
    """人物裁剪对象"""
    def __init__(self, image: np.ndarray, bbox: Tuple[int, int, int, int], confidence: float):
        """
        Args:
            image: 裁剪后的人物图片
            bbox: 边界框坐标 (x1, y1, x2, y2)
            confidence: 检测置信度
        """
        self.image = image
        self.bbox = bbox  # (x1, y1, x2, y2)
        self.confidence = confidence
        self.x1, self.y1, self.x2, self.y2 = bbox
        self.width = self.x2 - self.x1
        self.height = self.y2 - self.y1
        self.area = self.width * self.height
        # 计算中心点（用于判断是否在画面中心）
        self.center_x = (self.x1 + self.x2) / 2
        self.center_y = (self.y1 + self.y2) / 2


class YoloDetector:
    """多目标检测模块"""
    
    def __init__(self, model_path: str = 'yolov8n.pt', conf_threshold: float = 0.5):
        """
        初始化 YOLO 检测器
        
        Args:
            model_path: YOLO 模型路径
            conf_threshold: 置信度阈值
        """
        logger.info(f"🔧 加载 YOLO 模型: {model_path}")
        self.detector = YOLO(model_path)
        self.conf_threshold = conf_threshold
        logger.info("✅ YOLO 检测器初始化完成")
    
    def detect_persons(self, frame: np.ndarray) -> List[PersonCrop]:
        """
        检测画面中的所有人物
        
        Args:
            frame: 输入帧（BGR 格式）
            
        Returns:
            人物裁剪对象列表，每个包含裁剪后的图片和边界框信息
        """
        # 运行 YOLOv8 (Class=0, Person)
        # YOLO 内部已经包含 NMS (非极大值抑制)
        results = self.detector(frame, classes=0, verbose=False)
        
        person_crops = []
        
        for result in results:
            for box in result.boxes:
                # 获取边界框坐标 (x1, y1, x2, y2)
                x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
                confidence = float(box.conf[0].cpu().numpy())
                
                # 过滤低置信度检测
                if confidence < self.conf_threshold:
                    continue
                
                # 过滤太小的检测框
                if (x2 - x1) < 50 or (y2 - y1) < 50:
                    continue
                
                # ROI 裁剪 (Cropping): 根据坐标将每个人物从大图中裁剪成小图
                person_img = frame[y1:y2, x1:x2].copy()
                
                if person_img.size == 0:
                    continue
                
                # 创建 PersonCrop 对象
                crop = PersonCrop(
                    image=person_img,
                    bbox=(x1, y1, x2, y2),
                    confidence=confidence
                )
                
                person_crops.append(crop)
        
        logger.debug(f"🔍 检测到 {len(person_crops)} 个人物")
        
        return person_crops

