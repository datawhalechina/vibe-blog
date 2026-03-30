"""
TOC 优化验证脚本 - 完整 pipeline 测试
"""
import os
import logging


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from dotenv import load_dotenv
load_dotenv()


def test_full_pipeline():
    from services.llm_service import init_llm_service
    from services.blog_generator.blog_service import init_blog_service, get_blog_service
    from services.blog_generator.services.search_service import init_search_service
    from services.image_service import init_image_service

    config = {
        'AI_PROVIDER_FORMAT': os.getenv('AI_PROVIDER_FORMAT', 'openai'),
        'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY', ''),
        'OPENAI_API_BASE': os.getenv('OPENAI_API_BASE', ''),
        'TEXT_MODEL': 'qwen-max',  # 使用 qwen-max 避免 qwen3-max 的 token 限制
        'NANO_BANANA_API_KEY': os.getenv('NANO_BANANA_API_KEY', ''),
        'NANO_BANANA_API_BASE': os.getenv('NANO_BANANA_API_BASE', ''),
        'NANO_BANANA_MODEL': os.getenv('NANO_BANANA_MODEL', 'nano-banana-pro'),
        'ZAI_SEARCH_API_KEY': os.getenv('ZAI_SEARCH_API_KEY', ''),
        'ZAI_SEARCH_API_BASE': os.getenv('ZAI_SEARCH_API_BASE', ''),
    }

    llm = init_llm_service(config)
    init_image_service(config)
    search_service = init_search_service(config)
    init_blog_service(llm, search_service=search_service)
    blog_service = get_blog_service()

    print("\n" + "=" * 60)
    print("  TOC 优化验证 - 完整 Pipeline 测试")
    print("=" * 60)

    result = blog_service.generate_sync(
        topic="Redis 快速入门",
        article_type="tutorial",
        target_audience="beginner",
        target_length="mini"
    )

    if not result or not result.get('markdown'):
        print("\n❌ 生成失败")
        return

    markdown = result['markdown']

    # 提取目录部分
    print("\n=== 生成的目录 ===\n")
    in_toc = False
    toc_lines = []
    for line in markdown.split('\n'):
        if line.strip() == '## 目录':
            in_toc = True
            continue
        if in_toc:
            if line.strip().startswith('---') or (line.strip().startswith('##') and '目录' not in line):
                break
            if line.strip():
                toc_lines.append(line)
                print(line)

    # 验证
    print("\n=== 验证结果 ===\n")

    has_numbered_sections = any('一、' in l or '二、' in l or '三、' in l for l in toc_lines)
    has_subsections = any(l.strip().startswith('- [') and ('1.' in l or '2.' in l or '3.' in l) for l in toc_lines)
    has_nesting = any(l.startswith('    ') for l in toc_lines)

    print(f"  {'✅' if has_numbered_sections else '❌'} 主章节使用中文编号（一、二、三...）")
    print(f"  {'✅' if has_subsections else '❌'} 子标题使用数字编号（1.1, 2.1...）")
    print(f"  {'✅' if has_nesting else '❌'} 目录有多级嵌套")
    print(f"  📊 目录行数: {len(toc_lines)}")
    print(f"  📊 文章总字数: {len(markdown)}")

    # 保存文件
    from pathlib import Path
    from datetime import datetime
    output_dir = Path(__file__).parent.parent / 'outputs'
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filepath = output_dir / f"TOC_TEST_Redis快速入门_{timestamp}.md"
    filepath.write_text(markdown, encoding='utf-8')
    print(f"\n  📄 文章已保存: {filepath}")


if __name__ == "__main__":
    test_full_pipeline()
