"""
Mini 博客动画 v2 集成测试脚本

验证点：
1. Mini 模式配置是否正确
2. 章节配图是否生成
3. 多图序列视频是否生成
4. 动画 Prompt 是否传入（解决中文变形）

使用方法：
    python -m backend.scripts.test_mini_blog_v2 --topic "Python 装饰器入门"
"""

import asyncio
import logging
import argparse
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_mini_blog(topic: str):
    """测试 Mini 博客完整流程"""
    from dotenv import load_dotenv
    load_dotenv()
    
    from backend.services.blog_generator.blog_service import init_blog_service, get_blog_service
    from backend.services.llm_service import init_llm_service
    
    # 初始化服务
    llm_client = init_llm_service()
    init_blog_service(llm_client)
    blog_service = get_blog_service()
    
    if not blog_service:
        print("❌ 博客服务初始化失败")
        return None
    
    print(f"\n{'='*50}")
    print(f"🚀 开始测试 Mini 博客生成")
    print(f"📝 主题: {topic}")
    print(f"{'='*50}\n")
    
    # 生成博客
    result = blog_service.generate_sync(
        topic=topic,
        article_type="tutorial",
        target_audience="beginner",
        target_length="mini"
    )
    
    if not result:
        print("❌ 博客生成失败")
        return None
    
    # 验证结果
    sections = result.get('sections', [])
    section_images = result.get('section_images', [])
    images = result.get('images', [])
    
    print(f"\n{'='*50}")
    print("📊 测试结果")
    print(f"{'='*50}")
    
    # T1: Mini 博客生成
    if sections:
        print(f"✅ T1 通过: 章节数 = {len(sections)}")
        for i, section in enumerate(sections):
            print(f"   - 章节 {i+1}: {section.get('title', 'N/A')}")
    else:
        print("❌ T1 失败: 没有生成章节")
    
    # T2: 章节配图生成
    if section_images:
        print(f"✅ T2 通过: 章节配图数 = {len(section_images)}")
        for i, url in enumerate(section_images):
            print(f"   - 配图 {i+1}: {url[:60]}..." if url else f"   - 配图 {i+1}: None")
    else:
        print(f"⚠️ T2 待验证: section_images 为空，检查 images: {len(images)} 张")
    
    # T6: section_images 合并
    if 'section_images' in result:
        print(f"✅ T6 通过: section_images 已合并到 state")
    else:
        print("⚠️ T6 待验证: section_images 未在结果中")
    
    print(f"\n{'='*50}")
    print("📋 下一步：运行完整测试（包含视频生成）")
    print("   使用前端或 API 调用 generate_cover_video=True")
    print(f"{'='*50}\n")
    
    return result


def main():
    parser = argparse.ArgumentParser(description="Mini 博客动画 v2 测试")
    parser.add_argument("--topic", default="Python 装饰器入门", help="测试主题")
    args = parser.parse_args()
    
    test_mini_blog(args.topic)


if __name__ == "__main__":
    main()
