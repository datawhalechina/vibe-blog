"""
Coder Agent - 代码生成
"""

import json
import logging
import os
import re
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..prompts import get_prompt_manager

# 从环境变量读取并行配置，默认为 3
MAX_WORKERS = int(os.environ.get('BLOG_GENERATOR_MAX_WORKERS', '3'))

def _should_use_parallel():
    """判断是否应该使用并行执行。当开启追踪时禁用并行，避免上下文丢失。"""
    if os.environ.get('TRACE_ENABLED', 'false').lower() == 'true':
        return False
    return True

logger = logging.getLogger(__name__)

# Langfuse 追踪装饰器（只在 TRACE_ENABLED=true 时启用）
def _get_langfuse_client():
    """获取 Langfuse client，未启用时返回 None"""
    if os.environ.get('TRACE_ENABLED', 'false').lower() == 'true':
        try:
            from langfuse import get_client
            return get_client()
        except ImportError:
            pass
        except Exception:
            pass
    return None

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
langfuse_client = _get_langfuse_client()


class CoderAgent:
    """
    代码示例师 - 负责生成代码示例和输出
    """
    
    def __init__(self, llm_client):
        """
        初始化 Coder Agent
        
        Args:
            llm_client: LLM 客户端
        """
        self.llm = llm_client
    
    @observe(name="coder.generate_code", as_type="generation")
    def generate_code(
        self,
        code_description: str,
        context: str,
        language: str = "python",
        complexity: str = "medium",
        **kwargs  # 接收 langfuse_parent_trace_id 等参数
    ) -> Dict[str, Any]:
        """
        生成代码示例
        
        Args:
            code_description: 代码描述
            context: 所在章节上下文
            language: 编程语言
            complexity: 复杂度
            
        Returns:
            代码块字典
        """
        pm = get_prompt_manager()
        prompt = pm.render_coder(
            code_description=code_description,
            context=context,
            language=language,
            complexity=complexity
        )
        
        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response)
            return {
                "code": result.get("code_block", ""),
                "output": result.get("output_block", ""),
                "explanation": result.get("explanation", ""),
                "language": language
            }
            
        except Exception as e:
            logger.error(f"代码生成失败: {e}")
            raise
    
    def extract_code_placeholders(self, content: str) -> List[Dict[str, str]]:
        """
        从内容中提取代码占位符
        
        Args:
            content: 章节内容
            
        Returns:
            代码占位符列表
        """
        # 匹配 [CODE: code_id - description] 格式
        pattern = r'\[CODE:\s*(\w+)\s*-\s*([^\]]+)\]'
        matches = re.findall(pattern, content)
        
        placeholders = []
        for code_id, description in matches:
            placeholders.append({
                "id": code_id,
                "description": description.strip()
            })
        
        return placeholders
    
    @observe(name="coder.run")
    def run(self, state: Dict[str, Any], max_workers: int = None) -> Dict[str, Any]:
        """
        执行代码生成（并行）
        
        Args:
            state: 共享状态
            max_workers: 最大并行数
            
        Returns:
            更新后的状态
        """
        if state.get('error'):
            logger.error(f"前置步骤失败，跳过代码生成: {state.get('error')}")
            state['code_blocks'] = []
            return state
        
        sections = state.get('sections', [])
        if not sections:
            logger.warning("没有章节内容，跳过代码生成")
            state['code_blocks'] = []
            return state
        
        logger.info("开始生成代码示例")
        
        # 第一步：收集所有代码生成任务，预先分配顺序索引
        tasks = []
        for section_idx, section in enumerate(sections):
            content = section.get('content', '')
            section_title = section.get('title', '')
            
            placeholders = self.extract_code_placeholders(content)
            
            for placeholder in placeholders:
                tasks.append({
                    'order_idx': len(tasks),  # 保持原始顺序
                    'section_idx': section_idx,
                    'section_title': section_title,
                    'placeholder': placeholder
                })
        
        if not tasks:
            logger.info("没有代码占位符，跳过代码生成")
            state['code_blocks'] = []
            return state
        
        # 使用环境变量配置或传入的参数
        if max_workers is None:
            max_workers = MAX_WORKERS
        
        use_parallel = _should_use_parallel()
        if use_parallel:
            logger.info(f"共 {len(tasks)} 个代码块需要生成，使用 {min(max_workers, len(tasks))} 个并行线程")
        else:
            logger.info(f"共 {len(tasks)} 个代码块需要生成，使用串行模式（追踪已启用）")
        
        # 第二步：生成代码
        results = [None] * len(tasks)  # 预分配结果数组，保证顺序
        
        def generate_single_task(task):
            """单个代码生成任务"""
            try:
                code = self.generate_code(
                    code_description=task['placeholder']['description'],
                    context=f"章节: {task['section_title']}",
                    language="python",
                    complexity="medium"
                )
                return {
                    'success': True,
                    'order_idx': task['order_idx'],
                    'section_idx': task['section_idx'],
                    'code_block': {
                        "id": task['placeholder']['id'],
                        "code": code.get('code', ''),
                        "output": code.get('output', ''),
                        "explanation": code.get('explanation', ''),
                        "language": code.get('language', 'python')
                    }
                }
            except Exception as e:
                logger.error(f"代码生成失败 [{task['placeholder']['id']}]: {e}")
                return {
                    'success': False,
                    'order_idx': task['order_idx'],
                    'section_idx': task['section_idx'],
                    'placeholder_id': task['placeholder']['id'],
                    'error': str(e)
                }
        
        if use_parallel:
            # 并行执行
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(generate_single_task, task): task for task in tasks}
                
                for future in as_completed(futures):
                    result = future.result()
                    order_idx = result['order_idx']
                    results[order_idx] = result
                    
                    if result['success']:
                        logger.info(f"代码生成完成: {result['code_block']['id']}")
        else:
            # 串行执行（追踪模式）- 直接调用方法以保持 Langfuse 上下文
            for task in tasks:
                try:
                    code = self.generate_code(
                        code_description=task['placeholder']['description'],
                        context=f"章节: {task['section_title']}",
                        language="python",
                        complexity="medium"
                    )
                    results[task['order_idx']] = {
                        'success': True,
                        'order_idx': task['order_idx'],
                        'section_idx': task['section_idx'],
                        'code_block': {
                            "id": task['placeholder']['id'],
                            "code": code.get('code', ''),
                            "output": code.get('output', ''),
                            "explanation": code.get('explanation', ''),
                            "language": code.get('language', 'python')
                        }
                    }
                    logger.info(f"代码生成完成: {task['placeholder']['id']}")
                except Exception as e:
                    logger.error(f"代码生成失败 [{task['placeholder']['id']}]: {e}")
                    results[task['order_idx']] = {
                        'success': False,
                        'order_idx': task['order_idx'],
                        'section_idx': task['section_idx'],
                        'placeholder_id': task['placeholder']['id'],
                        'error': str(e)
                    }
        
        # 第三步：按原始顺序组装结果，更新章节关联
        code_blocks = []
        section_code_ids = {i: [] for i in range(len(sections))}  # 每个章节的 code_ids
        
        for result in results:
            if result and result['success']:
                code_blocks.append(result['code_block'])
                section_code_ids[result['section_idx']].append(result['code_block']['id'])
        
        # 更新章节的 code_ids
        for section_idx, code_ids in section_code_ids.items():
            if code_ids:
                if 'code_ids' not in sections[section_idx]:
                    sections[section_idx]['code_ids'] = []
                sections[section_idx]['code_ids'].extend(code_ids)
        
        state['code_blocks'] = code_blocks
        logger.info(f"代码生成完成: {len(code_blocks)} 个代码块")
        
        return state
