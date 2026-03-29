"""
图片生成服务 - 基于 Nano Banana API
"""
import requests
import json
import time
import os
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class AspectRatio(Enum):
    """支持的图像比例"""
    AUTO = "auto"
    SQUARE = "1:1"
    LANDSCAPE_16_9 = "16:9"
    PORTRAIT_9_16 = "9:16"
    LANDSCAPE_4_3 = "4:3"
    PORTRAIT_3_4 = "3:4"
    LANDSCAPE_3_2 = "3:2"
    PORTRAIT_2_3 = "2:3"
    LANDSCAPE_5_4 = "5:4"
    PORTRAIT_4_5 = "4:5"
    ULTRAWIDE_21_9 = "21:9"


class ImageSize(Enum):
    """支持的图像大小"""
    SIZE_1K = "1K"
    SIZE_2K = "2K"
    SIZE_4K = "4K"


class TaskStatus(Enum):
    """任务状态"""
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass
class ImageResult:
    """图片生成结果"""
    url: str
    local_path: Optional[str] = None
    oss_url: Optional[str] = None  # OSS 公网 URL


class NanoBananaService:
    """Nano Banana 图片生成服务"""

    SUPPORTED_MODELS = [
        "nano-banana-fast",
        "nano-banana",
        "nano-banana-pro",
        "nano-banana-pro-vt",
        "nano-banana-pro-cl",
        "nano-banana-pro-vip",
        "nano-banana-pro-4k-vip"
    ]

    def __init__(
        self,
        api_key: str,
        api_base: str = "https://grsai.dakka.com.cn",
        model: str = "nano-banana-pro",
        output_folder: str = "outputs/images"
    ):
        """
        初始化图片生成服务

        Args:
            api_key: API 密钥
            api_base: API 基础 URL
            model: 默认使用的模型
            output_folder: 图片输出目录
        """
        self.api_key = api_key
        self.api_base = api_base.rstrip('/')
        self.model = model
        self.output_folder = output_folder
        
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        })
        
        # 确保输出目录存在
        Path(output_folder).mkdir(parents=True, exist_ok=True)

    def is_available(self) -> bool:
        """检查服务是否可用"""
        return bool(self.api_key)

    def generate(
        self,
        prompt: str,
        aspect_ratio: AspectRatio = AspectRatio.LANDSCAPE_16_9,
        image_size: ImageSize = ImageSize.SIZE_2K,
        model: Optional[str] = None,
        style_prefix: str = "",
        download: bool = True,
        max_wait_time: int = 300,
        max_retries: int = 1
    ) -> Optional[ImageResult]:
        """
        生成图片

        Args:
            prompt: 图片描述
            aspect_ratio: 图片比例
            image_size: 图片大小
            model: 模型名称（可选，默认使用初始化时的模型）
            style_prefix: 风格前缀（会添加到 prompt 前面）
            download: 是否下载到本地
            max_wait_time: 最大等待时间（秒）
            max_retries: 最大重试次数（默认1次）

        Returns:
            ImageResult 或 None
        """
        use_model = model or self.model
        full_prompt = f"{style_prefix}\n\n{prompt}" if style_prefix else prompt
        
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    logger.info(f"图片生成重试 ({attempt}/{max_retries}): {prompt[:50]}...")
                else:
                    logger.info(f"开始生成图片: {prompt[:50]}...")
                
                # 提交任务
                result = self._draw(
                    model=use_model,
                    prompt=full_prompt,
                    aspect_ratio=aspect_ratio,
                    image_size=image_size
                )
                
                # 检查 API 返回的错误码
                if result.get('code') != 0:
                    logger.error(f"API 返回错误: {result}")
                    last_error = f"API 返回错误: {result}"
                    continue
                
                data = result.get('data') or {}
                task_id = data.get('id')
                if not task_id:
                    logger.error(f"未获取到任务ID: {result}")
                    last_error = f"未获取到任务ID: {result}"
                    continue
                
                logger.info(f"任务已提交: {task_id}")
                
                # 等待完成
                final_result = self._wait_for_completion(task_id, max_wait_time)
                
                # 获取图片 URL
                results = final_result.get('data', {}).get('results', [])
                if not results:
                    logger.error("未获取到生成结果")
                    last_error = "未获取到生成结果"
                    continue
                
                image_url = results[0].get('url')
                if not image_url:
                    logger.error("未获取到图片 URL")
                    last_error = "未获取到图片 URL"
                    continue
                
                logger.info(f"图片生成成功: {image_url}")
                
                # 直接上传到 OSS（不经过本地）
                oss_url = None
                if download:
                    upload_result = self._upload_to_oss(image_url)
                    oss_url = upload_result.get('oss_url')
                
                return ImageResult(url=image_url, local_path=None, oss_url=oss_url)
                
            except Exception as e:
                last_error = str(e)
                logger.error(f"图片生成失败 (尝试 {attempt + 1}/{max_retries + 1}): {e}", exc_info=True)
                continue
        
        logger.error(f"图片生成最终失败，已重试 {max_retries} 次: {last_error}")
        return None

    def generate_batch(
        self,
        prompts: List[str],
        aspect_ratio: AspectRatio = AspectRatio.LANDSCAPE_16_9,
        image_size: ImageSize = ImageSize.SIZE_2K,
        style_prefix: str = "",
        download: bool = True
    ) -> List[Optional[ImageResult]]:
        """
        批量生成图片

        Args:
            prompts: 图片描述列表
            aspect_ratio: 图片比例
            image_size: 图片大小
            style_prefix: 风格前缀
            download: 是否下载到本地

        Returns:
            ImageResult 列表
        """
        results = []
        for i, prompt in enumerate(prompts):
            logger.info(f"生成第 {i+1}/{len(prompts)} 张图片")
            result = self.generate(
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                image_size=image_size,
                style_prefix=style_prefix,
                download=download
            )
            results.append(result)
        return results

    def _draw(
        self,
        model: str,
        prompt: str,
        aspect_ratio: AspectRatio = AspectRatio.AUTO,
        image_size: ImageSize = ImageSize.SIZE_1K,
        urls: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """调用绘画接口"""
        if model not in self.SUPPORTED_MODELS:
            raise ValueError(f"不支持的模型: {model}. 支持的模型: {self.SUPPORTED_MODELS}")

        request_body = {
            "model": model,
            "prompt": prompt,
            "aspectRatio": aspect_ratio.value,
            "imageSize": image_size.value,
            "shutProgress": False,
            "webHook": "-1"  # 使用轮询方式
        }

        if urls:
            request_body["urls"] = urls

        url = f"{self.api_base}/v1/draw/nano-banana"
        try:
            response = self.session.post(url, json=request_body, timeout=30)
            response.raise_for_status()
            result = response.json()
            if result is None:
                logger.error(f"API 返回空响应")
                return {}
            return result
        except requests.exceptions.Timeout:
            logger.error(f"API 请求超时: {url}")
            return {}
        except requests.exceptions.RequestException as e:
            logger.error(f"API 请求失败: {e}")
            return {}

    def _get_result(self, task_id: str) -> Dict[str, Any]:
        """获取任务结果"""
        url = f"{self.api_base}/v1/draw/result"
        response = self.session.post(url, json={"id": task_id})
        response.raise_for_status()
        return response.json()

    def _wait_for_completion(
        self,
        task_id: str,
        max_wait_time: int = 300,
        poll_interval: int = 2
    ) -> Dict[str, Any]:
        """等待任务完成"""
        start_time = time.time()
        last_progress = -1

        while True:
            elapsed = time.time() - start_time
            if elapsed > max_wait_time:
                raise TimeoutError(f"任务等待超时 (超过 {max_wait_time} 秒)")

            result = self._get_result(task_id)

            if result.get('code') == 0:
                data = result.get('data', {})
                status = data.get('status')
                progress = data.get('progress', 0)

                if progress != last_progress:
                    logger.info(f"任务进度: {progress}%")
                    last_progress = progress

                if status == TaskStatus.SUCCEEDED.value:
                    return result
                elif status == TaskStatus.FAILED.value:
                    raise RuntimeError(
                        f"任务失败: {data.get('failure_reason')} - {data.get('error')}"
                    )

            time.sleep(poll_interval)

    def _upload_to_oss(self, image_url: str) -> dict:
        """
        直接将图片 URL 上传到 OSS（不经过本地文件）
        
        Returns:
            {'oss_url': str or None}
        """
        from .oss_service import get_oss_service
        oss_service = get_oss_service()
        
        if oss_service and oss_service.is_available:
            oss_result = oss_service.upload_image_from_url(image_url)
            if oss_result.get('success'):
                oss_url = oss_result.get('url')
                logger.info(f"图片已直接上传到 OSS: {oss_url}")
                return {'oss_url': oss_url}
            else:
                logger.warning(f"图片上传 OSS 失败: {oss_result.get('error')}")
        
        # OSS 不可用或上传失败
        return {'oss_url': None}


# 全局服务实例
_image_service: Optional[NanoBananaService] = None


def get_image_service() -> Optional[NanoBananaService]:
    """获取全局图片生成服务实例"""
    return _image_service


def init_image_service(config: dict) -> Optional[NanoBananaService]:
    """
    从配置初始化图片生成服务

    Args:
        config: Flask app.config 字典

    Returns:
        NanoBananaService 实例或 None
    """
    global _image_service
    
    api_key = config.get('NANO_BANANA_API_KEY', '')
    if not api_key:
        logger.warning("未配置 NANO_BANANA_API_KEY，图片生成服务不可用")
        return None
    
    _image_service = NanoBananaService(
        api_key=api_key,
        api_base=config.get('NANO_BANANA_API_BASE', 'https://grsai.dakka.com.cn'),
        model=config.get('NANO_BANANA_MODEL', 'nano-banana-pro'),
        output_folder=config.get('IMAGE_OUTPUT_FOLDER', 'outputs/images')
    )
    
    logger.info(f"图片生成服务已初始化: model={_image_service.model}")
    return _image_service


# 科普绘本风格 Prompt 模板
STORYBOOK_STYLE_PREFIX = """请生成一张卡通风格的信息图：

采用可爱的手绘卡通风格，色彩明亮温暖。
使用简洁的卡通元素、图标，增强趣味性和视觉记忆。
所有图像必须使用手绘卡通风格，没有写实风格图画元素。
信息精简，突出关键词与核心概念，多留白，易于一眼抓住重点。
如果有敏感人物或者版权内容，画一个相似替代。

【图片内容】：
"""
