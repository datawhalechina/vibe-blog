"""
工具函数
"""

import re
import hashlib
from typing import List, Dict, Any
from collections import OrderedDict


def deduplicate_by_url(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    根据 URL 去重搜索结果
    
    Args:
        results: 搜索结果列表
        
    Returns:
        去重后的结果列表
    """
    seen_urls = set()
    unique_results = []
    
    for item in results:
        url = item.get('url', '')
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_results.append(item)
    
    return unique_results


def extract_key_concepts(results: List[Dict[str, Any]], max_concepts: int = 10) -> List[str]:
    """
    从搜索结果中提取关键概念
    
    Args:
        results: 搜索结果列表
        max_concepts: 最大概念数
        
    Returns:
        关键概念列表
    """
    # 简单实现：从标题和内容中提取高频词
    # 实际使用时可以用 LLM 提取
    all_text = ' '.join([
        item.get('title', '') + ' ' + item.get('content', '')
        for item in results
    ])
    
    # 简单的词频统计（实际应用中应该用更复杂的 NLP）
    words = re.findall(r'\b[A-Za-z]{3,}\b', all_text)
    word_freq = {}
    for word in words:
        word_lower = word.lower()
        word_freq[word_lower] = word_freq.get(word_lower, 0) + 1
    
    # 排序并返回高频词
    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, freq in sorted_words[:max_concepts]]


def generate_anchor_id(title: str) -> str:
    """
    根据标题生成锚点 ID
    
    Args:
        title: 章节标题
        
    Returns:
        锚点 ID
    """
    # 移除特殊字符，转换为小写，空格替换为连字符
    anchor = re.sub(r'[^\w\s-]', '', title.lower())
    anchor = re.sub(r'\s+', '-', anchor.strip())
    return anchor


def estimate_reading_time(text: str, words_per_minute: int = 200) -> int:
    """
    估算阅读时间
    
    Args:
        text: 文本内容
        words_per_minute: 每分钟阅读字数
        
    Returns:
        阅读时间（分钟）
    """
    # 中文按字符计算，英文按单词计算
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    english_words = len(re.findall(r'\b[A-Za-z]+\b', text))
    
    # 中文阅读速度约 300 字/分钟，英文约 200 词/分钟
    chinese_time = chinese_chars / 300
    english_time = english_words / 200
    
    return max(1, int(chinese_time + english_time))


def generate_table_of_contents(sections: List[Dict[str, Any]]) -> str:
    """
    生成目录 Markdown
    
    Args:
        sections: 章节列表
        
    Returns:
        目录 Markdown 字符串
    """
    toc_lines = []
    for i, section in enumerate(sections, 1):
        title = section.get('title', f'章节 {i}')
        anchor = generate_anchor_id(title)
        toc_lines.append(f"- [{title}](#{anchor})")
    
    return '\n'.join(toc_lines)


def replace_placeholders(
    content: str, 
    code_blocks: List[Dict], 
    images: List[Dict],
    image_ids: List[str] = None
) -> str:
    """
    替换内容中的占位符
    
    Args:
        content: 原始内容
        code_blocks: 代码块列表
        images: 图片列表（完整的图片资源列表）
        image_ids: 当前章节的图片ID列表（用于精确匹配）
        
    Returns:
        替换后的内容
    """
    result = content
    
    # 替换代码占位符 [CODE: xxx - description]
    for code in code_blocks:
        code_id = code.get('id', '')
        pattern = rf'\[CODE:\s*{re.escape(code_id)}[^\]]*\]'
        
        code_content = code.get('code', '').strip()
        language = code.get('language', 'python')
        
        # 移除 LLM 可能添加的代码块标记，然后统一重新包装
        # 移除开头的 ```xxx，同时提取语言类型
        if code_content.startswith('```'):
            first_newline = code_content.find('\n')
            if first_newline != -1:
                # 提取语言类型（如 ```python 中的 python）
                lang_line = code_content[:first_newline].strip()
                if len(lang_line) > 3:
                    language = lang_line[3:].strip()  # 使用 LLM 指定的语言
                code_content = code_content[first_newline + 1:]
            else:
                code_content = code_content[3:]
        # 移除结尾的 ```
        if code_content.rstrip().endswith('```'):
            code_content = code_content.rstrip()[:-3].rstrip()
        # 统一包装
        code_block = f"```{language}\n{code_content}\n```"
        
        output_content = code.get('output', '').strip()
        # 同样处理输出
        if output_content.startswith('```'):
            first_newline = output_content.find('\n')
            if first_newline != -1:
                output_content = output_content[first_newline + 1:]
            else:
                output_content = output_content[3:]
        if output_content.rstrip().endswith('```'):
            output_content = output_content.rstrip()[:-3].rstrip()
        output_block = f"```\n{output_content}\n```"
        
        replacement = f"{code_block}\n\n#### OUTPUT\n{output_block}\n\n{code.get('explanation', '')}"
        # 使用 lambda 避免替换字符串中的反斜杠被解释为转义序列
        result = re.sub(pattern, lambda m: replacement, result)
    
    # 清理未被替换的代码占位符（代码生成失败的情况）
    remaining_code_pattern = r'\[CODE:\s*[^\]]+\]'
    result = re.sub(remaining_code_pattern, '', result)
    
    # 替换图片占位符 [IMAGE: xxx - description]
    image_pattern = r'\[IMAGE:\s*[^\]]+\]'
    image_matches = list(re.finditer(image_pattern, result))
    
    # 构建 image_id -> image 的映射表
    image_map = {img.get('id'): img for img in images}
    
    # 获取当前章节应该使用的图片列表
    if image_ids:
        # 使用传入的 image_ids 精确匹配
        section_images = [image_map.get(img_id) for img_id in image_ids if image_map.get(img_id)]
    else:
        # 兼容旧逻辑：按顺序使用
        section_images = images
    
    # 从后往前替换，避免位置偏移
    for i, match in enumerate(reversed(image_matches)):
        img_index = len(image_matches) - 1 - i
        if img_index < len(section_images):
            img = section_images[img_index]
            if img is None:
                continue
            render_method = img.get('render_method', 'mermaid')
            
            if render_method == 'mermaid':
                img_content = img.get('content', '').strip()
                # 移除 LLM 可能添加的代码块标记，然后统一重新包装
                if img_content.startswith('```'):
                    first_newline = img_content.find('\n')
                    if first_newline != -1:
                        img_content = img_content[first_newline + 1:]
                    else:
                        img_content = img_content[3:]
                if img_content.rstrip().endswith('```'):
                    img_content = img_content.rstrip()[:-3].rstrip()
                # 统一包装为 mermaid 代码块
                replacement = f"```mermaid\n{img_content}\n```\n\n*{img.get('caption', '')}*"
            elif render_method == 'ai_image':
                rendered_path = img.get('rendered_path') or 'placeholder.png'
                caption = img.get('caption', '')
                # 只用 alt text，不再额外输出斜体 caption，避免与章节标题视觉重复
                replacement = f"![{caption}]({rendered_path})"
            else:
                rendered_path = img.get('rendered_path') or 'placeholder.png'
                replacement = f"![{img.get('caption', '')}]({rendered_path})"
            
            result = result[:match.start()] + replacement + result[match.end():]
    
    return result


def format_reference_links(links: List[str]) -> str:
    """
    格式化参考链接
    
    Args:
        links: 链接列表
        
    Returns:
        格式化后的 Markdown
    """
    if not links:
        return "暂无参考资料"
    
    lines = []
    for i, link in enumerate(links, 1):
        lines.append(f"{i}. {link}")
    
    return '\n'.join(lines)


def format_summary_points(points: List[str]) -> str:
    """
    格式化总结要点
    
    Args:
        points: 要点列表
        
    Returns:
        格式化后的 Markdown
    """
    if not points:
        return ""
    
    lines = []
    for point in points:
        lines.append(f"- {point}")
    
    return '\n'.join(lines)
