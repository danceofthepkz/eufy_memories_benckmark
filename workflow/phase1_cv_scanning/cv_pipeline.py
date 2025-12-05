"""
第一阶段主 Pipeline: CV_Pipeline
整合所有6个模块，实现完整的视觉扫描与特征提取流程
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

from .data_loader import DataLoader
from .frame_sampler import FrameSampler
from .yolo_detector import YoloDetector
from .feature_encoder import FeatureEncoder
from .identity_arbiter import IdentityArbiter
from .result_buffer import ResultBuffer
from .simple_tracker import SimpleTracker

logger = logging.getLogger(__name__)


class CV_Pipeline:
    """第一阶段：视觉扫描与特征提取 Pipeline"""
    
    def __init__(self, 
                 dataset_json_path: str,
                 videos_base_dir: str,
                 yolo_model: str = 'yolov8n.pt',
                 face_model_name: str = 'buffalo_l',
                 reid_model_name: str = 'osnet_x1_0',
                 enable_tracking: bool = True,
                 iou_threshold: float = 0.7,
                 revalidate_interval: int = 5,
                 max_age: int = 3):
        """
        初始化 CV Pipeline
        
        Args:
            dataset_json_path: long_mem_dataset.json 的路径
            videos_base_dir: 视频文件的基础目录
            yolo_model: YOLO 模型路径
            face_model_name: InsightFace 模型名称
            reid_model_name: ReID 模型名称（如 'osnet_x1_0'）
            enable_tracking: 是否启用跟踪优化（跳过重复检测）
            iou_threshold: IoU 阈值，用于判断是否是同一个人
            revalidate_interval: 重新验证间隔（帧数），每 N 帧重新检测一次
            max_age: 跟踪最大年龄（帧数），超过此值未匹配则清除
        """
        logger.info("=" * 60)
        logger.info("初始化 CV Pipeline (第一阶段)")
        logger.info("=" * 60)
        
        # 初始化各个模块
        self.loader = DataLoader(dataset_json_path, videos_base_dir)      # 模块 1
        self.sampler = FrameSampler()                                      # 模块 2
        self.detector = YoloDetector(yolo_model)                          # 模块 3
        self.encoder = FeatureEncoder(face_model_name, reid_model_name)  # 模块 4
        self.arbiter = IdentityArbiter()                                  # 模块 5
        self.buffer = ResultBuffer()                                       # 模块 6
        
        # 初始化跟踪器（用于优化：跳过重复检测）
        self.enable_tracking = enable_tracking
        if enable_tracking:
            self.tracker = SimpleTracker(
                iou_threshold=iou_threshold,
                revalidate_interval=revalidate_interval,
                max_age=max_age
            )
            logger.info(f"✅ 跟踪优化已启用: IoU阈值={iou_threshold}, "
                       f"重新验证间隔={revalidate_interval}帧")
        else:
            self.tracker = None
            logger.info("⚠️  跟踪优化已禁用（将进行所有帧的完整检测）")
        
        logger.info("✅ CV Pipeline 初始化完成")
    
    def process_one_clip(self, json_record: Dict) -> Optional[Dict]:
        """
        处理单个视频片段
        
        Args:
            json_record: JSON 记录，包含 video_path, camera, time
        
        Returns:
            Clip_Obj: {
                'time': datetime,
                'cam': str,
                'people_detected': List[List[Dict]]
            } 或 None（如果处理失败）
        """
        # 1. Load: 解析 JSON 记录
        result = self.loader.parse(json_record)
        if result is None:
            return None
        
        video_path, timestamp, camera = result
        
        logger.info(f"🎬 处理视频: {video_path} @ {timestamp} ({camera})")
        
        # 重置跟踪器（每个视频开始时重置）
        if self.tracker:
            self.tracker.reset()
        
        # 2. Open Video: 采样帧
        frames, video_duration = self.sampler.get_frames(video_path, fps=1.0)
        if not frames:
            logger.warning(f"⚠️  视频无有效帧: {video_path}")
            return None
        
        clip_results = []
        stats = {
            'total_detections': 0,
            'skipped_detections': 0,
            'full_detections': 0
        }
        
        # 处理每一帧
        for frame_idx, frame in enumerate(frames):
            # 3. Detect (Multi-Object): 检测人物
            person_crops = self.detector.detect_persons(frame)
            
            if not person_crops:
                # 这一帧没有检测到人物
                clip_results.append([])
                # 清理过期的跟踪
                if self.tracker:
                    self.tracker.cleanup(frame_idx)
                continue
            
            frame_people = []
            
            for crop in person_crops:
                stats['total_detections'] += 1
                
                # 尝试匹配到已有跟踪（如果启用跟踪）
                track_id = None
                skip_detection = False
                
                if self.tracker:
                    track_id = self.tracker.match(crop.bbox, frame_idx)
                    
                    if track_id:
                        # 检查是否需要重新验证
                        if self.tracker.should_revalidate(track_id, frame_idx):
                            # 需要重新验证，进行完整检测
                            skip_detection = False
                        else:
                            # 可以跳过检测，复用上一帧的身份
                            skip_detection = True
                            stats['skipped_detections'] += 1
                
                if skip_detection:
                    # 跳过特征提取和身份识别，复用跟踪的身份
                    track = self.tracker.tracks[track_id]
                    identity = track.identity.copy()
                    
                    # 更新跟踪信息（只更新位置，不更新身份）
                    self.tracker.update_track(
                        track_id=track_id,
                        bbox=crop.bbox,
                        identity=None,  # 不更新身份
                        frame_idx=frame_idx,
                        skip_detection=True
                    )
                    
                    logger.debug(f"帧 {frame_idx}: 跳过检测 track_id={track_id}, "
                               f"person_id={identity.get('person_id')}")
                else:
                    # 进行完整检测：特征提取 + 身份识别
                    stats['full_detections'] += 1
                    
                    # 4. Encode: 提取特征
                    vectors = self.encoder.extract(crop)
                    
                    # 5. Arbitrate (Crucial Logic): 识别身份
                    # 注意：这里面包含了 update_db_cache 的副作用
                    identity = self.arbiter.identify(vectors, timestamp)
                    
                    # 更新或创建跟踪
                    if self.tracker:
                        if track_id:
                            # 更新已有跟踪
                            self.tracker.update_track(
                                track_id=track_id,
                                bbox=crop.bbox,
                                identity=identity,
                                frame_idx=frame_idx,
                                skip_detection=False
                            )
                        else:
                            # 创建新跟踪
                            track_id = self.tracker.create_track(
                                bbox=crop.bbox,
                                identity=identity,
                                frame_idx=frame_idx
                            )
                
                # 添加额外信息
                person_info = {
                    **identity,
                    'bbox': crop.bbox,
                    'confidence': crop.confidence,
                    'frame_idx': frame_idx
                }
                
                # 如果启用了跟踪，添加跟踪ID
                if self.tracker and track_id:
                    person_info['track_id'] = track_id
                
                frame_people.append(person_info)
            
            clip_results.append(frame_people)
            
            # 清理过期的跟踪
            if self.tracker:
                self.tracker.cleanup(frame_idx)
        
        # 6. Buffer: 创建 Clip_Obj（包含视频时长和路径）
        clip_obj = self.buffer.create_clip_obj(
            timestamp, 
            camera, 
            clip_results,
            video_duration=video_duration,
            video_path=video_path
        )
        
        # 输出统计信息
        skip_ratio = (stats['skipped_detections'] / stats['total_detections'] * 100 
                     if stats['total_detections'] > 0 else 0)
        
        logger.info(f"✅ 处理完成: {camera} @ {timestamp}, "
                   f"共 {len(frames)} 帧, 检测到人物 {stats['total_detections']} 次")
        
        if self.tracker and stats['total_detections'] > 0:
            logger.info(f"   📊 优化统计: 完整检测 {stats['full_detections']} 次, "
                       f"跳过 {stats['skipped_detections']} 次 "
                       f"({skip_ratio:.1f}%), "
                       f"节省计算量约 {skip_ratio:.1f}%")
            
            # 输出跟踪器统计
            tracker_stats = self.tracker.get_stats()
            if tracker_stats['total_tracks'] > 0:
                logger.debug(f"   跟踪统计: {tracker_stats['total_tracks']} 个跟踪, "
                           f"总跳过率 {tracker_stats['skip_ratio']*100:.1f}%")
        
        return clip_obj
    
    def process_all_clips(self, max_clips: Optional[int] = None) -> List[Dict]:
        """
        处理所有视频片段
        
        Args:
            max_clips: 最大处理数量（用于测试），None 表示处理全部
        
        Returns:
            Clip_Obj 列表
        """
        all_records = self.loader.get_all_records()
        
        if max_clips:
            all_records = all_records[:max_clips]
        
        logger.info(f"🚀 开始处理 {len(all_records)} 个视频片段")
        
        clip_objs = []
        
        for idx, record in enumerate(all_records, 1):
            logger.info(f"\n[{idx}/{len(all_records)}] 处理中...")
            
            clip_obj = self.process_one_clip(record)
            
            if clip_obj:
                clip_objs.append(clip_obj)
            else:
                logger.warning(f"⚠️  跳过无效记录: {record.get('video_path', 'unknown')}")
        
        logger.info(f"\n✅ 处理完成: 成功 {len(clip_objs)}/{len(all_records)}")
        
        return clip_objs

