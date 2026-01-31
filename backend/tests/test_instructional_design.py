#!/usr/bin/env python3
"""
Instructional Design 增强功能测试脚本

测试内容：
- TC-01: 学习目标提取
- TC-02: Verbatim Data 保留
- TC-03: 信息架构设计
- TC-04: Reviewer 检查
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import json
from services.blog_generator.prompts.prompt_manager import get_prompt_manager
from services.blog_generator.schemas.state import create_initial_state


def test_researcher_template():
    """测试 researcher.j2 模板是否包含 Instructional Design 分析"""
    print("=" * 60)
    print("测试 1: researcher.j2 模板")
    print("=" * 60)
    
    pm = get_prompt_manager()
    prompt = pm.render_researcher(
        topic="Redis 缓存最佳实践",
        search_depth="medium",
        target_audience="intermediate",
        search_results=[
            {"title": "Redis 官方文档", "source": "redis.io", "content": "Redis 读取性能：110,000 QPS"}
        ]
    )
    
    # 检查关键内容
    checks = [
        ("Instructional Design 分析" in prompt, "包含 Instructional Design 分析部分"),
        ("学习目标提取" in prompt, "包含学习目标提取"),
        ("Verbatim" in prompt or "原样保留" in prompt, "包含 Verbatim Data 说明"),
        ("instructional_analysis" in prompt, "输出格式包含 instructional_analysis"),
    ]
    
    all_passed = True
    for passed, desc in checks:
        status = "✅" if passed else "❌"
        print(f"  {status} {desc}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n✅ researcher.j2 模板测试通过")
    else:
        print("\n❌ researcher.j2 模板测试失败")
    
    return all_passed


def test_planner_template():
    """测试 planner.j2 模板是否包含 Instructional Design 规划"""
    print("\n" + "=" * 60)
    print("测试 2: planner.j2 模板")
    print("=" * 60)
    
    pm = get_prompt_manager()
    
    # 模拟 instructional_analysis
    instructional_analysis = {
        "learning_objectives": [
            {"type": "primary", "objective": "理解 Redis 缓存原理"},
            {"type": "secondary", "objective": "学会配置缓存策略"}
        ],
        "content_type": "tutorial",
        "audience": {
            "knowledge_level": "intermediate"
        }
    }
    
    # 模拟 verbatim_data
    verbatim_data = [
        {"type": "statistic", "value": "110,000 QPS", "context": "读取性能", "source": "Redis 官方"},
        {"type": "quote", "value": "Redis is not just a cache", "source": "Antirez"}
    ]
    
    prompt = pm.render_planner(
        topic="Redis 缓存最佳实践",
        article_type="tutorial",
        target_audience="intermediate",
        target_length="medium",
        background_knowledge="Redis 是一个高性能的内存数据库",
        key_concepts=["缓存", "TTL", "淘汰策略"],
        instructional_analysis=instructional_analysis,
        verbatim_data=verbatim_data
    )
    
    # 检查关键内容
    checks = [
        ("Instructional Design 规划" in prompt, "包含 Instructional Design 规划部分"),
        ("信息架构设计" in prompt, "包含信息架构设计"),
        ("110,000 QPS" in prompt, "包含 Verbatim 数据"),
        ("information_architecture" in prompt, "输出格式包含 information_architecture"),
        ("verbatim_data_refs" in prompt, "章节输出包含 verbatim_data_refs"),
    ]
    
    all_passed = True
    for passed, desc in checks:
        status = "✅" if passed else "❌"
        print(f"  {status} {desc}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n✅ planner.j2 模板测试通过")
    else:
        print("\n❌ planner.j2 模板测试失败")
    
    return all_passed


def test_reviewer_template():
    """测试 reviewer.j2 模板是否包含 Verbatim 检查"""
    print("\n" + "=" * 60)
    print("测试 3: reviewer.j2 模板")
    print("=" * 60)
    
    pm = get_prompt_manager()
    
    # 模拟 verbatim_data
    verbatim_data = [
        {"type": "statistic", "value": "110,000 QPS", "context": "读取性能", "source": "Redis 官方"},
    ]
    
    # 模拟 learning_objectives
    learning_objectives = [
        {"type": "primary", "objective": "理解 Redis 缓存原理"},
    ]
    
    prompt = pm.render_reviewer(
        document="## Redis 性能\n\nRedis 性能很好，可以达到约 10 万 QPS。",
        outline={"title": "Redis 缓存", "sections": []},
        verbatim_data=verbatim_data,
        learning_objectives=learning_objectives
    )
    
    # 检查关键内容
    checks = [
        ("Verbatim Data 完整性检查" in prompt, "包含 Verbatim Data 检查部分"),
        ("110,000 QPS" in prompt, "包含具体的 Verbatim 数据"),
        ("verbatim_violation" in prompt, "包含 verbatim_violation issue_type"),
        ("学习目标覆盖度检查" in prompt, "包含学习目标检查部分"),
        ("learning_objective_gap" in prompt, "包含 learning_objective_gap issue_type"),
    ]
    
    all_passed = True
    for passed, desc in checks:
        status = "✅" if passed else "❌"
        print(f"  {status} {desc}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n✅ reviewer.j2 模板测试通过")
    else:
        print("\n❌ reviewer.j2 模板测试失败")
    
    return all_passed


def test_shared_state():
    """测试 SharedState 是否包含新字段"""
    print("\n" + "=" * 60)
    print("测试 4: SharedState 扩展")
    print("=" * 60)
    
    state = create_initial_state(
        topic="Redis 缓存最佳实践",
        article_type="tutorial",
        target_audience="intermediate"
    )
    
    # 检查新字段
    checks = [
        ("instructional_analysis" in state, "包含 instructional_analysis 字段"),
        ("learning_objectives" in state, "包含 learning_objectives 字段"),
        ("verbatim_data" in state, "包含 verbatim_data 字段"),
        ("information_architecture" in state, "包含 information_architecture 字段"),
        (state.get("instructional_analysis") is None, "instructional_analysis 初始为 None"),
        (state.get("learning_objectives") == [], "learning_objectives 初始为空列表"),
        (state.get("verbatim_data") == [], "verbatim_data 初始为空列表"),
    ]
    
    all_passed = True
    for passed, desc in checks:
        status = "✅" if passed else "❌"
        print(f"  {status} {desc}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n✅ SharedState 测试通过")
    else:
        print("\n❌ SharedState 测试失败")
    
    return all_passed


def test_data_models():
    """测试新增的数据模型"""
    print("\n" + "=" * 60)
    print("测试 5: 数据模型")
    print("=" * 60)
    
    from services.blog_generator.schemas.state import (
        LearningObjective,
        AudienceAnalysis,
        VerbatimDataItem,
        InstructionalAnalysis,
        InformationArchitecture,
        ReviewIssue
    )
    
    checks = []
    
    # 测试 LearningObjective
    try:
        obj = LearningObjective(type="primary", objective="理解 Redis 缓存原理")
        checks.append((True, "LearningObjective 模型正常"))
    except Exception as e:
        checks.append((False, f"LearningObjective 模型失败: {e}"))
    
    # 测试 VerbatimDataItem
    try:
        item = VerbatimDataItem(type="statistic", value="110,000 QPS", source="Redis 官方")
        checks.append((True, "VerbatimDataItem 模型正常"))
    except Exception as e:
        checks.append((False, f"VerbatimDataItem 模型失败: {e}"))
    
    # 测试 InstructionalAnalysis
    try:
        analysis = InstructionalAnalysis(
            learning_objectives=[obj],
            content_type="tutorial"
        )
        checks.append((True, "InstructionalAnalysis 模型正常"))
    except Exception as e:
        checks.append((False, f"InstructionalAnalysis 模型失败: {e}"))
    
    # 测试 ReviewIssue 新增的 issue_type
    try:
        issue = ReviewIssue(
            section_id="section_1",
            issue_type="verbatim_violation",
            severity="high",
            description="统计数据被改写",
            suggestion="恢复原始数据",
            original_value="110,000 QPS",
            found_value="约 10 万 QPS"
        )
        checks.append((True, "ReviewIssue verbatim_violation 类型正常"))
    except Exception as e:
        checks.append((False, f"ReviewIssue 模型失败: {e}"))
    
    all_passed = True
    for passed, desc in checks:
        status = "✅" if passed else "❌"
        print(f"  {status} {desc}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n✅ 数据模型测试通过")
    else:
        print("\n❌ 数据模型测试失败")
    
    return all_passed


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("Instructional Design 增强功能测试")
    print("=" * 60 + "\n")
    
    results = []
    
    results.append(("researcher.j2 模板", test_researcher_template()))
    results.append(("planner.j2 模板", test_planner_template()))
    results.append(("reviewer.j2 模板", test_reviewer_template()))
    results.append(("SharedState 扩展", test_shared_state()))
    results.append(("数据模型", test_data_models()))
    
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
