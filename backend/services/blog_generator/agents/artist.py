"""
Artist Agent - 配图生成
"""

import json
import logging
import os
import re
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..prompts import get_prompt_manager
from ...image_service import get_image_service, AspectRatio, ImageSize

# 从环境变量读取并行配置，默认为 3
MAX_WORKERS = int(os.environ.get('BLOG_GENERATOR_MAX_WORKERS', '3'))

def _should_use_parallel():
    """判断是否应该使用并行执行。当开启追踪时禁用并行，避免上下文丢失。"""
    if os.environ.get('TRACE_ENABLED', 'false').lower() == 'true':
        return False
    return True

logger = logging.getLogger(__name__)

# 图片预算：根据文章长度限制总图片数
IMAGE_BUDGET = {
    'mini': 3,
    'short': 5,
    'medium': 8,
    'long': 12,
    'custom': 8,
}


def _extract_json(text: str) -> dict:
    """从 LLM 响应中提取 JSON（处理 markdown 包裹）"""
    text = text.strip()
    if '```json' in text:
        start = text.find('```json') + 7
        end = text.find('```', start)
        if end != -1:
            text = text[start:end].strip()
        else:
            text = text[start:].strip()
    elif '```' in text:
        start = text.find('```') + 3
        end = text.find('```', start)
        if end != -1:
            text = text[start:end].strip()
        else:
            text = text[start:].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return json.loads(text, strict=False)

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

    # ========== Mermaid 语法修复 ==========

    def _sanitize_mermaid(self, code: str) -> str:
        """静态预处理：修复常见 Mermaid 语法问题"""
        # 1. 移除 ```mermaid 标记
        code = re.sub(r'^```(?:mermaid)?\s*\n?', '', code.strip())
        code = re.sub(r'\n?```\s*$', '', code.strip())
        # 2. 移除节点文本中的 \n 换行符
        code = re.sub(r'(?<=\[)([^\]]*?)\\n([^\]]*?)(?=\])', r'\1 \2', code)
        code = re.sub(r'(?<=\()([^\)]*?)\\n([^\)]*?)(?=\))', r'\1 \2', code)
        # 3. 修复重复箭头 --> -->  变为 -->
        code = re.sub(r'(-+>)\s*\1', r'\1', code)
        return code.strip()

    def _validate_mermaid(self, code: str) -> tuple:
        """基础语法校验，返回 (is_valid, error_msg)"""
        errors = []
        first_line = code.strip().split('\n')[0].strip() if code.strip() else ''
        if not re.match(r'^(flowchart|graph|sequenceDiagram|classDiagram|stateDiagram|gantt|pie|erDiagram|mindmap|timeline)', first_line):
            errors.append("缺少图表类型声明")
        subgraph_count = len(re.findall(r'\bsubgraph\b', code))
        end_count = len(re.findall(r'^\s*end\s*$', code, re.MULTILINE))
        if subgraph_count != end_count:
            errors.append(f"subgraph({subgraph_count}) 与 end({end_count}) 不匹配")
        if errors:
            return False, "; ".join(errors)
        return True, "OK"

    def _repair_mermaid(self, mermaid_code: str, error_msg: str) -> str:
        """用 LLM 修复 Mermaid 语法错误（最多 2 次重试）"""
        max_retries = int(os.getenv('MERMAID_REPAIR_MAX_RETRIES', '2'))
        for attempt in range(max_retries):
            logger.info(f"[Mermaid] 语法修复 (尝试 {attempt + 1}/{max_retries}): {error_msg}")
            prompt = f"""以下 Mermaid 代码有语法错误，请修复。只输出修复后的纯 Mermaid 代码，不要包含 ```mermaid 标记。

错误信息：{error_msg}

原始代码：
{mermaid_code}

修复要求：只修复语法错误，不改变图表内容和结构。节点文本不要用 \\n。含特殊字符的文本用双引号包裹。节点 ID 只用英文字母和数字。确保 subgraph 都有对应的 end。"""
            try:
                response = self.llm.chat(messages=[{"role": "user", "content": prompt}])
                repaired = self._sanitize_mermaid(response.strip())
                is_valid, new_error = self._validate_mermaid(repaired)
                if is_valid:
                    logger.info("[Mermaid] 语法修复成功")
                    return repaired
                error_msg = new_error
                mermaid_code = repaired
            except Exception as e:
                logger.error(f"[Mermaid] 修复调用失败: {e}")
                break
        logger.warning("[Mermaid] 修复达到最大重试次数，返回最后结果")
        return mermaid_code

    @observe(name="artist.generate_image", as_type="generation")
    def generate_image(
        self,
        image_type: str,
        description: str,
        context: str,
        audience_adaptation: str = "technical-beginner",
        article_title: str = "",  # 新增：文章标题
        illustration_type: str = "",  # 新增：插图类型（Type × Style 二维系统）
        **kwargs  # 接收 langfuse_parent_trace_id 等参数
    ) -> Dict[str, Any]:
        """
        生成配图
        
        Args:
            image_type: 图片类型
            description: 图片描述
            context: 所在章节上下文
            audience_adaptation: 受众适配类型
            article_title: 文章标题（用于图片说明）
            illustration_type: 插图类型 ID（infographic/scene/flowchart/comparison/framework/timeline）
            
        Returns:
            图片资源字典
        """
        pm = get_prompt_manager()
        prompt = pm.render_artist(
            image_type=image_type,
            description=description,
            context=context,
            audience_adaptation=audience_adaptation,
            article_title=article_title,
            illustration_type=illustration_type
        )
        
        # 调试日志：记录传入的上下文摘要
        context_preview = context[:200] if len(context) > 200 else context
        logger.debug(f"生成配图 - 类型: {image_type}, 描述: {description[:50]}..., 上下文预览: {context_preview}...")
        
        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            result = _extract_json(response)
            content = result.get("content", "")
            render_method = result.get("render_method", "mermaid")
            caption = result.get("caption", "")

            # 改进 caption：如果 LLM 返回的 caption 是空的或太通用，使用章节标题
            if not caption or caption == article_title:
                caption = description[:60] if description else article_title

            # Mermaid 语法修复链
            if render_method == "mermaid":
                content = self._sanitize_mermaid(content)
                is_valid, error_msg = self._validate_mermaid(content)
                if not is_valid:
                    logger.warning(f"[Mermaid] 语法校验失败: {error_msg}")
                    content = self._repair_mermaid(content, error_msg)
            else:
                # 非 mermaid：仅清理 markdown 标记
                if content.strip().startswith('```'):
                    content = content.strip()
                    if content.startswith('```mermaid'):
                        content = content[len('```mermaid'):].strip()
                    else:
                        content = content[3:].strip()
                    if content.endswith('```'):
                        content = content[:-3].strip()

            return {
                "render_method": render_method,
                "content": content,
                "caption": result.get("caption", "")
            }
            
        except Exception as e:
            logger.error(f"配图生成失败: {e}")
            raise
    
    def _render_ai_image(
        self,
        prompt: str,
        caption: str,
        image_style: str = "",
        aspect_ratio: str = "16:9",
        illustration_type: str = ""
    ) -> str:
        """
        调用 Nano Banana API 生成 AI 图片
        
        Args:
            prompt: AI 图片生成 Prompt
            caption: 图片说明
            image_style: 图片风格 ID（可选，为空则使用默认卡通风格）
            aspect_ratio: 宽高比（16:9 或 9:16）
            illustration_type: 插图类型 ID（可选，用于 Type × Style 二维渲染）
            
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
                # 使用风格管理器渲染 Prompt（支持 Type × Style 二维渲染）
                from services.image_styles import get_style_manager
                style_manager = get_style_manager()
                content = f"{prompt}\n\n图片说明：{caption}"
                full_prompt = style_manager.render_prompt(image_style, content, illustration_type=illustration_type)
                type_label = f", type={illustration_type}" if illustration_type else ""
                logger.info(f"开始生成【文章内容图】({image_style}{type_label}): {caption}")
            else:
                # 兼容旧逻辑：使用默认卡通手绘风格
                from ..prompts import get_prompt_manager
                full_prompt = get_prompt_manager().render_artist_default(prompt, caption)
                logger.info(f"开始生成【文章内容图】: {caption}")
            
            # 根据前端选择的宽高比生成图片
            aspect_ratio_enum = AspectRatio.PORTRAIT_9_16 if aspect_ratio == "9:16" else AspectRatio.LANDSCAPE_16_9
            logger.info(f"使用宽高比: {aspect_ratio}")
            
            result = image_service.generate(
                prompt=full_prompt,
                aspect_ratio=aspect_ratio_enum,
                image_size=ImageSize.SIZE_1K,
                max_wait_time=600
            )
            
            if result and (result.oss_url or result.local_path):
                # 优先返回 OSS URL
                final_path = result.oss_url or result.local_path
                logger.info(f"AI 图片生成成功: {final_path}")
                return final_path
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
    
    @observe(name="artist.detect_missing_diagrams", as_type="generation")
    def detect_missing_diagrams(
        self,
        sections: List[Dict[str, Any]],
        **kwargs  # 接收 langfuse_parent_trace_id 等参数
    ) -> List[Dict[str, Any]]:
        """
        检测章节中缺失的图表
        
        Args:
            sections: 章节列表
            
        Returns:
            需要补充的图表任务列表
        """
        diagram_tasks = []
        pm = get_prompt_manager()
        
        for section_idx, section in enumerate(sections):
            content = section.get('content', '')
            title = section.get('title', '')
            
            # 跳过已有足够图片的章节（已有 2 个以上图片占位符）
            existing_placeholders = self.extract_image_placeholders(content)
            if len(existing_placeholders) >= 2:
                continue
            
            # 跳过内容过短的章节
            if len(content) < 500:
                continue
            
            try:
                # 调用 LLM 检测缺失图表
                prompt = pm.render_missing_diagram_detector(
                    section_title=title,
                    content=content[:3000]  # 限制内容长度
                )
                
                response = self.llm.chat(
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                
                result = _extract_json(response)
                needs_diagrams = result.get('needs_diagrams', [])
                
                # 每个章节最多补充 1 个图表
                if needs_diagrams:
                    item = needs_diagrams[0]
                    diagram_tasks.append({
                        'section_idx': section_idx,
                        'image_type': item.get('diagram_type', 'flowchart'),
                        'description': item.get('description', ''),
                        'context': item.get('context', content[:1000])
                    })
                    logger.info(f"章节 [{title}] 检测到缺失图表: {item.get('diagram_type')}")
                    
            except Exception as e:
                logger.warning(f"检测缺失图表失败 [{title}]: {e}")
                continue
        
        return diagram_tasks
    
    @observe(name="artist.run")
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
        
        # ========== Mini 模式：使用专用的章节配图生成 ==========
        target_length = state.get('target_length', 'medium')
        if target_length in ('mini', 'short'):
            logger.info(f"[{target_length}] 模式：使用章节配图生成")
            return self._generate_mini_section_images(state, sections)
        
        # ========== 新增：ASCII 流程图预处理 ==========
        # 检测并将 ASCII 流程图转换为占位符，复用现有配图生成流程
        sections = self.preprocess_ascii_flowcharts(sections)
        state['sections'] = sections  # 更新 state 中的 sections
        
        # ========== 新增：缺失图表检测 ==========
        # 用 LLM 分析内容，检测需要补图的位置
        missing_diagram_tasks = self.detect_missing_diagrams(sections)
        
        if missing_diagram_tasks:
            logger.info(f"检测到 {len(missing_diagram_tasks)} 个缺失图表位置")
        
        outline = state.get('outline', {})
        sections_outline = outline.get('sections', [])
        
        # 第一步：收集所有图片生成任务，预先分配 ID 和顺序索引
        tasks = []
        image_id_counter = 1
        
        # 1. 从大纲中收集配图任务
        article_title = state.get('topic', '')  # 获取文章标题
        for i, section_outline in enumerate(sections_outline):
            image_type = section_outline.get('image_type', 'none')
            if image_type == 'none':
                continue
            
            image_description = section_outline.get('image_description', '')
            section_title = section_outline.get('title', '')
            
            section_content = ""
            if i < len(sections):
                section_content = sections[i].get('content', '')[:1000]
            
            # Type × Style: 优先使用大纲指定的 illustration_type，否则自动推荐
            illustration_type = section_outline.get('illustration_type', '')
            if not illustration_type and section_content:
                from services.image_styles import get_style_manager
                illustration_type = get_style_manager().auto_recommend_type(section_content)
                logger.debug(f"章节 {i} 自动推荐 illustration_type: {illustration_type}")
            
            tasks.append({
                'order_idx': len(tasks),
                'image_id': f"img_{image_id_counter}",
                'section_idx': i if i < len(sections) else None,
                'source': 'outline',
                'image_type': image_type,
                'description': image_description,
                'context': f"章节标题: {section_title}\n\n章节内容摘要:\n{section_content}",
                'audience_adaptation': state.get('audience_adaptation', 'technical-beginner'),
                'article_title': article_title,
                'illustration_type': illustration_type
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
                
                # Type × Style: 根据占位符上下文自动推荐
                from services.image_styles import get_style_manager
                ph_illustration_type = get_style_manager().auto_recommend_type(surrounding_context)
                
                tasks.append({
                    'order_idx': len(tasks),
                    'image_id': f"img_{image_id_counter}",
                    'section_idx': section_idx,
                    'source': 'placeholder',
                    'image_type': placeholder['type'],
                    'description': placeholder['description'],
                    'context': f"章节标题: {section_title}\n\n相关内容:\n{surrounding_context}",
                    'audience_adaptation': state.get('audience_adaptation', 'technical-beginner'),
                    'article_title': article_title,
                    'illustration_type': ph_illustration_type
                })
                image_id_counter += 1
        
        # 3. 从缺失图表检测收集配图任务
        for task in missing_diagram_tasks:
            section_idx = task['section_idx']
            section_title = sections[section_idx].get('title', '') if section_idx < len(sections) else ''
            
            # Type × Style: 根据缺失图表上下文自动推荐
            from services.image_styles import get_style_manager
            md_illustration_type = get_style_manager().auto_recommend_type(task['context'])
            
            tasks.append({
                'order_idx': len(tasks),
                'image_id': f"img_{image_id_counter}",
                'section_idx': section_idx,
                'source': 'missing_diagram',
                'image_type': task['image_type'],
                'description': task['description'],
                'context': f"章节标题: {section_title}\n\n相关内容:\n{task['context']}",
                'audience_adaptation': state.get('audience_adaptation', 'technical-beginner'),
                'article_title': article_title,
                'illustration_type': md_illustration_type
            })
            image_id_counter += 1
        
        if not tasks:
            logger.info("没有配图任务，跳过配图生成")
            state['images'] = []
            return state

        # 图片预算控制：根据文章长度限制总图片数
        target_length = state.get('target_length', 'medium')
        budget = IMAGE_BUDGET.get(target_length, IMAGE_BUDGET['medium'])
        if len(tasks) > budget:
            logger.info(f"图片预算控制: {len(tasks)} 张 → {budget} 张 (target_length={target_length})")
            # 优先保留 outline 来源，其次 placeholder，最后 missing_diagram
            priority = {'outline': 0, 'placeholder': 1, 'missing_diagram': 2}
            tasks.sort(key=lambda t: (priority.get(t['source'], 9), t['order_idx']))
            tasks = tasks[:budget]
            # 重新编号 order_idx
            for i, task in enumerate(tasks):
                task['order_idx'] = i

        total_image_count = len(tasks)
        
        # 使用环境变量配置或传入的参数
        if max_workers is None:
            max_workers = MAX_WORKERS
        
        use_parallel = _should_use_parallel()
        if use_parallel:
            logger.info(f"开始生成配图 (共 {total_image_count} 张)，使用 {min(max_workers, total_image_count)} 个并行线程")
        else:
            logger.info(f"开始生成配图 (共 {total_image_count} 张)，使用串行模式（追踪已启用）")
        
        # 第二步：生成图片
        results = [None] * len(tasks)
        
        def generate_single_task(task):
            """单个图片生成任务"""
            try:
                # 生成图片
                image = self.generate_image(
                    image_type=task['image_type'],
                    description=task['description'],
                    context=task['context'],
                    audience_adaptation=task.get('audience_adaptation', 'technical-beginner'),
                    article_title=task.get('article_title', ''),
                    illustration_type=task.get('illustration_type', '')
                )
                
                render_method = image.get('render_method', 'mermaid')
                rendered_path = None
                
                # 如果是 ai_image 类型，调用 Nano Banana API 生成图片
                if render_method == 'ai_image':
                    # 从 state 获取图片风格参数
                    image_style = state.get('image_style', '')
                    
                    # 区分封面图和内容图的宽高比
                    # 第一个章节的图片作为封面图，使用前端选择的宽高比
                    # 其他章节的图片保持 16:9
                    if task['source'] == 'outline' and task['section_idx'] == 0:
                        # 封面图（第一个章节）：使用前端选择的宽高比（与视频一致）
                        aspect_ratio = state.get('aspect_ratio', '16:9')
                        logger.info(f"检测到封面图，使用宽高比: {aspect_ratio}")
                    else:
                        # 内容图：保持 16:9
                        aspect_ratio = '16:9'
                    
                    # 直接使用文章标题作为图片标题，不使用 LLM 生成的 caption
                    article_title = task.get('article_title', '')
                    
                    rendered_path = self._render_ai_image(
                        prompt=image.get('content', ''),
                        caption=article_title,  # 使用文章标题，而不是 LLM 生成的 caption
                        image_style=image_style,
                        aspect_ratio=aspect_ratio,
                        illustration_type=task.get('illustration_type', '')
                    )
                    if rendered_path:
                        # 如果是 OSS URL，直接使用；否则转为相对路径
                        if not rendered_path.startswith('http'):
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
        
        if use_parallel:
            # 并行执行
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(generate_single_task, task): task for task in tasks}
                
                for future in as_completed(futures):
                    result = future.result()
                    order_idx = result['order_idx']
                    results[order_idx] = result
                    
                    if result['success']:
                        img_id = result['image_resource']['id']
                        img_type = tasks[order_idx]['image_type']
                        source = result['source']
                        logger.info(f"配图生成完成: {img_id} ({img_type}) [来源:{source}]")
        else:
            # 串行执行（追踪模式）- 直接调用方法以保持 Langfuse 上下文
            for task in tasks:
                try:
                    image = self.generate_image(
                        image_type=task['image_type'],
                        description=task['description'],
                        context=task['context'],
                        audience_adaptation=task.get('audience_adaptation', 'technical-beginner'),
                        article_title=task.get('article_title', '')
                    )
                    
                    render_method = image.get('render_method', 'mermaid')
                    rendered_path = None
                    
                    if render_method == 'ai_image':
                        image_style = state.get('image_style', '')
                        if task['source'] == 'outline' and task['section_idx'] == 0:
                            aspect_ratio = state.get('aspect_ratio', '16:9')
                        else:
                            aspect_ratio = '16:9'
                        
                        article_title = task.get('article_title', '')
                        rendered_path = self._render_ai_image(
                            prompt=image.get('content', ''),
                            caption=article_title,
                            image_style=image_style,
                            aspect_ratio=aspect_ratio
                        )
                        if rendered_path and not rendered_path.startswith('http'):
                            rendered_path = f"./images/{rendered_path.split('/')[-1]}"
                    
                    results[task['order_idx']] = {
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
                    logger.info(f"配图生成完成: {task['image_id']} ({task['image_type']}) [来源:{task['source']}]")
                except Exception as e:
                    logger.error(f"配图生成失败 [{task['image_id']}]: {e}")
                    results[task['order_idx']] = {
                        'success': False,
                        'order_idx': task['order_idx'],
                        'section_idx': task['section_idx'],
                        'image_id': task['image_id'],
                        'error': str(e)
                    }
        
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
    
    def _generate_mini_section_images(
        self,
        state: Dict[str, Any],
        sections: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Mini 模式：为每个章节生成统一风格的配图
        
        这些配图同时用于：
        1. 博客文章展示（插入到章节末尾）
        2. 视频生成（作为首尾帧过渡的素材）
        
        Args:
            state: 共享状态
            sections: 章节列表
            
        Returns:
            更新后的状态
        """
        from ..prompts import get_prompt_manager
        from ...image_service import get_image_service, AspectRatio, ImageSize
        
        image_service = get_image_service()
        if not image_service or not image_service.is_available():
            logger.warning("[Mini 模式] 图片生成服务不可用，跳过章节配图生成")
            state['images'] = []
            state['section_images'] = []
            return state
        
        pm = get_prompt_manager()
        
        # 获取配置
        image_style = state.get('image_style', '')
        aspect_ratio = state.get('aspect_ratio', '16:9')
        article_title = state.get('topic', '')
        
        # 根据宽高比选择图片比例
        if aspect_ratio == "9:16":
            image_aspect_ratio = AspectRatio.PORTRAIT_9_16
        else:
            image_aspect_ratio = AspectRatio.LANDSCAPE_16_9
        
        images = []
        section_images = []  # 用于视频生成的图片 URL 列表
        
        max_workers = MAX_WORKERS
        
        def generate_section_image(idx: int, section: Dict[str, Any]):
            """生成单个章节的配图"""
            section_title = section.get('title', f'章节{idx + 1}')
            section_content = section.get('content', '')
            
            # 提取章节摘要（取前 2000 字）
            section_summary = section_content[:2000] if section_content else section_title
            
            try:
                # 生成图片 Prompt
                if image_style:
                    from ...image_styles import get_style_manager
                    style_manager = get_style_manager()
                    # Type × Style: Mini 模式也自动推荐 illustration_type
                    mini_illustration_type = style_manager.auto_recommend_type(section_summary)
                    image_prompt = style_manager.render_prompt(image_style, section_summary, illustration_type=mini_illustration_type)
                else:
                    # 使用封面图模板
                    image_prompt = pm.render_cover_image_prompt(
                        article_summary=f"章节标题：{section_title}\n\n{section_summary}"
                    )
                
                logger.info(f"[Mini 模式] 生成章节 {idx + 1} 配图: {section_title}")
                
                result = image_service.generate(
                    prompt=image_prompt,
                    aspect_ratio=image_aspect_ratio,
                    image_size=ImageSize.SIZE_1K,
                    max_wait_time=600
                )
                
                if result and (result.oss_url or result.url):
                    image_url = result.oss_url or result.url
                    
                    return {
                        'success': True,
                        'idx': idx,
                        'section_title': section_title,
                        'image_url': image_url,
                        'image_resource': {
                            'id': f'mini_img_{idx + 1}',
                            'render_method': 'ai_image',
                            'content': image_prompt,
                            'caption': section_title,
                            'rendered_path': image_url
                        }
                    }
                else:
                    logger.warning(f"[Mini 模式] 章节 {idx + 1} 配图生成失败")
                    return {'success': False, 'idx': idx}
                    
            except Exception as e:
                logger.error(f"[Mini 模式] 章节 {idx + 1} 配图生成异常: {e}")
                return {'success': False, 'idx': idx, 'error': str(e)}
        
        # 并行生成所有章节配图
        logger.info(f"[Mini 模式] 开始并行生成 {len(sections)} 张章节配图")
        
        results = [None] * len(sections)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(generate_section_image, idx, section): idx
                for idx, section in enumerate(sections)
            }
            
            for future in as_completed(futures):
                result = future.result()
                if result:
                    results[result['idx']] = result
        
        # 按顺序组装结果
        for idx, result in enumerate(results):
            if result and result.get('success'):
                images.append(result['image_resource'])
                section_images.append(result['image_url'])
                
                # 更新章节的 image_ids
                if idx < len(sections):
                    if 'image_ids' not in sections[idx]:
                        sections[idx]['image_ids'] = []
                    sections[idx]['image_ids'].append(result['image_resource']['id'])
                
                logger.info(f"[Mini 模式] 章节 {idx + 1} 配图完成: {result['image_url'][:80]}...")
            else:
                # 配图失败，添加空占位
                section_images.append(None)
        
        # 过滤掉失败的配图
        section_images = [url for url in section_images if url]
        
        state['images'] = images
        state['section_images'] = section_images  # 用于视频生成
        state['sections'] = sections
        
        logger.info(f"[Mini 模式] 章节配图生成完成: 共 {len(images)} 张")
        
        return state
