"""
转化流水线服务 - 管理完整的内容转化流程
支持 SSE 实时进度推送
"""
import json
import logging
import re
import time
from threading import Thread
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class PipelineService:
    """转化流水线服务"""
    
    def __init__(
        self,
        llm_service,
        image_service=None,
        task_manager=None
    ):
        self.llm_service = llm_service
        self.image_service = image_service
        self.task_manager = task_manager
    
    def run_pipeline(
        self,
        task_id: str,
        content: str,
        title: str = "",
        target_audience: str = "技术小白",
        style: str = "可爱卡通风",
        page_count: int = 8,
        generate_images: bool = False,
        aspect_ratio: str = "16:9"  # 新增：接收宽高比参数
    ) -> Dict[str, Any]:
        """运行完整的转化流水线"""
        tm = self.task_manager
        
        try:
            tm.set_running(task_id)
            
            # 阶段 1: 内容分析
            tm.send_progress(task_id, 'analyze', 10, '📝 正在分析技术内容...')
            time.sleep(0.3)
            
            tech_concepts = self._extract_tech_concepts(content)
            
            tm.send_progress(task_id, 'analyze', 100, f'✅ 内容分析完成，识别到 {len(tech_concepts)} 个技术概念')
            tm.send_result(task_id, 'analyze', 'concepts', {'concepts': tech_concepts})
            
            # 阶段 2: 比喻生成
            tm.send_progress(task_id, 'metaphor', 10, '💡 正在为技术概念寻找生活化比喻...')
            
            metaphors = self._find_metaphors(tech_concepts)
            metaphor_list = [f"{k} -> {v[0]}" for k, v in metaphors.items()]
            
            tm.send_progress(task_id, 'metaphor', 100, f'✅ 比喻生成完成，找到 {len(metaphors)} 个比喻')
            tm.send_result(task_id, 'metaphor', 'metaphors', {'metaphors': metaphor_list})
            
            # 阶段 3: 大纲生成
            tm.send_progress(task_id, 'outline', 10, '📋 正在生成科普绘本大纲...')
            
            outline_result = self._generate_outline_streaming(
                task_id, content, title, tech_concepts, metaphors,
                target_audience, style, page_count
            )
            
            if not outline_result:
                tm.send_error(task_id, 'outline', '大纲生成失败', recoverable=False)
                return {'success': False, 'error': '大纲生成失败'}
            
            # 检查 pages 是否存在
            if not outline_result.get('pages'):
                logger.warning(f"大纲中没有 pages 字段，outline_result: {outline_result}")
                tm.send_error(task_id, 'outline', '大纲生成失败：没有生成页面内容', recoverable=False)
                return {'success': False, 'error': '大纲生成失败：没有生成页面内容'}
            
            tm.send_progress(task_id, 'outline', 100, '✅ 大纲生成完成')
            tm.send_result(task_id, 'outline', 'outline_complete', {
                'title': outline_result.get('title'),
                'page_count': len(outline_result.get('pages', []))
            })
            
            # 阶段 4: 内容生成
            pages = outline_result.get('pages', [])
            total_pages = len(pages)
            
            tm.send_progress(task_id, 'content', 10, f'📖 正在生成 {total_pages} 页内容...')
            
            for i, page in enumerate(pages):
                progress = 10 + int((i + 1) / total_pages * 80)
                tm.send_progress(
                    task_id, 'content', progress,
                    f'📖 第 {page.get("page_number", i+1)} 页: {page.get("title", "")[:20]}...',
                    current=i+1, total=total_pages
                )
                tm.send_result(task_id, 'content', 'page_content', {
                    'page_number': page.get('page_number', i+1),
                    'title': page.get('title'),
                    'content': page.get('content'),
                    'metaphor': page.get('metaphor'),
                    'tech_point': page.get('tech_point', ''),
                    'real_world_example': page.get('real_world_example', ''),
                    'key_takeaway': page.get('key_takeaway', ''),
                    'image_description': page.get('image_description')
                })
                time.sleep(0.2)
            
            tm.send_progress(task_id, 'content', 100, f'✅ {total_pages} 页内容生成完成')
            
            # 阶段 5: 图片生成 - 每5页生成一张配图
            if self.image_service and self.image_service.is_available() and len(pages) > 0:
                # 计算需要生成配图的页面（每5页一张，至少第1页有图）
                image_pages = [i for i in range(len(pages)) if i % 5 == 0]
                
                total_images = len(image_pages)
                if total_images == 0:
                    logger.info("没有需要生成配图的页面")
                else:
                    tm.send_progress(task_id, 'image', 10, f'🎨 正在生成 {total_images} 张配图（每5页1张）...')
                
                for idx, page_idx in enumerate(image_pages):
                    if page_idx >= len(pages):
                        logger.warning(f"页面索引 {page_idx} 超出范围，跳过")
                        continue
                    page = pages[page_idx]
                    image_desc = page.get('image_description', '')
                    if image_desc:
                        progress = 10 + int((idx + 1) / total_images * 80)
                        tm.send_progress(
                            task_id, 'image', progress,
                            f'🎨 正在生成第 {page.get("page_number", page_idx+1)} 页配图 ({idx+1}/{total_images})...',
                            current=idx+1, total=total_images
                        )
                        
                        try:
                            from services.media import AspectRatio, ImageSize, STORYBOOK_STYLE_PREFIX
                            # 第一页使用前端选择的宽高比，其他页保持 16:9
                            if page_idx == 0:
                                selected_aspect_ratio = AspectRatio.PORTRAIT_9_16 if aspect_ratio == "9:16" else AspectRatio.LANDSCAPE_16_9
                            else:
                                selected_aspect_ratio = AspectRatio.LANDSCAPE_16_9
                            
                            image_result = self.image_service.generate(
                                prompt=image_desc,
                                aspect_ratio=selected_aspect_ratio,
                                image_size=ImageSize.SIZE_2K,
                                style_prefix=STORYBOOK_STYLE_PREFIX,
                                download=True
                            )
                            
                            if image_result:
                                page['image_url'] = image_result.url
                                page['image_local_path'] = image_result.local_path
                                
                                tm.send_result(task_id, 'image', 'page_image', {
                                    'page_number': page.get('page_number', page_idx+1),
                                    'image_url': image_result.url
                                })
                        except Exception as e:
                            logger.warning(f"第 {page_idx+1} 页图片生成失败: {e}")
                            tm.send_error(task_id, 'image', f'第 {page_idx+1} 页图片生成失败', recoverable=True)
                
                tm.send_progress(task_id, 'image', 100, f'✅ {total_images} 张配图生成完成')
            
            # 完成
            outputs = {
                'title': outline_result.get('title'),
                'subtitle': outline_result.get('subtitle'),
                'core_metaphor': outline_result.get('core_metaphor'),
                'total_pages': len(pages),
                'pages': pages,
                'style': style,
                'target_audience': target_audience
            }
            
            tm.send_complete(task_id, outputs)
            
            return {'success': True, 'result': outputs}
            
        except Exception as e:
            logger.exception(f"流水线执行失败: {e}")
            tm.send_error(task_id, 'unknown', str(e), recoverable=False)
            return {'success': False, 'error': str(e)}
    
    def run_pipeline_async(self, task_id, content, title="", target_audience="技术小白",
                          style="可爱卡通风", page_count=8, generate_images=False, aspect_ratio="16:9", app=None):
        """异步运行流水线"""
        def _run():
            if app:
                with app.app_context():
                    self.run_pipeline(task_id, content, title, target_audience, style, page_count, generate_images, aspect_ratio)
            else:
                self.run_pipeline(task_id, content, title, target_audience, style, page_count, generate_images, aspect_ratio)
        
        thread = Thread(target=_run, daemon=True)
        thread.start()
        return thread
    
    def _extract_tech_concepts(self, content: str) -> list:
        """提取技术概念"""
        from services.transform_service import TransformService
        concepts = []
        content_lower = content.lower()
        for keyword in TransformService.METAPHOR_LIBRARY.keys():
            if keyword in content_lower:
                concepts.append(keyword)
        return concepts[:5]
    
    def _find_metaphors(self, concepts: list) -> dict:
        """查找比喻"""
        from services.transform_service import TransformService
        metaphors = {}
        for concept in concepts:
            concept_lower = concept.lower()
            if concept_lower in TransformService.METAPHOR_LIBRARY:
                metaphors[concept] = TransformService.METAPHOR_LIBRARY[concept_lower]
        return metaphors
    
    def _generate_outline_streaming(self, task_id, content, title, tech_concepts, metaphors,
                                    target_audience, style, page_count) -> Optional[Dict[str, Any]]:
        """流式生成大纲"""
        tm = self.task_manager
        
        metaphor_hints = ""
        if metaphors:
            metaphor_hints = "\n可用的比喻参考：\n"
            for concept, (metaphor, explanation) in metaphors.items():
                metaphor_hints += f"- {concept} -> {metaphor}: {explanation}\n"
        
        system_prompt = """你是一个技术科普专家，擅长用生活化的比喻把复杂技术讲得通俗易懂。

## 核心原则

1. **比喻必须结合技术点**：不能只讲比喻，要在比喻中穿插技术概念的解释
2. **内容要丰富详实**：每页 200-300 字，包含比喻场景 + 技术原理 + 实际应用
3. **循序渐进**：从简单到复杂，每页都要有新的知识点
4. **技术准确**：比喻要准确映射技术概念，不能误导读者

## 每页内容结构

1. **场景引入**（50字）：用生活场景引出话题
2. **比喻讲解**（100字）：用比喻解释技术概念
3. **技术揭秘**（80字）：揭示比喻背后的真实技术原理
4. **实战提示**（50字）：给出实际应用建议或注意事项

## 输出 JSON 格式

{
  "title": "标题（有趣且能体现技术主题）",
  "subtitle": "副标题（用比喻概括核心内容）",
  "core_metaphor": "核心比喻（一句话说明整体类比）",
  "pages": [
    {
      "page_number": 1,
      "title": "页面标题（简短有趣）",
      "content": "页面正文（200-300字，包含比喻+技术讲解+应用提示）",
      "metaphor": "本页使用的比喻",
      "tech_point": "本页核心技术点（用专业术语）",
      "real_world_example": "真实应用场景举例",
      "image_description": "配图描述（具体、可视化）",
      "key_takeaway": "本页要点总结（一句话）",
      "mapping": {"比喻元素": "技术概念"}
    }
  ]
}"""

        user_prompt = f"""请将以下技术博客转化为{page_count}页的技术科普绘本。

目标读者：{target_audience}
视觉风格：{style}
{metaphor_hints}

## 原始技术内容

{content}

## 重要要求

1. 必须生成完整的 {page_count} 页内容，pages 数组不能为空
2. 每页都要有完整的 page_number, title, content, metaphor, tech_point, image_description 等字段
3. 直接输出 JSON，不要有任何思考过程或解释

请输出完整的 JSON 格式科普绘本内容（确保 pages 数组包含 {page_count} 个页面对象）："""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        accumulated = ""
        
        def on_chunk(delta, acc):
            nonlocal accumulated
            accumulated = acc
            tm.send_stream(task_id, 'outline', delta, acc)
        
        if hasattr(self.llm_service, 'chat_stream'):
            response = self.llm_service.chat_stream(messages=messages, temperature=0.7, on_chunk=on_chunk)
        else:
            response = self.llm_service.chat(messages=messages, temperature=0.7)
        
        if not response:
            return None
        
        return self._parse_json_response(response)
    
    def _parse_json_response(self, response: str) -> Optional[Dict[str, Any]]:
        """解析 JSON 响应"""
        if not response:
            logger.error("LLM 响应为空")
            return None
        
        logger.info(f"LLM 响应长度: {len(response)} 字符")
        
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
        if json_match:
            json_str = json_match.group(1)
            logger.info("从 markdown 代码块中提取 JSON")
        else:
            json_str = response.strip()
            # 尝试找到 JSON 对象的开始和结束
            start_idx = json_str.find('{')
            if start_idx >= 0:
                # 找到最后一个匹配的 }
                brace_count = 0
                end_idx = -1
                for i, c in enumerate(json_str[start_idx:], start_idx):
                    if c == '{':
                        brace_count += 1
                    elif c == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_idx = i
                            break
                if end_idx > start_idx:
                    json_str = json_str[start_idx:end_idx + 1]
                    logger.info(f"提取 JSON 对象: {start_idx} - {end_idx}")
        
        try:
            result = json.loads(json_str)
            logger.info(f"JSON 解析成功，包含 {len(result.get('pages', []))} 页")
            return result
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {e}")
            logger.error(f"JSON 字符串前 500 字符: {json_str[:500]}")
            return None


def create_pipeline_service(llm_service, image_service=None, task_manager=None):
    """创建流水线服务实例"""
    return PipelineService(llm_service, image_service, task_manager)
