#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
最终测试：基于本地图片生成 Veo3 动画视频

完整流程：
1. 从 .env 加载配置
2. 上传本地图片到 OSS
3. 调用 Veo3 API 生成动画视频
4. 保存结果
"""

import sys
import os
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# 加载 .env 配置
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def upload_to_oss(image_path: str) -> str:
    """上传图片到 OSS 并返回公网 URL"""
    try:
        import oss2
    except ImportError:
        logger.error("❌ 需要安装 oss2: pip install oss2")
        raise
    
    # 从环境变量获取 OSS 配置
    access_key_id = os.getenv('OSS_ACCESS_KEY_ID')
    access_key_secret = os.getenv('OSS_ACCESS_KEY_SECRET')
    bucket_name = os.getenv('OSS_BUCKET_NAME', 'ai-story-agent')
    # 根据错误信息，bucket 在北京区
    endpoint = 'https://oss-cn-beijing.aliyuncs.com'
    
    if not access_key_id or not access_key_secret:
        logger.error(f"❌ OSS 配置不完整")
        logger.error(f"   OSS_ACCESS_KEY_ID: {bool(access_key_id)}")
        logger.error(f"   OSS_ACCESS_KEY_SECRET: {bool(access_key_secret)}")
        raise ValueError("OSS 配置不完整")
    
    logger.info(f"📤 上传图片到 OSS: {bucket_name}")
    
    # 初始化 OSS
    auth = oss2.Auth(access_key_id, access_key_secret)
    bucket = oss2.Bucket(auth, endpoint, bucket_name)
    
    # 生成 OSS 对象名
    filename = Path(image_path).name
    object_name = f"test_videos/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
    
    # 上传文件
    logger.info(f"   上传到: {object_name}")
    with open(image_path, 'rb') as f:
        bucket.put_object(object_name, f)
    
    # 生成公网 URL
    oss_url = f"https://{bucket_name}.oss-cn-hangzhou.aliyuncs.com/{object_name}"
    logger.info(f"✅ 上传成功")
    logger.info(f"   URL: {oss_url}")
    
    return oss_url


def generate_video(image_url: str) -> dict:
    """调用 Veo3 API 生成视频"""
    from services.video_service import Veo3Service, VideoAspectRatio
    
    # VEO3_API_KEY 复用 NANO_BANANA_API_KEY
    api_key = os.getenv('VEO3_API_KEY') or os.getenv('NANO_BANANA_API_KEY')
    if not api_key:
        logger.error("❌ VEO3_API_KEY 或 NANO_BANANA_API_KEY 未设置")
        raise ValueError("API Key 未设置")
    
    logger.info(f"🎬 初始化 Veo3 服务")
    video_service = Veo3Service(api_key=api_key)
    
    if not video_service.is_available():
        raise RuntimeError("Veo3 服务不可用")
    
    logger.info(f"✅ Veo3 服务已初始化")
    
    # 获取动画 Prompt
    prompt = video_service.get_default_animation_prompt()
    logger.info(f"📝 使用动画 Prompt (长度: {len(prompt)} 字)")
    
    # 生成视频
    logger.info(f"🚀 调用 Veo3 API 生成视频")
    logger.info(f"   图片 URL: {image_url[:60]}...")
    logger.info(f"   宽高比: 16:9")
    logger.info(f"   模型: veo3.1-fast")
    
    call_count = [0]
    
    def progress_callback(progress: int, status: str):
        call_count[0] += 1
        if call_count[0] % 2 == 0:  # 每隔一次打印
            logger.info(f"   进度: {progress}% - {status}")
    
    result = video_service.generate_from_image(
        image_url=image_url,
        prompt=prompt,
        aspect_ratio=VideoAspectRatio.LANDSCAPE_16_9,
        progress_callback=progress_callback,
        max_wait_time=600
    )
    
    if not result:
        raise RuntimeError("视频生成失败")
    
    return {
        'url': result.url,
        'oss_url': result.oss_url,
        'task_id': result.task_id,
    }


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Veo3 视频生成测试')
    parser.add_argument('--image', type=str, default='outputs/test_image.png', help='本地图片路径')
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("Veo3 动画视频生成测试")
    logger.info("=" * 80)
    
    try:
        # 1. 验证图片
        image_file = Path(args.image)
        if not image_file.exists():
            logger.error(f"❌ 图片不存在: {args.image}")
            return False
        
        logger.info(f"\n[步骤 0] 验证输入")
        logger.info(f"📸 图片: {image_file.absolute()}")
        logger.info(f"📏 大小: {image_file.stat().st_size / 1024:.2f} KB")
        
        # 2. 上传到 OSS
        logger.info(f"\n[步骤 1] 上传图片到 OSS")
        oss_url = upload_to_oss(args.image)
        
        # 3. 生成视频
        logger.info(f"\n[步骤 2] 调用 Veo3 API 生成视频")
        result = generate_video(oss_url)
        
        # 4. 输出结果
        logger.info("\n" + "=" * 80)
        logger.info("✅ 视频生成成功！")
        logger.info("=" * 80)
        logger.info(f"📹 视频 URL: {result['url']}")
        if result['oss_url']:
            logger.info(f"☁️  OSS URL: {result['oss_url']}")
        if result['task_id']:
            logger.info(f"🔑 任务 ID: {result['task_id']}")
        
        # 5. 保存结果
        output_file = Path("outputs") / f"veo3_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("Veo3 动画视频生成结果\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"生成时间: {datetime.now().isoformat()}\n\n")
            f.write("【输入】\n")
            f.write(f"原始图片: {args.image}\n")
            f.write(f"OSS 图片: {oss_url}\n\n")
            f.write("【输出】\n")
            f.write(f"视频 URL: {result['url']}\n")
            if result['oss_url']:
                f.write(f"OSS 视频: {result['oss_url']}\n")
            if result['task_id']:
                f.write(f"任务 ID: {result['task_id']}\n")
        
        logger.info(f"\n💾 结果已保存: {output_file}")
        logger.info("\n" + "=" * 80)
        logger.info("测试完成！")
        logger.info("=" * 80)
        
        return True
        
    except Exception as e:
        logger.error(f"\n❌ 错误: {e}", exc_info=True)
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
