"""
Phase 0: 系统初始化 (Initialization)
职责：建立"认知基准"，加载家人底库并注册到数据库
"""

import os
import cv2
import numpy as np
import psycopg2
from pathlib import Path
from typing import Dict, Optional
from dotenv import load_dotenv
from insightface.app import FaceAnalysis
import logging

logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()


class LibraryLoader:
    """读取底库模块 - 扫描lib文件夹并提取特征向量"""
    
    def __init__(self, face_model_name: str = 'buffalo_l'):
        """
        初始化底库加载器
        
        Args:
            face_model_name: InsightFace 模型名称
        """
        logger.info(f"🔧 初始化底库加载器，加载 InsightFace 模型: {face_model_name}")
        try:
            self.face_analyzer = FaceAnalysis(
                name=face_model_name,
                providers=['CPUExecutionProvider']
            )
            self.face_analyzer.prepare(ctx_id=0, det_size=(640, 640))
            logger.info("✅ InsightFace 模型加载成功")
        except Exception as e:
            logger.error(f"❌ InsightFace 模型加载失败: {e}")
            raise
    
    def load_library(self, lib_path: str) -> Dict[str, np.ndarray]:
        """
        扫描 lib 文件夹，提取每张家人照片的特征向量
        
        Args:
            lib_path: lib 文件夹路径（如 'memories_ai_benchmark/lib'）
            
        Returns:
            字典: {图片ID: 512维特征向量}
                例如: {'1': np.ndarray(512), '2': np.ndarray(512), ...}
        """
        lib_dir = Path(lib_path)
        
        if not lib_dir.exists():
            logger.warning(f"⚠️  底库目录不存在: {lib_path}")
            return {}
        
        logger.info(f"📂 扫描底库目录: {lib_path}")
        
        lib_dict = {}
        
        # 扫描所有图片文件（支持 .jpeg, .jpg, .png）
        image_extensions = ['.jpeg', '.jpg', '.png']
        image_files = []
        for ext in image_extensions:
            image_files.extend(lib_dir.glob(f"*{ext}"))
        
        if not image_files:
            logger.warning(f"⚠️  底库目录中没有找到图片文件")
            return {}
        
        logger.info(f"📸 找到 {len(image_files)} 张图片")
        
        for img_path in image_files:
            img_id = img_path.stem  # 例如 "1" 从 "1.jpeg"
            
            # 读取图片
            img = cv2.imread(str(img_path))
            
            if img is None:
                logger.warning(f"⚠️  无法读取图片: {img_path}")
                continue
            
            # 使用 ArcFace 提取 512维向量
            face_emb = self._extract_face_feature(img)
            
            if face_emb is not None:
                lib_dict[img_id] = face_emb
                logger.info(f"✅ 加载底库图片: {img_id} -> 特征维度: {face_emb.shape}")
            else:
                logger.warning(f"⚠️  图片 {img_id} 中未检测到人脸")
        
        logger.info(f"✅ 底库加载完成，共 {len(lib_dict)} 张有效图片")
        return lib_dict
    
    def _extract_face_feature(self, img: np.ndarray) -> Optional[np.ndarray]:
        """
        提取人脸特征 (ArcFace)
        
        Args:
            img: 图片 (BGR 格式)
            
        Returns:
            512维人脸特征向量，如果未检测到人脸则返回 None
        """
        try:
            # 检测人脸
            faces = self.face_analyzer.get(img)
            
            if len(faces) == 0:
                return None
            
            # 选择最大的人脸（通常质量最好）
            face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
            
            # 提取 512维向量
            face_emb = face.embedding.astype(np.float32)
            
            # 归一化
            face_emb = face_emb / (np.linalg.norm(face_emb) + 1e-8)
            
            return face_emb
            
        except Exception as e:
            logger.warning(f"⚠️  人脸特征提取失败: {e}")
            return None


class RegistryManager:
    """建立身份注册表模块 - 将底库数据写入数据库"""
    
    def __init__(self):
        """初始化注册管理器"""
        self.db_config = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': os.getenv('POSTGRES_PORT', '5432'),
            'database': os.getenv('POSTGRES_DB', 'neweufy'),
            'user': os.getenv('POSTGRES_USER', 'postgres'),
            'password': os.getenv('POSTGRES_PASSWORD', 'eufy123')
        }
        logger.info("✅ 注册管理器初始化完成")
    
    def register_family(self, lib_dict: Dict[str, np.ndarray], lib_path: str):
        """
        将底库数据注册到数据库
        
        Args:
            lib_dict: {图片ID: 512维特征向量}
            lib_path: lib 文件夹路径（用于记录 source_image）
        """
        if not lib_dict:
            logger.warning("⚠️  底库字典为空，跳过注册")
            return
        
        logger.info(f"📝 开始注册 {len(lib_dict)} 个家人到底库...")
        
        try:
            conn = psycopg2.connect(**self.db_config)
            conn.autocommit = False  # 使用事务
            
            cur = conn.cursor()
            
            registered_count = 0
            skipped_count = 0
            
            for img_id, face_emb in lib_dict.items():
                # 1. 检查 persons 表中是否已存在
                cur.execute("""
                    SELECT id FROM persons 
                    WHERE name = %s AND role = 'owner'
                """, (f"Family_{img_id}",))
                
                existing = cur.fetchone()
                
                if existing:
                    person_id = existing[0]
                    logger.info(f"  ℹ️  家人已存在: Family_{img_id} (ID: {person_id})")
                else:
                    # 2. 在 persons 表中创建记录：role='owner'
                    cur.execute("""
                        INSERT INTO persons (name, role, first_seen, last_seen)
                        VALUES (%s, 'owner', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        RETURNING id
                    """, (f"Family_{img_id}",))
                    
                    person_id = cur.fetchone()[0]
                    logger.info(f"  ✅ 创建家人记录: Family_{img_id} (ID: {person_id})")
                    registered_count += 1
                
                # 3. 检查 person_faces 表中是否已存在
                source_image = f"lib/{img_id}.jpeg"  # 假设是 .jpeg 格式
                cur.execute("""
                    SELECT id FROM person_faces 
                    WHERE person_id = %s AND source_image = %s
                """, (person_id, source_image))
                
                if cur.fetchone():
                    logger.debug(f"  ℹ️  人脸特征已存在: {source_image}")
                    skipped_count += 1
                else:
                    # 4. 在 person_faces 表中存入向量
                    face_emb_str = '[' + ','.join(map(str, face_emb)) + ']'
                    
                    cur.execute("""
                        INSERT INTO person_faces (person_id, embedding, source_image)
                        VALUES (%s, %s::vector, %s)
                    """, (person_id, face_emb_str, source_image))
                    
                    logger.info(f"  ✅ 存入人脸特征: {source_image} (Person ID: {person_id})")
            
            conn.commit()
            cur.close()
            conn.close()
            
            logger.info(f"\n✅ 注册完成:")
            logger.info(f"   - 新建家人记录: {registered_count}")
            logger.info(f"   - 新增人脸特征: {len(lib_dict) - skipped_count}")
            logger.info(f"   - 跳过已存在: {skipped_count}")
            
        except Exception as e:
            logger.error(f"❌ 注册失败: {e}")
            if conn:
                conn.rollback()
                conn.close()
            raise


class Phase0Initialization:
    """Phase 0: 系统初始化主类"""
    
    def __init__(self, face_model_name: str = 'buffalo_l'):
        """
        初始化 Phase 0
        
        Args:
            face_model_name: InsightFace 模型名称
        """
        self.loader = LibraryLoader(face_model_name)
        self.registry = RegistryManager()
        logger.info("✅ Phase 0 初始化完成")
    
    def run(self, lib_path: str):
        """
        执行完整的初始化流程
        
        Args:
            lib_path: lib 文件夹路径（如 'memories_ai_benchmark/lib'）
        """
        logger.info("=" * 60)
        logger.info("🎬 Phase 0: 系统初始化")
        logger.info("=" * 60)
        
        # 1. 读取底库 (Load Library)
        logger.info("\n📂 步骤 1: 读取底库")
        lib_dict = self.loader.load_library(lib_path)
        
        if not lib_dict:
            logger.error("❌ 底库加载失败，无法继续初始化")
            return False
        
        # 2. 建立身份注册表 (Registry)
        logger.info("\n📝 步骤 2: 建立身份注册表")
        try:
            self.registry.register_family(lib_dict, lib_path)
            logger.info("\n✅ Phase 0 初始化完成！")
            logger.info("   系统现在认识了'家人'的长相，但还不知道他们穿什么衣服。")
            return True
        except Exception as e:
            logger.error(f"❌ 注册失败: {e}")
            return False

