"""
Artist Agent - 配图生成
"""

import json
import logging
import re
from typing import Dict, Any, List

from ..prompts.prompt_manager import get_prompt_manager
from ...image_service import get_image_service, AspectRatio, ImageSize

logger = logging.getLogger(__name__)


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
    
    def generate_image(
        self,
        image_type: str,
        description: str,
        context: str
    ) -> Dict[str, Any]:
        """
        生成配图
        
        Args:
            image_type: 图片类型
            description: 图片描述
            context: 所在章节上下文
            
        Returns:
            图片资源字典
        """
        pm = get_prompt_manager()
        prompt = pm.render_artist(
            image_type=image_type,
            description=description,
            context=context
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
    
    def _render_ai_image(self, prompt: str, caption: str) -> str:
        """
        调用 Nano Banana API 生成 AI 图片
        
        Args:
            prompt: AI 图片生成 Prompt
            caption: 图片说明
            
        Returns:
            图片本地路径，失败返回 None
        """
        image_service = get_image_service()
        if not image_service or not image_service.is_available():
            logger.warning("图片生成服务不可用，跳过 AI 图片生成")
            return None
        
        try:
            # 构建完整的 Prompt（卡通手绘信息图风格）
            full_prompt = f"""请根据输入内容提取核心主题与要点，生成一张卡通风格的信息图：

采用手绘风格，横版（16:9）构图。
使用可爱的卡通元素、图标，增强趣味性和视觉记忆。
所有图像必须使用手绘卡通风格，没有写实风格图画元素。
信息精简，突出关键词与核心概念，多留白，易于一眼抓住重点。
如果有敏感人物或者版权内容，画一个相似替代。

输入内容：
{prompt}

图片说明：{caption}
"""
            
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
    
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行配图生成
        
        Args:
            state: 共享状态
            
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
        
        outline = state.get('outline', {})
        sections_outline = outline.get('sections', [])
        
        # 先统计总图片数量
        # 1. 来自大纲的图片数量
        outline_image_count = sum(
            1 for s in sections_outline 
            if s.get('image_type', 'none') != 'none'
        )
        
        # 2. 来自占位符的图片数量
        placeholder_image_count = 0
        for section in sections:
            content = section.get('content', '')
            placeholders = self.extract_image_placeholders(content)
            placeholder_image_count += len(placeholders)
        
        total_image_count = outline_image_count + placeholder_image_count
        
        logger.info(f"开始生成配图 (共 {total_image_count} 张: 大纲 {outline_image_count} + 占位符 {placeholder_image_count})")
        
        images = []
        image_id_counter = 1
        current_progress = 0
        
        # 从大纲中获取配图需求
        for i, section_outline in enumerate(sections_outline):
            image_type = section_outline.get('image_type', 'none')
            if image_type == 'none':
                continue
            
            image_description = section_outline.get('image_description', '')
            section_title = section_outline.get('title', '')
            
            # 获取对应章节的实际内容作为上下文
            section_content = ""
            if i < len(sections):
                section_content = sections[i].get('content', '')[:1000]  # 限制长度
            
            try:
                current_progress += 1
                image = self.generate_image(
                    image_type=image_type,
                    description=image_description,
                    context=f"章节标题: {section_title}\n\n章节内容摘要:\n{section_content}"
                )
                
                image_id = f"img_{image_id_counter}"
                render_method = image.get('render_method', 'mermaid')
                rendered_path = None
                
                # 如果是 ai_image 类型，调用 Nano Banana API 生成图片
                if render_method == 'ai_image':
                    rendered_path = self._render_ai_image(
                        prompt=image.get('content', ''),
                        caption=image.get('caption', '')
                    )
                    if rendered_path:
                        # 转换为相对路径
                        rendered_path = f"./images/{rendered_path.split('/')[-1]}"
                
                image_resource = {
                    "id": image_id,
                    "render_method": render_method,
                    "content": image.get('content', ''),
                    "caption": image.get('caption', ''),
                    "rendered_path": rendered_path
                }
                images.append(image_resource)
                
                # 更新章节的 image_ids
                if i < len(sections):
                    if 'image_ids' not in sections[i]:
                        sections[i]['image_ids'] = []
                    sections[i]['image_ids'].append(image_id)
                
                logger.info(f"配图生成完成 ({current_progress}/{total_image_count}): {image_id} ({image_type}) [来源:大纲:规划阶段]")
                image_id_counter += 1
                
            except Exception as e:
                logger.error(f"配图生成失败 [{section_title}]: {e}")
        
        # 也从章节内容中提取图片占位符
        for section in sections:
            content = section.get('content', '')
            section_title = section.get('title', '')
            
            placeholders = self.extract_image_placeholders(content)
            
            for placeholder in placeholders:
                try:
                    current_progress += 1
                    # 提取占位符周围的上下文（前后各1000字符）
                    placeholder_text = f"[IMAGE: {placeholder['type']} - {placeholder['description']}]"
                    placeholder_pos = content.find(placeholder_text)
                    if placeholder_pos >= 0:
                        start = max(0, placeholder_pos - 1000)
                        end = min(len(content), placeholder_pos + len(placeholder_text) + 1000)
                        surrounding_context = content[start:end]
                    else:
                        surrounding_context = content[:2000]
                    
                    image = self.generate_image(
                        image_type=placeholder['type'],
                        description=placeholder['description'],
                        context=f"章节标题: {section_title}\n\n相关内容:\n{surrounding_context}"
                    )
                    
                    image_id = f"img_{image_id_counter}"
                    render_method = image.get('render_method', 'mermaid')
                    rendered_path = None
                    
                    # 如果是 ai_image 类型，调用 Nano Banana API 生成图片
                    if render_method == 'ai_image':
                        rendered_path = self._render_ai_image(
                            prompt=image.get('content', ''),
                            caption=image.get('caption', '')
                        )
                        if rendered_path:
                            # 转换为相对路径
                            rendered_path = f"./images/{rendered_path.split('/')[-1]}"
                    
                    image_resource = {
                        "id": image_id,
                        "render_method": render_method,
                        "content": image.get('content', ''),
                        "caption": image.get('caption', ''),
                        "rendered_path": rendered_path
                    }
                    images.append(image_resource)
                    
                    # 只有当图片成功生成时，才将其 image_id 添加到章节中
                    if rendered_path:
                        if 'image_ids' not in section:
                            section['image_ids'] = []
                        section['image_ids'].append(image_id)
                        logger.info(f"配图生成完成 ({current_progress}/{total_image_count}): {image_id} ({placeholder['type']}) [来源:占位符:写作阶段]")
                    else:
                        logger.warning(f"配图生成失败 ({current_progress}/{total_image_count}): {image_id} ({placeholder['type']}) - rendered_path 为空")
                    
                    image_id_counter += 1
                    
                except Exception as e:
                    logger.error(f"配图生成失败: {e}")
        
        state['images'] = images
        logger.info(f"配图生成完成: 共 {len(images)} 张图片")
        
        return state
