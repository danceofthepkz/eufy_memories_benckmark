"""
模块 2: 向量序列化适配器 (Vector Adapter)
职责：将 NumPy 数组转换为 PostgreSQL pgvector 格式
"""

import numpy as np
from typing import Union, List, Optional
import logging

logger = logging.getLogger(__name__)


class VectorAdapter:
    """向量序列化适配器"""
    
    # 标准向量维度
    FACE_DIM = 512
    BODY_DIM = 2048
    
    def __init__(self):
        """初始化适配器"""
        pass
    
    def to_pgvector(self, vector: Union[np.ndarray, List[float]], 
                    expected_dim: Optional[int] = None) -> str:
        """
        将向量转换为 PostgreSQL pgvector 格式的字符串
        
        pgvector 格式：'[0.12, -0.5, 0.8, ...]'
        
        Args:
            vector: NumPy 数组或 Python 列表
            expected_dim: 期望的维度（用于验证）
        
        Returns:
            pgvector 格式的字符串，例如：'[0.12, -0.5, 0.8, ...]'
        
        Raises:
            ValueError: 如果向量维度不匹配或格式错误
        """
        # 转换为 NumPy 数组
        if isinstance(vector, list):
            vector = np.array(vector, dtype=np.float32)
        elif isinstance(vector, np.ndarray):
            vector = vector.astype(np.float32)
        else:
            raise ValueError(f"不支持的向量类型: {type(vector)}")
        
        # 展平多维数组
        if vector.ndim > 1:
            vector = vector.flatten()
        
        # 验证维度
        actual_dim = len(vector)
        if expected_dim is not None and actual_dim != expected_dim:
            raise ValueError(
                f"向量维度不匹配: 期望 {expected_dim}, 实际 {actual_dim}"
            )
        
        # 转换为列表并格式化为字符串
        vector_list = vector.tolist()
        pgvector_str = '[' + ','.join(str(x) for x in vector_list) + ']'
        
        logger.debug(f"✅ 向量转换完成: {actual_dim} 维 → pgvector 格式")
        
        return pgvector_str
    
    def to_pgvector_face(self, vector: Union[np.ndarray, List[float]]) -> str:
        """
        将人脸向量转换为 pgvector 格式（512维）
        
        Args:
            vector: 人脸特征向量
        
        Returns:
            pgvector 格式的字符串
        """
        return self.to_pgvector(vector, expected_dim=self.FACE_DIM)
    
    def to_pgvector_body(self, vector: Union[np.ndarray, List[float]]) -> str:
        """
        将身体向量转换为 pgvector 格式（2048维）
        
        Args:
            vector: 身体特征向量
        
        Returns:
            pgvector 格式的字符串
        """
        return self.to_pgvector(vector, expected_dim=self.BODY_DIM)
    
    def validate_dimension(self, vector: Union[np.ndarray, List[float]], 
                          expected_dim: int) -> bool:
        """
        验证向量维度
        
        Args:
            vector: 向量
            expected_dim: 期望的维度
        
        Returns:
            如果维度匹配返回 True，否则返回 False
        """
        try:
            if isinstance(vector, list):
                actual_dim = len(vector)
            elif isinstance(vector, np.ndarray):
                actual_dim = vector.size if vector.ndim == 0 else len(vector.flatten())
            else:
                return False
            
            return actual_dim == expected_dim
        except Exception:
            return False
    
    def normalize(self, vector: Union[np.ndarray, List[float]]) -> np.ndarray:
        """
        归一化向量（L2 归一化）
        
        Args:
            vector: 向量
        
        Returns:
            归一化后的 NumPy 数组
        """
        if isinstance(vector, list):
            vector = np.array(vector, dtype=np.float32)
        
        norm = np.linalg.norm(vector)
        if norm == 0:
            logger.warning("⚠️  向量为零向量，无法归一化")
            return vector
        
        normalized = vector / norm
        logger.debug(f"✅ 向量归一化完成: 原始范数={norm:.4f}")
        
        return normalized

