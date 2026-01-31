#!/usr/bin/env python3
"""
Instructional Design 真实 LLM 调用测试脚本

测试内容：
- TC-01: ResearcherAgent 学习目标提取
- TC-02: PlannerAgent 信息架构设计
- TC-03: ReviewerAgent Verbatim 检查
"""
import sys
import os

# 获取 backend 目录路径
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from dotenv import load_dotenv
# 明确加载 backend/.env 文件
env_path = os.path.join(backend_dir, '.env')
load_dotenv(env_path)
print(f"📁 加载 .env 文件: {env_path}")

import json
from services.llm_service import LLMService
from services.blog_generator.agents.researcher import ResearcherAgent
from services.blog_generator.agents.planner import PlannerAgent
from services.blog_generator.agents.reviewer import ReviewerAgent
from services.blog_generator.schemas.state import create_initial_state
from services.blog_generator.services.smart_search_service import SmartSearchService


def get_llm_client():
    """获取 LLM 客户端"""
    return LLMService(
        provider_format='openai',
        openai_api_key=os.environ.get('OPENAI_API_KEY'),
        openai_api_base=os.environ.get('OPENAI_API_BASE'),
        text_model=os.environ.get('TEXT_MODEL', 'qwen3-235b-a22b')
    )


def test_researcher_llm():
    """TC-01: 测试 ResearcherAgent 学习目标提取（真实 LLM 调用）"""
    print("\n" + "=" * 60)
    print("TC-01: ResearcherAgent 学习目标提取（真实 LLM 调用）")
    print("=" * 60)
    
    llm = get_llm_client()
    researcher = ResearcherAgent(llm_client=llm, search_service=None)
    
    topic = "OpenClaw 本地 AI 助手入门"
    
    # 使用真实搜索到的 OpenClaw 内容
    search_results = [
        {
            "title": "OpenClaw 项目介绍",
            "source": "developer.aliyun.com",
            "content": """
OpenClaw（原 Clawdbot/Moltbot）是一个跑在你自己机器上的 AI 助手，可以对接几乎所有主流聊天工具。

核心数据：
- GitHub stars：超过 10 万
- 一周访问量：200 万
- 支持平台：WhatsApp、Telegram、Discord、Slack、Teams、飞书、钉钉、Twitch、Google Chat 等 20+ 平台

项目负责人表示："OpenClaw 这个名字拆开来看：Open（开源、开放）+ Claw（龙虾爪，致敬起源）。"

关键特性：数据全在你手里。不像那些云端 AI 助手，你的聊天记录、文件、API 密钥都存在自己的服务器上。
            """
        },
        {
            "title": "OpenClaw 技术架构",
            "source": "aipuzi.cn",
            "content": """
从技术本质看，OpenClaw 是一个模块化、插件驱动、多模态协同的 AI 代理框架（Agent Framework）。

技术架构：
1. 大脑：大语言模型（LLM）作为核心推理引擎
2. 感知层：操作系统 API、浏览器自动化、邮件客户端、日历服务
3. 执行层：代码编辑器（Codex/Cursor）、语音合成（ElevenLabs）、智能家居控制
4. 记忆层：持久化向量记忆（Persistent Memory）、跨会话上下文继承（24/7 Context Persistence）

核心组件：
- 本地向量数据库：sqlite-vec
- 心跳机制：Heartbeats
- 安全提醒：prompt injection 目前在整个行业都是未解决的问题
            """
        }
    ]
    
    print(f"\n🔍 主题: {topic}")
    print(f"📄 搜索结果数量: {len(search_results)}")
    
    # 调用 summarize 方法
    result = researcher.summarize(
        topic=topic,
        search_results=search_results,
        target_audience="intermediate",
        search_depth="medium"
    )
    
    print("\n📋 返回结果:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # 检查 instructional_analysis
    instructional_analysis = result.get("instructional_analysis", {})
    
    print("\n📚 Instructional Design 分析:")
    
    # 检查学习目标
    learning_objectives = instructional_analysis.get("learning_objectives", [])
    print(f"\n学习目标 ({len(learning_objectives)} 个):")
    for obj in learning_objectives:
        print(f"  - [{obj.get('type', 'unknown')}] {obj.get('objective', 'N/A')}")
    
    # 检查 Verbatim Data
    verbatim_data = instructional_analysis.get("verbatim_data", [])
    print(f"\nVerbatim Data ({len(verbatim_data)} 项):")
    for item in verbatim_data:
        print(f"  - [{item.get('type', 'unknown')}] {item.get('value', 'N/A')}")
        if item.get('source'):
            print(f"    来源: {item.get('source')}")
    
    # 检查内容类型
    content_type = instructional_analysis.get("content_type", "unknown")
    print(f"\n内容类型: {content_type}")
    
    # 检查受众分析
    audience = instructional_analysis.get("audience", {})
    if audience:
        print(f"\n受众分析:")
        print(f"  - 知识水平: {audience.get('knowledge_level', 'N/A')}")
        print(f"  - 阅读目的: {audience.get('reading_purpose', 'N/A')}")
        print(f"  - 期望收获: {audience.get('expected_outcome', 'N/A')}")
    
    # 验证
    print("\n" + "-" * 40)
    print("验证结果:")
    
    checks = [
        (len(learning_objectives) >= 1, f"学习目标数量 >= 1 (实际: {len(learning_objectives)})"),
        (len(verbatim_data) >= 1, f"Verbatim Data 数量 >= 1 (实际: {len(verbatim_data)})"),
    ]
    
    all_passed = True
    for passed, desc in checks:
        status = "✅" if passed else "❌"
        print(f"  {status} {desc}")
        if not passed:
            all_passed = False
    
    return all_passed, result


def test_planner_llm(researcher_result: dict):
    """TC-02: 测试 PlannerAgent 信息架构设计（真实 LLM 调用）"""
    print("\n" + "=" * 60)
    print("TC-02: PlannerAgent 信息架构设计（真实 LLM 调用）")
    print("=" * 60)
    
    llm = get_llm_client()
    planner = PlannerAgent(llm_client=llm)
    
    # 从 researcher 结果获取数据
    instructional_analysis = researcher_result.get("instructional_analysis", {})
    verbatim_data = instructional_analysis.get("verbatim_data", [])
    
    # 调用 generate_outline 方法
    outline = planner.generate_outline(
        topic="OpenClaw 本地 AI 助手入门",
        article_type="tutorial",
        target_audience="intermediate",
        target_length="short",
        background_knowledge=researcher_result.get("background_knowledge", ""),
        key_concepts=researcher_result.get("key_concepts", []),
        instructional_analysis=instructional_analysis,
        verbatim_data=verbatim_data
    )
    
    print("\n📋 大纲结果:")
    print(f"标题: {outline.get('title', 'N/A')}")
    print(f"章节数: {len(outline.get('sections', []))}")
    
    # 检查信息架构
    info_arch = outline.get("information_architecture", {})
    print(f"\n📐 信息架构:")
    print(f"  - 结构类型: {info_arch.get('structure_type', 'N/A')}")
    
    # 检查章节
    print(f"\n📑 章节详情:")
    for section in outline.get("sections", []):
        print(f"\n  [{section.get('id', 'N/A')}] {section.get('title', 'N/A')}")
        if section.get('learning_objective'):
            print(f"    学习目标: {section.get('learning_objective')}")
        if section.get('verbatim_data_refs'):
            print(f"    Verbatim 引用: {section.get('verbatim_data_refs')}")
        if section.get('cognitive_load'):
            print(f"    认知负荷: {section.get('cognitive_load')}")
    
    # 验证
    print("\n" + "-" * 40)
    print("验证结果:")
    
    checks = [
        (len(outline.get('sections', [])) >= 2, f"章节数 >= 2 (实际: {len(outline.get('sections', []))})"),
        (outline.get('title'), "有标题"),
        (info_arch.get('structure_type'), f"有信息架构类型 (实际: {info_arch.get('structure_type', 'N/A')})"),
    ]
    
    all_passed = True
    for passed, desc in checks:
        status = "✅" if passed else "❌"
        print(f"  {status} {desc}")
        if not passed:
            all_passed = False
    
    return all_passed, outline


def test_reviewer_llm(verbatim_data: list, learning_objectives: list):
    """TC-03: 测试 ReviewerAgent Verbatim 检查（真实 LLM 调用）"""
    print("\n" + "=" * 60)
    print("TC-03: ReviewerAgent Verbatim 检查（真实 LLM 调用）")
    print("=" * 60)
    
    llm = get_llm_client()
    reviewer = ReviewerAgent(llm_client=llm)
    
    # 根据 verbatim_data 构造故意包含违规的文档
    # 将精确数据改写为模糊表述（故意违规）
    document_with_errors = """
## OpenClaw 简介

OpenClaw 是一个很火的开源 AI 助手项目，GitHub 上有很多 star，访问量也很大。

项目作者说过，这个名字很有意义。

## 技术架构

OpenClaw 基于大语言模型技术，支持多种平台。
"""
    
    outline = {
        "title": "OpenClaw 本地 AI 助手入门",
        "sections": [
            {"id": "section_1", "title": "OpenClaw 简介"},
            {"id": "section_2", "title": "技术架构"}
        ]
    }
    
    print("\n📄 测试文档（故意包含 Verbatim 违规）:")
    print(document_with_errors)
    
    print("\n📋 Verbatim Data（应该原样保留）:")
    for item in verbatim_data:
        print(f"  - [{item.get('type')}] {item.get('value')}")
    
    # 调用 review 方法
    result = reviewer.review(
        document=document_with_errors,
        outline=outline,
        verbatim_data=verbatim_data,
        learning_objectives=learning_objectives
    )
    
    print("\n📊 审核结果:")
    print(f"  - 得分: {result.get('score', 'N/A')}")
    print(f"  - 通过: {result.get('approved', 'N/A')}")
    print(f"  - 摘要: {result.get('summary', 'N/A')}")
    
    issues = result.get("issues", [])
    print(f"\n⚠️ 问题列表 ({len(issues)} 个):")
    
    verbatim_violations = []
    for issue in issues:
        issue_type = issue.get('issue_type', 'unknown')
        severity = issue.get('severity', 'unknown')
        desc = issue.get('description', 'N/A')
        
        print(f"\n  [{severity}] {issue_type}")
        print(f"    描述: {desc}")
        if issue.get('suggestion'):
            print(f"    建议: {issue.get('suggestion')}")
        if issue.get('original_value'):
            print(f"    原始值: {issue.get('original_value')}")
        if issue.get('found_value'):
            print(f"    发现值: {issue.get('found_value')}")
        
        if issue_type == "verbatim_violation":
            verbatim_violations.append(issue)
    
    # 验证
    print("\n" + "-" * 40)
    print("验证结果:")
    
    checks = [
        (len(verbatim_violations) >= 1, f"检测到 verbatim_violation (实际: {len(verbatim_violations)} 个)"),
        (result.get('score', 100) < 100, f"得分 < 100 (实际: {result.get('score', 'N/A')})"),
    ]
    
    all_passed = True
    for passed, desc in checks:
        status = "✅" if passed else "❌"
        print(f"  {status} {desc}")
        if not passed:
            all_passed = False
    
    return all_passed


def main():
    """运行所有真实 LLM 测试"""
    print("\n" + "=" * 60)
    print("🚀 Instructional Design 真实 LLM 调用测试")
    print("=" * 60)
    
    # 检查环境变量
    if not os.environ.get('OPENAI_API_KEY'):
        print("\n❌ 错误: 未设置 OPENAI_API_KEY 环境变量")
        return 1
    
    text_model = os.environ.get('TEXT_MODEL', 'qwen3-235b-a22b')
    print(f"\n📡 LLM 配置:")
    print(f"  - API Base: {os.environ.get('OPENAI_API_BASE', 'default')}")
    print(f"  - Model: {text_model}")
    
    results = []
    
    # TC-01: Researcher
    try:
        passed, researcher_result = test_researcher_llm()
        results.append(("TC-01: ResearcherAgent", passed))
    except Exception as e:
        print(f"\n❌ TC-01 异常: {e}")
        results.append(("TC-01: ResearcherAgent", False))
        researcher_result = {"instructional_analysis": {}}
    
    # TC-02: Planner
    try:
        passed, outline = test_planner_llm(researcher_result)
        results.append(("TC-02: PlannerAgent", passed))
    except Exception as e:
        print(f"\n❌ TC-02 异常: {e}")
        results.append(("TC-02: PlannerAgent", False))
    
    # TC-03: Reviewer
    try:
        instructional_analysis = researcher_result.get("instructional_analysis", {})
        verbatim_data = instructional_analysis.get("verbatim_data", [])
        learning_objectives = instructional_analysis.get("learning_objectives", [])
        
        if not verbatim_data:
            print("\n⚠️ Researcher 未提取到 Verbatim Data，跳过 TC-03")
            results.append(("TC-03: ReviewerAgent", True))
        else:
            passed = test_reviewer_llm(verbatim_data, learning_objectives)
            results.append(("TC-03: ReviewerAgent", passed))
    except Exception as e:
        print(f"\n❌ TC-03 异常: {e}")
        results.append(("TC-03: ReviewerAgent", False))
    
    # 汇总
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {status}: {name}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 所有测试通过！")
    else:
        print("⚠️ 部分测试失败，请检查")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
