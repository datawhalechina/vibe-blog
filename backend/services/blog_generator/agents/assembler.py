"""
Assembler Agent - 文档组装
"""

import logging
import re
from typing import Dict, Any, List

from ..prompts import get_prompt_manager
from ..utils.helpers import (
    replace_placeholders,
    estimate_reading_time
)

logger = logging.getLogger(__name__)


def _fix_markdown_separators(text: str) -> str:
    """
    修复 Markdown 分隔线 (---) 的格式问题：
    1. 确保 --- 前后都有空行，避免 Setext 标题解析（文本紧挨 --- 会被渲染为加粗标题）
    2. 确保 --- 和 ## 标题之间有空行，避免 ---## 连写
    3. 跳过代码块内部的 ---，避免破坏 ASCII 拓扑图等内容
    """
    lines = text.split('\n')
    result = []
    in_code_block = False

    for line in lines:
        stripped = line.strip()
        # 跟踪代码块边界
        if stripped.startswith('```'):
            in_code_block = not in_code_block
            result.append(line)
            continue

        if not in_code_block:
            # 情况1: 独立的 --- 行
            if stripped == '---':
                if result and result[-1].strip() != '':
                    result.append('')
                result.append('---')
                result.append('')
            # 情况2: ---## 连写（--- 紧跟标题或其他内容）
            elif stripped.startswith('---') and len(stripped) > 3 and stripped[3] != '-':
                separator = '---'
                rest = stripped[3:].lstrip()
                if result and result[-1].strip() != '':
                    result.append('')
                result.append(separator)
                result.append('')
                result.append(rest)
            else:
                result.append(line)
        else:
            result.append(line)

    text = '\n'.join(result)
    # 清理可能产生的多余空行（超过2个连续空行压缩为2个）
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text


class AssemblerAgent:
    """
    文档组装师 - 负责最终文档组装
    """
    
    def __init__(self):
        """
        初始化 Assembler Agent
        """
        pass
    
    def extract_subheadings(self, content: str) -> List[Dict[str, Any]]:
        """
        从章节内容中提取多级子标题（### 和 #### 标题）

        Args:
            content: 章节内容

        Returns:
            子标题列表，每项包含 title 和 level，以及可选的 children
            示例: [
                {"title": "1.1 安装", "level": 3, "children": [
                    {"title": "1.1.1 环境准备", "level": 4}
                ]},
                {"title": "1.2 配置", "level": 3, "children": []}
            ]
        """
        # 匹配 ### 和 #### 标题
        pattern = r'^(#{3,4})\s+(.+?)$'
        matches = re.findall(pattern, content, re.MULTILINE)

        result = []
        for hashes, title in matches:
            level = len(hashes)
            if level == 3:
                result.append({"title": title.strip(), "level": 3, "children": []})
            elif level == 4 and result:
                # 挂到最近的 ### 下面
                result[-1]["children"].append({"title": title.strip(), "level": 4})

        return result

    def replace_source_references(self, content: str, search_results: List[Dict]) -> str:
        """
        Replace {source_NNN} placeholders with actual source links.

        Args:
            content: Markdown content with {source_NNN} placeholders
            search_results: List of search results (1-indexed in placeholders)

        Returns:
            Content with placeholders replaced by markdown links
        """
        if not search_results:
            return content

        def replace_match(match):
            idx = int(match.group(1))
            if 0 < idx <= len(search_results):
                source = search_results[idx - 1]
                title = source.get('title', '来源')
                url = source.get('source', source.get('url', ''))
                if url:
                    return f"（[{title}]({url})）"
                return f"（{title}）"
            return match.group(0)  # Keep original if index out of range

        return re.sub(r'\{source_(\d{1,3})\}', replace_match, content)
    
    def assemble(
        self,
        outline: Dict[str, Any],
        sections: List[Dict[str, Any]],
        code_blocks: List[Dict[str, Any]],
        images: List[Dict[str, Any]],
        document_references: List[Dict[str, Any]] = None,
        search_results: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        组装最终文档
        
        Args:
            outline: 大纲
            sections: 章节内容列表
            code_blocks: 代码块列表
            images: 图片资源列表
            document_references: 文档来源引用列表
            
        Returns:
            组装结果
        """
        pm = get_prompt_manager()
        
        # 1. 从章节内容中提取多级子标题，构建目录数据
        toc_sections = []
        for section in sections:
            section_title = section.get('title', '')
            content = section.get('content', '')
            subheadings = self.extract_subheadings(content)
            toc_sections.append({
                'title': section_title,
                'subheadings': subheadings
            })
        
        # 2. 生成文章头部
        header = pm.render_assembler_header(
            title=outline.get('title', '技术博客'),
            subtitle=outline.get('subtitle', ''),
            reading_time=outline.get('reading_time', 30),
            core_value=outline.get('core_value', ''),
            table_of_contents=outline.get('table_of_contents', []),
            introduction=outline.get('introduction', ''),
            sections=toc_sections
        )
        
        # 3. 组装章节内容
        body_parts = []
        for section in sections:
            content = section.get('content', '')
            
            # 获取当前章节的 image_ids（由 artist agent 生成时记录）
            section_image_ids = section.get('image_ids', [])
            
            # 替换占位符，传入章节的 image_ids 用于精确匹配
            content = replace_placeholders(content, code_blocks, images, image_ids=section_image_ids)

            # 替换 {source_NNN} 为实际来源链接
            if search_results:
                content = self.replace_source_references(content, search_results)

            body_parts.append(content)
        
        body = '\n\n---\n\n'.join(body_parts)
        
        # 4. 生成文章尾部（支持分类展示参考来源）
        conclusion = outline.get('conclusion', {})
        footer = pm.render_assembler_footer(
            summary_points=conclusion.get('summary_points', []),
            next_steps=conclusion.get('next_steps', ''),
            reference_links=outline.get('reference_links', []),
            document_references=document_references or []
        )
        
        # 5. 组装完整文档
        full_document = header + body + footer
        
        # 6. 修复 Markdown 分隔线格式（防止 ---## 连写和 Setext 标题误判）
        full_document = _fix_markdown_separators(full_document)
        
        # 7. 统计信息
        word_count = len(full_document)
        image_count = len(images)
        code_block_count = len(code_blocks)
        
        return {
            "markdown": full_document,
            "word_count": word_count,
            "image_count": image_count,
            "code_block_count": code_block_count
        }
    
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行文档组装
        
        Args:
            state: 共享状态
            
        Returns:
            更新后的状态
        """
        if state.get('error'):
            logger.error(f"前置步骤失败，跳过文档组装: {state.get('error')}")
            state['final_markdown'] = ""
            return state
        
        outline = state.get('outline', {})
        sections = state.get('sections', [])
        if not outline or not sections:
            error_msg = "大纲或章节内容为空，无法进行文档组装"
            logger.error(error_msg)
            state['error'] = error_msg
            state['final_markdown'] = ""
            return state
        
        code_blocks = state.get('code_blocks', [])
        images = state.get('images', [])
        document_references = state.get('document_references', [])
        search_results = state.get('search_results', [])

        logger.info("开始组装文档")

        result = self.assemble(
            outline=outline,
            sections=sections,
            code_blocks=code_blocks,
            images=images,
            document_references=document_references,
            search_results=search_results
        )
        
        state['final_markdown'] = result.get('markdown', '')
        
        logger.info(f"文档组装完成: {result.get('word_count', 0)} 字, "
                   f"{result.get('image_count', 0)} 张图片, "
                   f"{result.get('code_block_count', 0)} 个代码块")
        
        return state
