"""
模块 4: 双模态特征编码模块 (Dual-Feature Encoder)
职责：把图片变成向量（人脸 + 身体）
"""

import cv2
import numpy as np
import torch
from typing import Dict, Optional
import logging
from insightface.app import FaceAnalysis

logger = logging.getLogger(__name__)

# 尝试导入 torchreid
try:
    import torchreid
    TORCHREID_AVAILABLE = True
except ImportError:
    TORCHREID_AVAILABLE = False
    logger.warning("⚠️  torchreid 未安装，将使用简化的身体特征提取")


class FeatureEncoder:
    """双模态特征编码模块"""
    
    def __init__(self, face_model_name: str = 'buffalo_l', reid_model_name: str = 'osnet_x1_0'):
        """
        初始化特征编码器
        
        Args:
            face_model_name: InsightFace 模型名称
            reid_model_name: ReID 模型名称（如 'osnet_x1_0', 'osnet_ibn_x1_0'）
        """
        # Face Branch: 初始化 ArcFace 模型
        logger.info(f"🔧 加载 InsightFace 模型: {face_model_name}")
        try:
            self.face_analyzer = FaceAnalysis(
                name=face_model_name,
                providers=['CPUExecutionProvider']
            )
            self.face_analyzer.prepare(ctx_id=0, det_size=(640, 640))
            logger.info("✅ InsightFace 模型加载成功")
        except Exception as e:
            logger.warning(f"⚠️  InsightFace 模型加载失败: {e}，将使用模拟模式")
            self.face_analyzer = None
        
        # Body Branch: 初始化 ReID 模型
        self.reid_model = None
        self.reid_model_name = reid_model_name
        
        if TORCHREID_AVAILABLE:
            try:
                logger.info(f"🔧 加载 ReID 模型: {reid_model_name}")
                self.reid_model = self._load_reid_model(reid_model_name)
                logger.info("✅ ReID 模型加载成功")
            except Exception as e:
                logger.warning(f"⚠️  ReID 模型加载失败: {e}，将使用简化实现")
                self.reid_model = None
        else:
            logger.warning("⚠️  torchreid 未安装，使用简化的身体特征提取")
            logger.info("   安装命令: pip install torchreid")
        
        logger.info("✅ 特征编码器初始化完成")
    
    def _load_reid_model(self, model_name: str = 'osnet_x1_0'):
        """
        加载 ReID 模型
        
        Args:
            model_name: 模型名称（如 'osnet_x1_0'）
            
        Returns:
            ReID 模型对象
        """
        # 构建模型（不指定类别数，只用于特征提取）
        model = torchreid.models.build_model(
            name=model_name,
            num_classes=1,  # 只用于特征提取，类别数不重要
            loss='softmax',
            pretrained=True  # 使用预训练权重
        )
        
        # 设置为评估模式
        model.eval()
        
        # 如果有GPU，移到GPU上
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        model = model.to(device)
        
        logger.info(f"   ReID 模型设备: {device}")
        
        return {
            'model': model,
            'device': device
        }
    
    def extract(self, person_crop) -> Dict[str, Optional[np.ndarray]]:
        """
        提取人脸和身体特征
        
        Args:
            person_crop: PersonCrop 对象，包含裁剪后的人物图片
            
        Returns:
            特征包: {
                'face_vec': np.ndarray (512维) 或 None,
                'body_vec': np.ndarray (512维或2048维，取决于模型)
            }
        """
        img = person_crop.image
        
        # Face Branch (人脸分支)
        face_vec = self._extract_face_feature(img)
        
        # Body Branch (躯干分支)
        body_vec = self._extract_body_feature(img)
        
        return {
            'face_vec': face_vec,
            'body_vec': body_vec
        }
    
    def _extract_face_feature(self, img: np.ndarray) -> Optional[np.ndarray]:
        """
        提取人脸特征 (ArcFace)
        
        Args:
            img: 人物图像 (BGR 格式)
            
        Returns:
            512维人脸特征向量，如果未检测到人脸或清晰度不够则返回 None
        """
        if self.face_analyzer is None:
            # 模拟模式：30% 概率返回人脸特征
            if np.random.rand() > 0.7:
                face_emb = np.random.rand(512).astype(np.float32)
                face_emb = face_emb / (np.linalg.norm(face_emb) + 1e-8)
                return face_emb
            return None
        
        try:
            # 检测人脸
            faces = self.face_analyzer.get(img)
            
            if len(faces) == 0:
                return None
            
            # 选择最大的人脸（通常质量最好）
            face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
            
            # 检查人脸清晰度（通过检测置信度）
            # 如果清晰度 > 阈值，提取特征
            if hasattr(face, 'det_score') and face.det_score < 0.5:
                return None
            
            # 提取 512维向量
            face_emb = face.embedding.astype(np.float32)
            
            # 归一化
            face_emb = face_emb / (np.linalg.norm(face_emb) + 1e-8)
            
            return face_emb
            
        except Exception as e:
            logger.warning(f"⚠️  人脸特征提取失败: {e}")
            return None
    
    def _extract_body_feature(self, img: np.ndarray) -> np.ndarray:
        """
        提取身体特征 (ReID)
        
        Args:
            img: 人物图像 (BGR 格式)
            
        Returns:
            身体特征向量（OSNet 通常是 512 维，但我们会扩展到 2048 维以保持兼容性）
        """
        if self.reid_model is not None:
            # 使用真正的 ReID 模型
            return self._extract_with_reid_model(img)
        
        # 降级方案：使用简化实现
        return self._extract_simple_body_feature(img)
    
    def _extract_with_reid_model(self, img: np.ndarray) -> np.ndarray:
        """
        使用真正的 ReID 模型提取特征
        
        Args:
            img: 人物图像 (BGR 格式)
            
        Returns:
            2048维身体特征向量
        """
        try:
            model = self.reid_model['model']
            device = self.reid_model['device']
            
            # 预处理图像
            # ReID 模型通常需要 RGB 格式，尺寸为 (256, 128)
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img_resized = cv2.resize(img_rgb, (128, 256))  # (width, height)
            
            # 转换为 torch tensor
            # 归一化到 [0, 1] 然后标准化
            img_tensor = torch.from_numpy(img_resized).float()
            img_tensor = img_tensor.permute(2, 0, 1)  # HWC -> CHW
            img_tensor = img_tensor / 255.0
            
            # ImageNet 标准化
            mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
            std = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)
            img_tensor = (img_tensor - mean) / std
            
            # 添加 batch 维度
            img_tensor = img_tensor.unsqueeze(0).to(device)
            
            # 提取特征
            with torch.no_grad():
                features = model(img_tensor)
                # 获取特征向量（通常是最后一层之前）
                if isinstance(features, tuple):
                    features = features[0]
                features = features.cpu().numpy().flatten()
            
            # OSNet 通常输出 512 维特征
            # 为了保持与数据库的兼容性（2048维），我们可以：
            # 1. 直接使用 512 维（需要修改数据库schema）
            # 2. 扩展到 2048 维（当前方案）
            
            feature_dim = len(features)
            
            if feature_dim < 2048:
                # 扩展到 2048 维（通过重复和归一化）
                # 方法：将特征重复多次，然后归一化
                repeat_times = (2048 // feature_dim) + 1
                extended_features = np.tile(features, repeat_times)[:2048]
                # 归一化
                extended_features = extended_features.astype(np.float32)
                extended_features = extended_features / (np.linalg.norm(extended_features) + 1e-8)
                return extended_features
            elif feature_dim > 2048:
                # 截断到 2048 维
                features = features[:2048].astype(np.float32)
                features = features / (np.linalg.norm(features) + 1e-8)
                return features
            else:
                # 正好 2048 维
                features = features.astype(np.float32)
                features = features / (np.linalg.norm(features) + 1e-8)
                return features
                
        except Exception as e:
            logger.warning(f"⚠️  ReID 模型特征提取失败: {e}，降级到简化实现")
            return self._extract_simple_body_feature(img)
    
    def _extract_simple_body_feature(self, img: np.ndarray) -> np.ndarray:
        """
        简化的身体特征提取（降级方案）
        
        Args:
            img: 人物图像 (BGR 格式)
            
        Returns:
            2048维身体特征向量
        """
        # Resize 到 ReID 标准尺寸
        img_resized = cv2.resize(img, (128, 256))
        img_gray = cv2.cvtColor(img_resized, cv2.COLOR_BGR2GRAY)
        
        # 提取直方图特征
        hist = cv2.calcHist([img_gray], [0], None, [256], [0, 256])
        hist = hist.flatten() / (hist.sum() + 1e-8)  # 归一化
        
        # 颜色特征 (HSV)
        hsv = cv2.cvtColor(img_resized, cv2.COLOR_BGR2HSV)
        h_hist = cv2.calcHist([hsv], [0], None, [180], [0, 180]).flatten()
        s_hist = cv2.calcHist([hsv], [1], None, [256], [0, 256]).flatten()
        
        # 组合特征
        simple_features = np.concatenate([hist, h_hist, s_hist])
        
        # 扩展到 2048 维
        if len(simple_features) < 2048:
            # 使用填充
            padding = np.random.randn(2048 - len(simple_features)) * 0.01
            body_emb = np.concatenate([simple_features, padding])
        else:
            body_emb = simple_features[:2048]
        
        # 归一化
        body_emb = body_emb.astype(np.float32)
        body_emb = body_emb / (np.linalg.norm(body_emb) + 1e-8)
        
        return body_emb
