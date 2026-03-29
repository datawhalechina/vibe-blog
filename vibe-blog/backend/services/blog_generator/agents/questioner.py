"""
Questioner Agent - 追问深化
"""

import json
import logging
import os
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..prompts import get_prompt_manager

# 从环境变量读取并行配置，默认为 3
MAX_WORKERS = int(os.environ.get('BLOG_GENERATOR_MAX_WORKERS', '3'))

def _should_use_parallel(mode: str = None):
    """判断是否应该使用并行执行。mini 模式强制并行，其他模式受 TRACE_ENABLED 控制。"""
    if mode == 'mini':
        return True
    if os.environ.get('TRACE_ENABLED', 'false').lower() == 'true':
        return False
    return True

logger = logging.getLogger(__name__)

def _get_observe_decorator():
    """获取 Langfuse observe 装饰器，未启用时返回空装饰器"""
    if os.environ.get('TRACE_ENABLED', 'false').lower() == 'true':
        try:
            from langfuse import observe
            return observe
        except ImportError:
            pass
    # 返回空装饰器
    def noop_decorator(*args, **kwargs):
        def wrapper(func):
            return func
        return wrapper if not args or not callable(args[0]) else func
    return noop_decorator

observe = _get_observe_decorator()


class QuestionerAgent:
    """
    追问师 - 负责发现内容模糊点并提出深化问题
    """
    
    def __init__(self, llm_client):
        """
        初始化 Questioner Agent
        
        Args:
            llm_client: LLM 客户端
        """
        self.llm = llm_client
    
    @observe(name="questioner.check_depth", as_type="generation")
    def check_depth(
        self,
        section_content: str,
        section_outline: Dict[str, Any],
        depth_requirement: str = "medium",
        **kwargs  # 接收 langfuse_parent_trace_id 等参数
    ) -> Dict[str, Any]:
        """
        检查章节内容深度
        
        Args:
            section_content: 章节内容
            section_outline: 章节大纲
            depth_requirement: 深度要求
            
        Returns:
            检查结果
        """
        pm = get_prompt_manager()
        prompt = pm.render_questioner(
            section_content=section_content,
            section_outline=section_outline,
            depth_requirement=depth_requirement
        )
        
        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                caller="questioner",
            )

            if not response or not response.strip():
                logger.warning(f"深度检查返回空响应，默认通过")
                return {
                    "is_detailed_enough": True,
                    "depth_score": 80,
                    "vague_points": []
                }
            
            result = json.loads(response)
            return {
                "is_detailed_enough": result.get("is_detailed_enough", True),
                "depth_score": result.get("depth_score", 80),
                "vague_points": result.get("vague_points", [])
            }
            
        except json.JSONDecodeError as e:
            logger.warning(f"深度检查 JSON 解析失败: {e}，响应内容: {response[:200] if response else '空'}，默认通过")
            return {
                "is_detailed_enough": True,
                "depth_score": 80,
                "vague_points": []
            }
        except Exception as e:
            logger.error(f"深度检查失败: {e}")
            # 默认通过
            return {
                "is_detailed_enough": True,
                "depth_score": 80,
                "vague_points": []
            }

    @observe(name="questioner.evaluate_section", as_type="generation")
    def evaluate_section(
        self,
        section_content: str,
        section_title: str = "",
        prev_summary: str = "",
        next_preview: str = "",
        **kwargs
    ) -> Dict[str, Any]:
        """
        多维度段落评估（Generator-Critic Loop 的 Critic 角色）

        对章节内容进行 4 维度评估：信息密度、逻辑连贯、专业深度、表达质量。
        输出结构化 JSON 包含分数、具体问题和可执行的改进建议。

        Args:
            section_content: 章节内容
            section_title: 章节标题
            prev_summary: 上一章节摘要（用于评估衔接）
            next_preview: 下一章节预览（用于评估衔接）

        Returns:
            评估结果字典
        """
        pm = get_prompt_manager()
        prompt = pm.render_section_evaluator(
            section_content=section_content,
            section_title=section_title,
            prev_summary=prev_summary,
            next_preview=next_preview,
        )

        default_result = {
            "scores": {
                "information_density": 7,
                "logical_coherence": 7,
                "professional_depth": 7,
                "expression_quality": 7,
            },
            "overall_quality": 7.0,
            "specific_issues": [],
            "improvement_suggestions": [],
        }

        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                caller="questioner",
            )

            if not response or not response.strip():
                logger.warning("段落评估返回空响应，使用默认分数")
                return default_result

            result = json.loads(response)
            scores = result.get("scores", default_result["scores"])
            # 计算 overall_quality（如果 LLM 没返回）
            score_values = [v for v in scores.values() if isinstance(v, (int, float))]
            overall = result.get(
                "overall_quality",
                round(sum(score_values) / max(len(score_values), 1), 1),
            )

            eval_result = {
                "scores": scores,
                "overall_quality": overall,
                "specific_issues": result.get("specific_issues", []),
                "improvement_suggestions": result.get("improvement_suggestions", []),
            }

            return eval_result

        except json.JSONDecodeError as e:
            logger.warning(f"段落评估 JSON 解析失败: {e}")
            return default_result
        except Exception as e:
            logger.error(f"段落评估失败: {e}")
            return default_result

    @observe(name="questioner.run")
    def run(self, state: Dict[str, Any], max_workers: int = None) -> Dict[str, Any]:
        """
        执行追问检查（并行）
        
        Args:
            state: 共享状态
            max_workers: 最大并行数
            
        Returns:
            更新后的状态
        """
        if state.get('error'):
            logger.error(f"前置步骤失败，跳过追问检查: {state.get('error')}")
            return state
        
        sections = state.get('sections', [])
        if not sections:
            logger.warning("没有章节内容，跳过追问检查")
            state['question_results'] = []
            state['all_sections_detailed'] = True
            return state
        
        outline = state.get('outline', {})
        sections_outline = outline.get('sections', [])
        
        # 根据 StyleProfile 或 target_length 确定深度要求
        from ..style_profile import StyleProfile
        target_length = state.get('target_length', 'medium')
        style = StyleProfile.from_target_length(target_length)
        depth_requirement = style.depth_requirement
        
        # 使用环境变量配置或传入的参数
        if max_workers is None:
            max_workers = MAX_WORKERS
        
        use_parallel = _should_use_parallel(mode=target_length)
        if use_parallel and max_workers < 3:
            max_workers = 3  # mini 模式强制并行时，确保至少 3 个线程
        if use_parallel:
            logger.info(f"开始追问检查 (深度要求: {depth_requirement})，{len(sections)} 个章节，使用 {min(max_workers, len(sections))} 个并行线程")
        else:
            logger.info(f"开始追问检查 (深度要求: {depth_requirement})，{len(sections)} 个章节，使用串行模式（追踪已启用）")
        
        # 准备任务列表
        tasks = []
        for i, section in enumerate(sections):
            section_outline = sections_outline[i] if i < len(sections_outline) else {}
            tasks.append({
                'order_idx': i,
                'section': section,
                'section_outline': section_outline,
                'depth_requirement': depth_requirement
            })
        
        # 执行检查
        results = [None] * len(tasks)
        
        def check_single_task(task):
            """单个章节检查任务"""
            try:
                result = self.check_depth(
                    section_content=task['section'].get('content', ''),
                    section_outline=task['section_outline'],
                    depth_requirement=task['depth_requirement']
                )
                return {
                    'success': True,
                    'order_idx': task['order_idx'],
                    'section': task['section'],
                    'result': result
                }
            except Exception as e:
                logger.error(f"章节检查失败 [{task['section'].get('title', '')}]: {e}")
                return {
                    'success': False,
                    'order_idx': task['order_idx'],
                    'section': task['section'],
                    'result': {
                        'is_detailed_enough': True,
                        'depth_score': 80,
                        'vague_points': []
                    }
                }
        
        if use_parallel:
            # 并行执行
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(check_single_task, task): task for task in tasks}
                
                for future in as_completed(futures):
                    result = future.result()
                    order_idx = result['order_idx']
                    results[order_idx] = result
        else:
            # 串行执行（追踪模式）- 直接调用方法以保持 Langfuse 上下文
            for task in tasks:
                try:
                    check_result = self.check_depth(
                        section_content=task['section'].get('content', ''),
                        section_outline=task['section_outline'],
                        depth_requirement=task['depth_requirement']
                    )
                    results[task['order_idx']] = {
                        'success': True,
                        'order_idx': task['order_idx'],
                        'section': task['section'],
                        'result': check_result
                    }
                except Exception as e:
                    logger.error(f"章节检查失败 [{task['section'].get('title', '')}]: {e}")
                    results[task['order_idx']] = {
                        'success': False,
                        'order_idx': task['order_idx'],
                        'section': task['section'],
                        'result': {
                            'is_detailed_enough': True,
                            'depth_score': 80,
                            'vague_points': []
                        }
                    }
        
        # 组装结果
        question_results = []
        all_detailed = True
        
        for result in results:
            if result:
                check_result = result['result']
                section = result['section']
                
                question_result = {
                    "section_id": section.get('id', f'section_{result["order_idx"]+1}'),
                    "is_detailed_enough": check_result.get('is_detailed_enough', True),
                    "depth_score": check_result.get('depth_score', 80),
                    "vague_points": check_result.get('vague_points', [])
                }
                question_results.append(question_result)
                
                if not check_result.get('is_detailed_enough', True):
                    all_detailed = False
                    logger.info(f"章节需要深化: {section.get('title', '')} (得分: {check_result.get('depth_score', 0)})")
        
        state['question_results'] = question_results
        state['all_sections_detailed'] = all_detailed
        
        logger.info(f"追问检查完成: {'全部通过' if all_detailed else '需要深化'}")
        
        return state
