"""
图片分析器 - 多模态图片理解

复用 vibe-blog 的多模态接入方式:
- 配置: IMAGE_CAPTION_MODEL=qwen3-vl-plus-2025-12-19
- 接口: llm_service.chat_with_image()
"""
import os
import base64
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ImageAnalysisResult:
    """图片分析结果"""
    description: str            # 图片内容描述
    detected_text: Optional[str]  # OCR 检测到的文字
    image_type: str             # screenshot|diagram|chart|photo|code|other
    relevance_score: float      # 与上下文的相关性 0-1
    quality_score: int          # 图片质量得分 0-100


class ImageAnalyzer:
    """
    图片分析器
    
    复用 vibe-blog 的多模态模型接入
    """
    
    # 图片类型映射
    IMAGE_TYPES = {
        'screenshot': '截图',
        'diagram': '图表/流程图',
        'chart': '数据图表',
        'photo': '照片',
        'code': '代码截图',
        'other': '其他',
    }
    
    def __init__(self, llm_service=None):
        """
        初始化图片分析器
        
        Args:
            llm_service: LLM 服务实例 (需支持 chat_with_image)
        """
        self.llm_service = llm_service
    
    def analyze_image(
        self, 
        image_path: str, 
        context: str = None
    ) -> Optional[ImageAnalysisResult]:
        """
        分析单张图片
        
        Args:
            image_path: 图片路径
            context: 上下文信息 (图片周围的文本)
            
        Returns:
            分析结果
        """
        if not self.llm_service:
            logger.warning("LLM 服务不可用，跳过图片分析")
            return None
        
        if not os.path.exists(image_path):
            logger.warning(f"图片不存在: {image_path}")
            return None
        
        try:
            # 读取图片并转为 base64
            with open(image_path, 'rb') as f:
                img_data = f.read()
            img_base64 = base64.b64encode(img_data).decode('utf-8')
            
            # 确定 MIME 类型
            ext = os.path.splitext(image_path)[1].lower()
            mime_map = {
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.gif': 'image/gif',
                '.webp': 'image/webp',
            }
            mime_type = mime_map.get(ext, 'image/jpeg')
            
            # 构建分析 Prompt
            prompt = self._build_analysis_prompt(context)
            
            # 调用多模态模型
            if hasattr(self.llm_service, 'chat_with_image'):
                response = self.llm_service.chat_with_image(prompt, img_base64, mime_type)
            else:
                logger.warning("LLM 服务不支持 chat_with_image")
                return None
            
            if not response:
                return None
            
            # 解析响应
            return self._parse_response(response)
            
        except Exception as e:
            logger.error(f"图片分析失败: {image_path}, 错误: {e}")
            return None
    
    def _build_analysis_prompt(self, context: str = None) -> str:
        """构建分析 Prompt"""
        prompt = """请分析这张图片，并以 JSON 格式返回以下信息：

1. description: 图片内容的详细描述（100-200字）
2. detected_text: 图片中检测到的文字（如果有）
3. image_type: 图片类型，从以下选项中选择：
   - screenshot: 软件/网页截图
   - diagram: 图表/流程图/架构图
   - chart: 数据图表（柱状图、折线图等）
   - photo: 照片
   - code: 代码截图
   - other: 其他
4. quality_score: 图片质量评分（0-100）
   - 考虑清晰度、完整性、信息量

"""
        if context:
            prompt += f"""
5. relevance_score: 与以下上下文的相关性（0-1）

上下文：
{context[:500]}

"""
        else:
            prompt += "5. relevance_score: 设为 0.5（无上下文）\n"
        
        prompt += """
请直接返回 JSON，不要包含其他内容：
{"description": "...", "detected_text": "...", "image_type": "...", "quality_score": 80, "relevance_score": 0.8}
"""
        return prompt
    
    def _parse_response(self, response: str) -> Optional[ImageAnalysisResult]:
        """解析模型响应"""
        import json
        
        try:
            # 尝试提取 JSON
            response = response.strip()
            if response.startswith('```'):
                # 移除代码块标记
                lines = response.split('\n')
                response = '\n'.join(lines[1:-1])
            
            data = json.loads(response)
            
            return ImageAnalysisResult(
                description=data.get('description', ''),
                detected_text=data.get('detected_text'),
                image_type=data.get('image_type', 'other'),
                relevance_score=float(data.get('relevance_score', 0.5)),
                quality_score=int(data.get('quality_score', 50)),
            )
            
        except json.JSONDecodeError:
            # 如果无法解析 JSON，尝试提取关键信息
            logger.warning("无法解析 JSON 响应，使用默认值")
            return ImageAnalysisResult(
                description=response[:200] if response else '',
                detected_text=None,
                image_type='other',
                relevance_score=0.5,
                quality_score=50,
            )
    
    def analyze_images_batch(
        self, 
        image_paths: List[str], 
        contexts: List[str] = None,
        max_images: int = 10
    ) -> List[Optional[ImageAnalysisResult]]:
        """
        批量分析图片
        
        Args:
            image_paths: 图片路径列表
            contexts: 对应的上下文列表
            max_images: 最多分析的图片数量
            
        Returns:
            分析结果列表
        """
        results = []
        
        for i, path in enumerate(image_paths[:max_images]):
            context = contexts[i] if contexts and i < len(contexts) else None
            result = self.analyze_image(path, context)
            results.append(result)
        
        # 超过限制的图片返回 None
        for _ in range(len(image_paths) - max_images):
            results.append(None)
        
        return results
