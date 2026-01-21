"""
Artist Agent - 配图生成
"""

import json
import logging
import os
import re
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..prompts.prompt_manager import get_prompt_manager
from ...image_service import get_image_service, AspectRatio, ImageSize

# 从环境变量读取并行配置，默认为 3
MAX_WORKERS = int(os.environ.get('BLOG_GENERATOR_MAX_WORKERS', '3'))

logger = logging.getLogger(__name__)

# ASCII 流程图特征模式（强特征 - 必须出现）
ASCII_FLOWCHART_STRONG_PATTERNS = [
    r'\+[-=]+\+',           # +---+ 或 +===+ 边框（流程图典型特征）
    r'[-=]{2,}>',           # ---> 或 ===> 箭头（流程图典型特征）
    r'<[-=]{2,}',           # <--- 反向箭头
]

# ASCII 流程图特征模式（弱特征 - 辅助判断）
ASCII_FLOWCHART_WEAK_PATTERNS = [
    r'\|[^|]{2,}\|',        # | xxx | 内容行
    r'\+-{2,}\+',           # +--+ 连续边框
]

# Markdown 表格特征（用于排除）
MARKDOWN_TABLE_PATTERN = r'^\s*\|([^|]+\|)+\s*$'  # | col1 | col2 | 格式
MARKDOWN_TABLE_SEPARATOR = r'^\s*\|[\s:-]+\|'      # |---|---| 分隔符

# 需要排除的其他模式
EXCLUDE_PATTERNS = [
    r'^\s*<!--.*-->',           # HTML 注释
    r'^\s*#',                   # Markdown 标题
    r'^\s*[-*]\s+.*-->',        # 列表项中的箭头（如 "- item --> result"）
    r'^\s*\d+\.\s+.*-->',       # 有序列表中的箭头
    r'^\$\$.*\$\$',             # LaTeX 块公式
    r'^\$.*\$$',                # LaTeX 行内公式
]


class ArtistAgent:
    """
    配图设计师 - 负责生成技术配图
    """
    
    def __init__(self, llm_client):
        """
        初始化 Artist Agent
        
        Args:
            llm_client: LLM 客户端
        """
        self.llm = llm_client
    
    def detect_ascii_flowcharts(self, content: str) -> List[Dict[str, Any]]:
        """
        检测内容中的 ASCII 流程图
        
        Args:
            content: 章节内容
            
        Returns:
            检测到的 ASCII 流程图列表，每项包含:
            - start_line: 起始行号
            - end_line: 结束行号  
            - ascii_content: ASCII 图内容
            - original_text: 原始文本（用于替换）
        """
        lines = content.split('\n')
        ascii_regions = []
        current_region = {"start_line": -1, "lines": []}
        
        # 检查是否在代码块内
        in_code_block = False
        
        for i, line in enumerate(lines):
            # 检测代码块边界
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                # 如果进入代码块，结束当前 ASCII 区域
                if in_code_block and len(current_region["lines"]) >= 3:
                    ascii_regions.append({
                        "start_line": current_region["start_line"],
                        "end_line": i - 1,
                        "lines": current_region["lines"],
                        "ascii_content": '\n'.join(current_region["lines"]),
                        "original_text": '\n'.join(current_region["lines"])
                    })
                current_region = {"start_line": -1, "lines": []}
                continue
            
            # 跳过代码块内的内容
            if in_code_block:
                continue
            
            # 检查是否是需要排除的行
            is_excluded = (
                re.match(MARKDOWN_TABLE_PATTERN, line) or 
                re.match(MARKDOWN_TABLE_SEPARATOR, line) or
                any(re.match(p, line) for p in EXCLUDE_PATTERNS)
            )
            if is_excluded:
                # 如果当前区域有强特征，继续收集；否则跳过
                if current_region.get("has_strong_feature"):
                    current_region["lines"].append(line)
                continue
            
            # 计算该行匹配的特征
            strong_match = any(re.search(p, line) for p in ASCII_FLOWCHART_STRONG_PATTERNS)
            weak_match = any(re.search(p, line) for p in ASCII_FLOWCHART_WEAK_PATTERNS)
            
            if strong_match or weak_match:
                if current_region["start_line"] == -1:
                    current_region["start_line"] = i
                    current_region["has_strong_feature"] = False
                current_region["lines"].append(line)
                # 记录是否有强特征
                if strong_match:
                    current_region["has_strong_feature"] = True
            else:
                # 当前行不是 ASCII 图的一部分
                # 必须有强特征且至少3行才算有效的 ASCII 流程图
                if len(current_region["lines"]) >= 3 and current_region.get("has_strong_feature"):
                    ascii_regions.append({
                        "start_line": current_region["start_line"],
                        "end_line": i - 1,
                        "lines": current_region["lines"],
                        "ascii_content": '\n'.join(current_region["lines"]),
                        "original_text": '\n'.join(current_region["lines"])
                    })
                current_region = {"start_line": -1, "lines": [], "has_strong_feature": False}
        
        # 处理末尾（同样需要检查强特征）
        if len(current_region["lines"]) >= 3 and current_region.get("has_strong_feature"):
            ascii_regions.append({
                "start_line": current_region["start_line"],
                "end_line": len(lines) - 1,
                "lines": current_region["lines"],
                "ascii_content": '\n'.join(current_region["lines"]),
                "original_text": '\n'.join(current_region["lines"])
            })
        
        return ascii_regions
    
    def preprocess_ascii_flowcharts(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        预处理章节内容，将 ASCII 流程图转换为占位符
        
        Args:
            sections: 章节列表
            
        Returns:
            处理后的章节列表
        """
        total_converted = 0
        
        for section in sections:
            content = section.get('content', '')
            section_title = section.get('title', '')
            
            # 检测 ASCII 流程图
            ascii_regions = self.detect_ascii_flowcharts(content)
            
            if not ascii_regions:
                continue
            
            logger.info(f"章节 [{section_title}] 检测到 {len(ascii_regions)} 个 ASCII 流程图")
            
            # 从后向前替换，避免位置偏移
            for region in reversed(ascii_regions):
                # 构建占位符，将 ASCII 内容作为描述
                # 对 ASCII 内容进行压缩处理，移除多余空格但保留结构
                ascii_desc = region['ascii_content'].replace('\n', ' | ')
                # 限制长度，避免占位符过长
                if len(ascii_desc) > 500:
                    ascii_desc = ascii_desc[:500] + '...'
                
                placeholder = f"[IMAGE: flowchart - 根据以下 ASCII 流程图生成 Mermaid 图表: {ascii_desc}]"
                
                # 替换原内容
                content = content.replace(region['original_text'], placeholder)
                total_converted += 1
            
            section['content'] = content
        
        if total_converted > 0:
            logger.info(f"ASCII 流程图预处理完成: 共转换 {total_converted} 个")
        
        return sections
    
    def generate_image(
        self,
        image_type: str,
        description: str,
        context: str,
        audience_adaptation: str = "technical-beginner"
    ) -> Dict[str, Any]:
        """
        生成配图
        
        Args:
            image_type: 图片类型
            description: 图片描述
            context: 所在章节上下文
            audience_adaptation: 受众适配类型
            
        Returns:
            图片资源字典
        """
        pm = get_prompt_manager()
        prompt = pm.render_artist(
            image_type=image_type,
            description=description,
            context=context,
            audience_adaptation=audience_adaptation
        )
        
        # 调试日志：记录传入的上下文摘要
        context_preview = context[:200] if len(context) > 200 else context
        logger.debug(f"生成配图 - 类型: {image_type}, 描述: {description[:50]}..., 上下文预览: {context_preview}...")
        
        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response)
            content = result.get("content", "")
            
            # 清理 content：移除可能的 ```mermaid 标记
            if content.strip().startswith('```mermaid'):
                content = content.strip()
                content = content[len('```mermaid'):].strip()
                if content.endswith('```'):
                    content = content[:-3].strip()
            elif content.strip().startswith('```'):
                content = content.strip()[3:].strip()
                if content.endswith('```'):
                    content = content[:-3].strip()
            
            return {
                "render_method": result.get("render_method", "mermaid"),
                "content": content,
                "caption": result.get("caption", "")
            }
            
        except Exception as e:
            logger.error(f"配图生成失败: {e}")
            raise
    
    def _render_ai_image(self, prompt: str, caption: str, image_style: str = "") -> str:
        """
        调用 Nano Banana API 生成 AI 图片
        
        Args:
            prompt: AI 图片生成 Prompt
            caption: 图片说明
            image_style: 图片风格 ID（可选，为空则使用默认卡通风格）
            
        Returns:
            图片本地路径，失败返回 None
        """
        image_service = get_image_service()
        if not image_service or not image_service.is_available():
            logger.warning("图片生成服务不可用，跳过 AI 图片生成")
            return None
        
        try:
            # 构建完整的 Prompt
            if image_style:
                # 使用风格管理器渲染 Prompt
                from services.image_styles import get_style_manager
                style_manager = get_style_manager()
                content = f"{prompt}\n\n图片说明：{caption}"
                full_prompt = style_manager.render_prompt(image_style, content)
                logger.info(f"开始生成【文章内容图】({image_style}): {caption}")
            else:
                # 兼容旧逻辑：使用默认卡通手绘风格
                from ..prompts.prompt_manager import get_prompt_manager
                full_prompt = get_prompt_manager().render_artist_default(prompt, caption)
                logger.info(f"开始生成【文章内容图】: {caption}")
            
            result = image_service.generate(
                prompt=full_prompt,
                aspect_ratio=AspectRatio.LANDSCAPE_16_9,
                image_size=ImageSize.SIZE_1K,
                max_wait_time=600
            )
            
            if result and result.local_path:
                logger.info(f"AI 图片生成成功: {result.local_path}")
                return result.local_path
            else:
                logger.warning(f"AI 图片生成失败: {caption}")
                return None
                
        except Exception as e:
            logger.error(f"AI 图片生成异常: {e}")
            return None
    
    def extract_image_placeholders(self, content: str) -> List[Dict[str, str]]:
        """
        从内容中提取图片占位符
        
        Args:
            content: 章节内容
            
        Returns:
            图片占位符列表
        """
        # 匹配 [IMAGE: image_type - description] 格式
        pattern = r'\[IMAGE:\s*(\w+)\s*-\s*([^\]]+)\]'
        matches = re.findall(pattern, content)
        
        placeholders = []
        for image_type, description in matches:
            placeholders.append({
                "type": image_type.strip(),
                "description": description.strip()
            })
        
        return placeholders
    
    def run(self, state: Dict[str, Any], max_workers: int = None) -> Dict[str, Any]:
        """
        执行配图生成（并行）
        
        Args:
            state: 共享状态
            max_workers: 最大并行数
            
        Returns:
            更新后的状态
        """
        if state.get('error'):
            logger.error(f"前置步骤失败，跳过配图生成: {state.get('error')}")
            state['images'] = []
            return state
        
        sections = state.get('sections', [])
        if not sections:
            logger.error("没有章节内容，跳过配图生成")
            state['images'] = []
            return state
        
        # ========== 新增：ASCII 流程图预处理 ==========
        # 检测并将 ASCII 流程图转换为占位符，复用现有配图生成流程
        sections = self.preprocess_ascii_flowcharts(sections)
        state['sections'] = sections  # 更新 state 中的 sections
        
        outline = state.get('outline', {})
        sections_outline = outline.get('sections', [])
        
        # 第一步：收集所有图片生成任务，预先分配 ID 和顺序索引
        tasks = []
        image_id_counter = 1
        
        # 1. 从大纲中收集配图任务
        for i, section_outline in enumerate(sections_outline):
            image_type = section_outline.get('image_type', 'none')
            if image_type == 'none':
                continue
            
            image_description = section_outline.get('image_description', '')
            section_title = section_outline.get('title', '')
            
            section_content = ""
            if i < len(sections):
                section_content = sections[i].get('content', '')[:1000]
            
            tasks.append({
                'order_idx': len(tasks),
                'image_id': f"img_{image_id_counter}",
                'section_idx': i if i < len(sections) else None,
                'source': 'outline',
                'image_type': image_type,
                'description': image_description,
                'context': f"章节标题: {section_title}\n\n章节内容摘要:\n{section_content}",
                'audience_adaptation': state.get('audience_adaptation', 'technical-beginner')
            })
            image_id_counter += 1
        
        # 2. 从章节占位符中收集配图任务
        for section_idx, section in enumerate(sections):
            content = section.get('content', '')
            section_title = section.get('title', '')
            
            placeholders = self.extract_image_placeholders(content)
            
            for placeholder in placeholders:
                placeholder_text = f"[IMAGE: {placeholder['type']} - {placeholder['description']}]"
                placeholder_pos = content.find(placeholder_text)
                if placeholder_pos >= 0:
                    start = max(0, placeholder_pos - 1000)
                    end = min(len(content), placeholder_pos + len(placeholder_text) + 1000)
                    surrounding_context = content[start:end]
                else:
                    surrounding_context = content[:2000]
                
                tasks.append({
                    'order_idx': len(tasks),
                    'image_id': f"img_{image_id_counter}",
                    'section_idx': section_idx,
                    'source': 'placeholder',
                    'image_type': placeholder['type'],
                    'description': placeholder['description'],
                    'context': f"章节标题: {section_title}\n\n相关内容:\n{surrounding_context}",
                    'audience_adaptation': state.get('audience_adaptation', 'technical-beginner')
                })
                image_id_counter += 1
        
        if not tasks:
            logger.info("没有配图任务，跳过配图生成")
            state['images'] = []
            return state
        
        total_image_count = len(tasks)
        
        # 使用环境变量配置或传入的参数
        if max_workers is None:
            max_workers = MAX_WORKERS
        
        logger.info(f"开始生成配图 (共 {total_image_count} 张)，使用 {min(max_workers, total_image_count)} 个并行线程")
        
        # 第二步：并行生成图片
        results = [None] * len(tasks)
        
        def generate_task(task):
            """单个图片生成任务"""
            try:
                image = self.generate_image(
                    image_type=task['image_type'],
                    description=task['description'],
                    context=task['context'],
                    audience_adaptation=task.get('audience_adaptation', 'technical-beginner')
                )
                
                render_method = image.get('render_method', 'mermaid')
                rendered_path = None
                
                # 如果是 ai_image 类型，调用 Nano Banana API 生成图片
                if render_method == 'ai_image':
                    # 从 state 获取图片风格参数
                    image_style = state.get('image_style', '')
                    rendered_path = self._render_ai_image(
                        prompt=image.get('content', ''),
                        caption=image.get('caption', ''),
                        image_style=image_style
                    )
                    if rendered_path:
                        rendered_path = f"./images/{rendered_path.split('/')[-1]}"
                
                return {
                    'success': True,
                    'order_idx': task['order_idx'],
                    'section_idx': task['section_idx'],
                    'source': task['source'],
                    'image_resource': {
                        "id": task['image_id'],
                        "render_method": render_method,
                        "content": image.get('content', ''),
                        "caption": image.get('caption', ''),
                        "rendered_path": rendered_path
                    }
                }
            except Exception as e:
                logger.error(f"配图生成失败 [{task['image_id']}]: {e}")
                return {
                    'success': False,
                    'order_idx': task['order_idx'],
                    'section_idx': task['section_idx'],
                    'image_id': task['image_id'],
                    'error': str(e)
                }
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(generate_task, task): task for task in tasks}
            
            for future in as_completed(futures):
                result = future.result()
                order_idx = result['order_idx']
                results[order_idx] = result
                
                if result['success']:
                    img_id = result['image_resource']['id']
                    img_type = tasks[order_idx]['image_type']
                    source = result['source']
                    logger.info(f"配图生成完成: {img_id} ({img_type}) [来源:{source}]")
        
        # 第三步：按原始顺序组装结果，更新章节关联
        images = []
        section_image_ids = {i: [] for i in range(len(sections))}
        
        for result in results:
            if result and result['success']:
                image_resource = result['image_resource']
                images.append(image_resource)
                
                section_idx = result['section_idx']
                source = result['source']
                
                # 更新章节关联
                if section_idx is not None and section_idx < len(sections):
                    # 大纲来源的图片始终关联
                    # 占位符来源的图片只有 rendered_path 时才关联
                    if source == 'outline' or image_resource.get('rendered_path'):
                        section_image_ids[section_idx].append(image_resource['id'])
        
        # 更新章节的 image_ids
        for section_idx, image_ids in section_image_ids.items():
            if image_ids:
                if 'image_ids' not in sections[section_idx]:
                    sections[section_idx]['image_ids'] = []
                sections[section_idx]['image_ids'].extend(image_ids)
        
        state['images'] = images
        logger.info(f"配图生成完成: 共 {len(images)} 张图片")
        
        return state
