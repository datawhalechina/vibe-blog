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
                'context': f"章节标题: {section_title}\n\n章节内容摘要:\n{section_content}"
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
                    'context': f"章节标题: {section_title}\n\n相关内容:\n{surrounding_context}"
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
                    context=task['context']
                )
                
                render_method = image.get('render_method', 'mermaid')
                rendered_path = None
                
                # 如果是 ai_image 类型，调用 Nano Banana API 生成图片
                if render_method == 'ai_image':
                    rendered_path = self._render_ai_image(
                        prompt=image.get('content', ''),
                        caption=image.get('caption', '')
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
