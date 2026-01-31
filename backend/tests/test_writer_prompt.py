#!/usr/bin/env python3
"""
测试 WriterAgent 的时间约束效果
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from services.blog_generator.agents.writer import WriterAgent
from services.llm_service import LLMService


def test_writer_agent():
    """使用 WriterAgent 测试时间约束效果"""
    
    # 从环境变量读取配置
    api_key = os.environ.get('OPENAI_API_KEY', '')
    api_base = os.environ.get('OPENAI_API_BASE', '')
    model = os.environ.get('LLM_TEXT_MODEL', 'qwen-plus')
    
    print(f"使用模型: {model}")
    print(f"API Base: {api_base}")
    
    llm = LLMService(
        provider_format='openai',
        openai_api_key=api_key,
        openai_api_base=api_base,
        text_model=model
    )
    
    # 创建 WriterAgent
    writer = WriterAgent(llm)
    
    # 模拟一个关于 2026 年新技术的章节大纲
    section_outline = {
        "id": "section_1",
        "title": "OpenClaw 简介",
        "key_points": [
            "OpenClaw 是什么",
            "OpenClaw 的核心特性",
            "OpenClaw 与传统方案的对比"
        ],
        "image_suggestions": [
            {"type": "architecture", "description": "OpenClaw 架构图"}
        ]
    }
    
    # 模拟 state
    state = {
        "topic": "OpenClaw: 基于 CLI 的 AI 代理框架",
        "article_type": "tutorial",
        "target_audience": "intermediate",
        "audience_adaptation": "default",
        "background_knowledge": "OpenClaw 是一个开源的 AI 代理框架，基于 CLI 工具组合实现可扩展的智能体。它回归 Unix 哲学，用命令行工具组合实现 AI 代理的可扩展性。",
        "outline": {
            "title": "OpenClaw: 基于 CLI 的 AI 代理框架入门",
            "sections": [section_outline]
        },
        "sections": []
    }
    
    print("=" * 60)
    print("正在调用 WriterAgent 生成内容...")
    print("=" * 60)
    
    # 调用 WriterAgent
    result = writer.run(state)
    
    # 获取生成的内容
    sections = result.get("sections", [])
    if not sections:
        print("❌ 未生成任何内容")
        return None
    
    content = sections[0].get("content", "")
    
    print("\n" + "=" * 60)
    print("WriterAgent 生成的内容:")
    print("=" * 60)
    print(content)
    
    # 检查是否存在时间幻觉
    print("\n" + "=" * 60)
    print("时间幻觉检查:")
    print("=" * 60)
    
    hallucination_keywords = [
        "2024年",
        "2024 年",
        "假设性",
        "尚未发布",
        "尚未正式",
        "免责声明",
        "并非官方",
        "假设性产品",
        "假设性设计"
    ]
    
    found_issues = []
    for keyword in hallucination_keywords:
        if keyword in content:
            found_issues.append(keyword)
    
    if found_issues:
        print(f"❌ 发现时间幻觉问题: {found_issues}")
    else:
        print("✅ 未发现明显的时间幻觉问题")
    
    return content


if __name__ == "__main__":
    test_writer_agent()
