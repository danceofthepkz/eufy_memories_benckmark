#!/usr/bin/env python3
"""
创建初始身体特征缓存脚本
从视频中提取人物特征，优先通过人脸匹配确认身份，确保人脸和身体特征对应正确
策略：从多个视频中寻找有正脸的帧，确认身份后再提取身体特征
"""

import sys
import os
import logging
from pathlib import Path
from datetime import datetime
import psycopg2
import numpy as np
from dotenv import load_dotenv

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from workflow.phase1_cv_scanning import (
    DataLoader,
    FrameSampler,
    YoloDetector,
    FeatureEncoder,
    PersonCrop,
    IdentityArbiter
)

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_db_config():
    """获取数据库配置"""
    return {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': os.getenv('POSTGRES_PORT', '5432'),
        'database': os.getenv('POSTGRES_DB', 'neweufy'),
        'user': os.getenv('POSTGRES_USER', 'postgres'),
        'password': os.getenv('POSTGRES_PASSWORD', 'eufy123')
    }


def find_faces_in_videos(max_videos=10):
    """
    从多个视频中寻找有正脸的帧，通过人脸匹配确认身份
    
    Args:
        max_videos: 最多处理多少个视频
        
    Returns:
        Dict[int, Dict]: {person_id: {body_vec, face_vec, video_path, frame_idx, ...}}
    """
    logger.info("=" * 60)
    logger.info("从多个视频中寻找有正脸的帧，确认身份")
    logger.info("=" * 60)
    
    # 初始化组件
    dataset_json = project_root / 'memories_ai_benchmark' / 'long_mem_dataset.json'
    videos_dir = project_root / 'memories_ai_benchmark' / 'videos'
    
    loader = DataLoader(str(dataset_json), str(videos_dir))
    sampler = FrameSampler()
    detector = YoloDetector('yolov8n.pt', conf_threshold=0.3)
    encoder = FeatureEncoder(face_model_name='buffalo_l', reid_model_name='osnet_x1_0')
    arbiter = IdentityArbiter()
    
    # 获取所有视频记录
    all_records = loader.get_all_records()
    if not all_records:
        logger.error("❌ 没有找到视频记录")
        return {}
    
    # 限制处理的视频数量
    records_to_process = all_records[:max_videos]
    logger.info(f"📹 将处理前 {len(records_to_process)} 个视频，寻找有正脸的帧...")
    
    matched_persons = {}  # {person_id: {body_vec, face_vec, ...}}
    
    # 获取所有家人ID
    db_config = get_db_config()
    try:
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        cur.execute("SELECT id FROM persons WHERE role = 'owner' ORDER BY id")
        all_family_ids = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()
        logger.info(f"📋 需要为 {len(all_family_ids)} 个家人找到身体特征")
    except Exception as e:
        logger.error(f"❌ 无法获取家人列表: {e}")
        return {}
    
    # 遍历视频，寻找有正脸的帧
    for video_idx, record in enumerate(records_to_process, 1):
        if len(matched_persons) >= len(all_family_ids):
            logger.info(f"\n✅ 已为所有家人找到身体特征，停止搜索")
            break
        
        video_path = record.get('video_path')
        logger.info(f"\n[{video_idx}/{len(records_to_process)}] 处理视频: {video_path}")
        
        # 解析视频路径
        result = loader.parse(record)
        if result is None:
            logger.warning(f"   ⚠️  跳过无效记录")
            continue
        
        video_path, timestamp, camera = result
        
        # 采样帧
        frames = sampler.get_frames(video_path, fps=1.0)
        if not frames:
            logger.warning(f"   ⚠️  无法提取帧")
            continue
        
        logger.info(f"   提取了 {len(frames)} 帧")
        
        # 遍历帧，寻找有正脸的人物
        found_in_this_video = False
        
        for frame_idx, frame in enumerate(frames):
            if len(matched_persons) >= len(all_family_ids):
                break
            
            person_crops = detector.detect_persons(frame)
            
            if len(person_crops) == 0:
                continue
            
            for crop_idx, crop in enumerate(person_crops):
                if len(matched_persons) >= len(all_family_ids):
                    break
                
                # 提取特征
                vectors = encoder.extract(crop)
                body_vec = vectors.get('body_vec')
                face_vec = vectors.get('face_vec')
                
                if body_vec is None:
                    continue
                
                # 如果有正脸，尝试通过人脸匹配确认身份
                if face_vec is not None:
                    logger.info(f"   帧 {frame_idx + 1}, 人物 {crop_idx + 1}: 检测到正脸，尝试匹配...")
                    
                    # 通过人脸匹配确认身份
                    identity = arbiter.identify(vectors, timestamp)
                    
                    if identity.get('person_id') and identity.get('role') == 'family':
                        person_id = identity['person_id']
                        
                        # 如果这个person_id还没有匹配过，保存
                        if person_id not in matched_persons:
                            matched_persons[person_id] = {
                                'body_vec': body_vec,
                                'face_vec': face_vec,
                                'bbox': crop.bbox,
                                'confidence': crop.confidence,
                                'video_path': video_path,
                                'frame_idx': frame_idx,
                                'crop_idx': crop_idx,
                                'match_method': 'face'
                            }
                            
                            logger.info(f"   ✅ 匹配成功: Person ID {person_id} (人脸匹配)")
                            logger.info(f"      身体特征维度: {body_vec.shape}")
                            found_in_this_video = True
        
        if found_in_this_video:
            logger.info(f"   ✅ 在此视频中找到 {sum(1 for p in matched_persons.values() if p.get('video_path') == video_path)} 个匹配")
    
    logger.info(f"\n✅ 通过人脸匹配找到 {len(matched_persons)} 个家人的身体特征")
    
    return matched_persons


def extract_backs_for_missing(matched_persons, max_videos=5):
    """
    为没有找到正脸的家人，从第一个视频提取背影特征
    
    Args:
        matched_persons: 已匹配的家人字典
        max_videos: 最多处理多少个视频寻找背影
        
    Returns:
        Dict[int, Dict]: 更新后的 matched_persons
    """
    # 获取所有家人ID
    db_config = get_db_config()
    try:
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        cur.execute("SELECT id FROM persons WHERE role = 'owner' ORDER BY id")
        all_family_ids = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"❌ 无法获取家人列表: {e}")
        return matched_persons
    
    missing_ids = [pid for pid in all_family_ids if pid not in matched_persons]
    
    if not missing_ids:
        logger.info("   ✅ 所有家人都已通过人脸匹配确认身份")
        return matched_persons
    
    logger.info(f"\n" + "=" * 60)
    logger.info("策略2: 为缺失的家人提取背影特征")
    logger.info("=" * 60)
    logger.info(f"   还需要为 {len(missing_ids)} 个家人提取身体特征")
    logger.info(f"   缺失的家人ID: {missing_ids}")
    logger.warning("\n⚠️  警告: 以下家人无法通过人脸匹配确认身份")
    logger.warning("   将使用背影特征，但无法保证对应关系正确")
    logger.warning("   建议: 检查视频中是否有这些家人的正脸")
    
    # 初始化组件
    dataset_json = project_root / 'memories_ai_benchmark' / 'long_mem_dataset.json'
    videos_dir = project_root / 'memories_ai_benchmark' / 'videos'
    
    loader = DataLoader(str(dataset_json), str(videos_dir))
    sampler = FrameSampler()
    detector = YoloDetector('yolov8n.pt', conf_threshold=0.3)
    encoder = FeatureEncoder(face_model_name='buffalo_l', reid_model_name='osnet_x1_0')
    
    # 从第一个视频提取背影
    all_records = loader.get_all_records()
    if not all_records:
        return matched_persons
    
    first_record = all_records[0]
    result = loader.parse(first_record)
    if result is None:
        return matched_persons
    
    video_path, timestamp, camera = result
    logger.info(f"\n📹 从第一个视频提取背影: {video_path}")
    
    frames = sampler.get_frames(video_path, fps=1.0)
    if not frames:
        return matched_persons
    
    # 收集未匹配的背影特征
    unmatched_bodies = []
    
    for frame_idx, frame in enumerate(frames[:30]):  # 处理前30帧
        if len(unmatched_bodies) >= len(missing_ids):
            break
        
        person_crops = detector.detect_persons(frame)
        
        for crop_idx, crop in enumerate(person_crops):
            if len(unmatched_bodies) >= len(missing_ids):
                break
            
            vectors = encoder.extract(crop)
            body_vec = vectors.get('body_vec')
            face_vec = vectors.get('face_vec')
            
            # 只收集没有正脸的（背影），且与已匹配的不重复
            if body_vec is not None and face_vec is None:
                # 检查是否与已匹配的重复
                is_duplicate = False
                for pid, data in matched_persons.items():
                    if data['body_vec'] is not None:
                        # 计算余弦相似度
                        similarity = np.dot(body_vec, data['body_vec']) / (
                            np.linalg.norm(body_vec) * np.linalg.norm(data['body_vec']) + 1e-8
                        )
                        if similarity > 0.9:  # 非常相似，可能是同一个人
                            is_duplicate = True
                            break
                
                if not is_duplicate:
                    unmatched_bodies.append({
                        'body_vec': body_vec,
                        'face_vec': None,
                        'bbox': crop.bbox,
                        'confidence': crop.confidence,
                        'video_path': video_path,
                        'frame_idx': frame_idx,
                        'crop_idx': crop_idx,
                        'match_method': 'back_only'
                    })
    
    # 按顺序分配给缺失的家人（但给出警告）
    for idx, person_id in enumerate(missing_ids):
        if idx < len(unmatched_bodies):
            matched_persons[person_id] = unmatched_bodies[idx]
            logger.warning(f"   ⚠️  Person ID {person_id}: 使用背影特征（未确认身份）")
        else:
            logger.warning(f"   ⚠️  Person ID {person_id}: 无法找到身体特征")
    
    return matched_persons


def save_to_database(matched_persons):
    """
    将身体特征保存到数据库作为家人的初始缓存
    
    Args:
        matched_persons: {person_id: {body_vec, ...}} 映射
    """
    if not matched_persons:
        logger.warning("⚠️  没有身体特征可保存")
        return
    
    db_config = get_db_config()
    
    try:
        conn = psycopg2.connect(**db_config)
        conn.autocommit = False
        cur = conn.cursor()
        
        logger.info("\n" + "=" * 60)
        logger.info("保存身体特征到数据库")
        logger.info("=" * 60)
        
        saved_count = 0
        face_matched_count = 0
        back_only_count = 0
        
        for person_id, data in matched_persons.items():
            # 获取家人名称
            cur.execute("SELECT name FROM persons WHERE id = %s", (person_id,))
            result = cur.fetchone()
            person_name = result[0] if result else f"Person_{person_id}"
            
            body_vec = data['body_vec']
            match_method = data.get('match_method', 'unknown')
            
            if body_vec is None:
                continue
            
            # 转换为字符串格式
            body_vec_str = '[' + ','.join(map(str, body_vec)) + ']'
            
            # 更新 current_body_embedding
            cur.execute("""
                UPDATE persons
                SET current_body_embedding = %s::vector,
                    body_update_time = %s,
                    last_seen = %s
                WHERE id = %s
            """, (body_vec_str, datetime.now(), datetime.now(), person_id))
            
            if match_method == 'face':
                logger.info(f"   ✅ {person_name} (ID: {person_id}): 已保存身体特征缓存 [人脸匹配确认]")
                face_matched_count += 1
            else:
                logger.warning(f"   ⚠️  {person_name} (ID: {person_id}): 已保存身体特征缓存 [仅背影，未确认身份]")
                back_only_count += 1
            
            logger.info(f"      特征维度: {body_vec.shape}, "
                       f"视频: {Path(data.get('video_path', '')).name}, "
                       f"帧: {data['frame_idx']}")
            
            saved_count += 1
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"\n✅ 成功保存 {saved_count} 个身体特征缓存")
        logger.info(f"   - 人脸匹配确认: {face_matched_count} 个")
        if back_only_count > 0:
            logger.warning(f"   - 仅背影（未确认）: {back_only_count} 个")
            logger.warning("   ⚠️  请检查这些家人的身体特征是否正确对应")
        
    except Exception as e:
        logger.error(f"❌ 保存失败: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
            conn.close()


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("创建初始身体特征缓存（智能匹配版本）")
    logger.info("=" * 60)
    logger.info("\n策略:")
    logger.info("1. 从多个视频中寻找有正脸的帧，通过人脸匹配确认身份")
    logger.info("2. 确保人脸和身体特征对应的是同一个人")
    logger.info("3. 如果没有正脸，使用背影特征（但会给出警告）")
    logger.info("")
    
    # 1. 从多个视频中寻找有正脸的帧
    matched_persons = find_faces_in_videos(max_videos=10)
    
    # 2. 为缺失的家人提取背影特征
    matched_persons = extract_backs_for_missing(matched_persons, max_videos=5)
    
    if not matched_persons:
        logger.error("❌ 未能提取到身体特征")
        return
    
    # 3. 保存到数据库
    save_to_database(matched_persons)
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ 完成！现在可以运行 Phase 1 测试了")
    logger.info("=" * 60)
    logger.info("\n💡 提示:")
    logger.info("   - 通过人脸匹配确认的身份，身体特征对应关系是可靠的")
    if any(data.get('match_method') == 'back_only' for data in matched_persons.values()):
        logger.warning("   - ⚠️  部分家人仅使用背影特征，请检查对应关系是否正确")
    logger.info("   - 运行: python workflow/phase1_cv_scanning/test_phase1.py")


if __name__ == '__main__':
    main()
