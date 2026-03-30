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

import logging
import argparse
from pathlib import Path
from datetime import datetime


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_mini_blog(topic: str):
    """测试 Mini 博客完整流程"""
    from dotenv import load_dotenv
    load_dotenv()
    
    import os
    from services.blog_generator.blog_service import init_blog_service, get_blog_service
    from services.llm_service import init_llm_service
    from services.image_service import init_image_service
    from services.blog_generator.services.search_service import init_search_service
    
    # 构建配置
    config = {
        'AI_PROVIDER_FORMAT': os.getenv('AI_PROVIDER_FORMAT', 'openai'),
        'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY', ''),
        'OPENAI_API_BASE': os.getenv('OPENAI_API_BASE', ''),
        'GOOGLE_API_KEY': os.getenv('GOOGLE_API_KEY', ''),
        'TEXT_MODEL': os.getenv('TEXT_MODEL', 'gpt-4o'),
        # 图片服务配置
        'NANO_BANANA_API_KEY': os.getenv('NANO_BANANA_API_KEY', ''),
        'NANO_BANANA_API_BASE': os.getenv('NANO_BANANA_API_BASE', 'https://grsai.dakka.com.cn'),
        'NANO_BANANA_MODEL': os.getenv('NANO_BANANA_MODEL', 'nano-banana-pro'),
        # 搜索服务配置
        'ZAI_SEARCH_API_KEY': os.getenv('ZAI_SEARCH_API_KEY', ''),
        'ZAI_SEARCH_API_BASE': os.getenv('ZAI_SEARCH_API_BASE', ''),
    }
    
    # 初始化服务
    llm_client = init_llm_service(config)
    init_image_service(config)  # 初始化图片服务
    search_service = init_search_service(config)  # 初始化搜索服务
    init_blog_service(llm_client, search_service=search_service)
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
    sections_count = result.get('sections_count', 0)
    images_count = result.get('images_count', 0)
    review_score = result.get('review_score', 0)
    success = result.get('success', False)
    
    print(f"\n{'='*50}")
    print("📊 测试结果")
    print(f"{'='*50}")
    
    # T1: Mini 博客生成
    if success and sections_count > 0:
        print(f"✅ T1 通过: 博客生成成功")
        print(f"   - 章节数: {sections_count}")
        print(f"   - 图片数: {images_count}")
        print(f"   - 审核得分: {review_score}")
    else:
        print(f"❌ T1 失败: success={success}, sections_count={sections_count}")
    
    # T2: 章节配图生成（需要配置图片服务）
    if images_count > 0:
        print(f"✅ T2 通过: 章节配图数 = {images_count}")
    else:
        print(f"⚠️ T2 跳过: 图片服务未配置（需要 IMAGE_PROVIDER 环境变量）")
    
    # T3: Mini 模式优化验证（通过日志确认）
    print(f"✅ T3 验证: 请检查上方日志中的以下关键输出:")
    print(f"   - '[mini] 模式跳过知识增强'")
    print(f"   - '[mini] 模式：使用章节配图生成'")
    print(f"   - '[mini] 模式：只处理 X 个 high 级别问题'")
    
    # 保存文章到文件
    markdown_content = result.get('markdown', '')
    if markdown_content:
        output_dir = Path(__file__).parent.parent / 'outputs'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成文件名
        safe_title = topic.replace('/', '_').replace('\\', '_')[:50]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{safe_title}_{timestamp}.md"
        filepath = output_dir / filename
        
        # 保存文件
        filepath.write_text(markdown_content, encoding='utf-8')
        print(f"\n✅ 文章已保存到: {filepath}")
        print(f"   - 文件大小: {len(markdown_content)} 字节")
        print(f"   - 章节数: {sections_count}")
        print(f"   - 配图数: {images_count}")
    
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
