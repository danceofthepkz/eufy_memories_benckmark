"""
Phase 1: 视觉扫描与特征提取
模块化实现，包含6个核心模块
"""

from .data_loader import DataLoader
from .frame_sampler import FrameSampler
from .yolo_detector import YoloDetector, PersonCrop
from .feature_encoder import FeatureEncoder
from .identity_arbiter import IdentityArbiter
from .result_buffer import ResultBuffer
from .simple_tracker import SimpleTracker, TrackedPerson
from .cv_pipeline import CV_Pipeline

__all__ = [
    'DataLoader',
    'FrameSampler',
    'YoloDetector',
    'PersonCrop',
    'FeatureEncoder',
    'IdentityArbiter',
    'ResultBuffer',
    'SimpleTracker',
    'TrackedPerson',
    'CV_Pipeline',
]

