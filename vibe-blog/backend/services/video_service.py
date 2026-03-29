"""
视频生成服务 - 统一入口
支持多种视频生成模型：Veo3, Sora2
通过模型名称自动路由到对应的服务
"""
import requests
import time
import os
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class VideoAspectRatio(Enum):
    """支持的视频比例"""
    LANDSCAPE_16_9 = "16:9"
    PORTRAIT_9_16 = "9:16"


class VideoStatus(Enum):
    """任务状态"""
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass
class VideoResult:
    """视频生成结果"""
    url: str
    local_path: Optional[str] = None
    task_id: Optional[str] = None
    oss_url: Optional[str] = None  # OSS 公网 URL
    pid: Optional[str] = None  # Sora2 视频 ID，用于续创作


class Veo3Service:
    """Veo3 视频生成服务"""

    SUPPORTED_MODELS = [
        "veo3.1-fast",
        "veo3.1-pro"
    ]

    @staticmethod
    def get_default_animation_prompt() -> str:
        """获取默认动画提示词（从 Jinja2 模板加载）"""
        from services.blog_generator.prompts import get_prompt_manager
        return get_prompt_manager().render_cover_video_prompt()

    def __init__(
        self,
        api_key: str,
        api_base: str = "https://grsai.dakka.com.cn",
        model: str = "veo3.1-fast",
        output_folder: str = "outputs/videos"
    ):
        """
        初始化视频生成服务

        Args:
            api_key: API 密钥
            api_base: API 基础 URL
            model: 默认使用的模型
            output_folder: 视频输出目录
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

    def generate_from_image(
        self,
        image_url: str,
        prompt: Optional[str] = None,
        aspect_ratio: VideoAspectRatio = VideoAspectRatio.LANDSCAPE_16_9,
        model: Optional[str] = None,
        download: bool = True,
        max_wait_time: int = 600,
        progress_callback: callable = None,
        max_retries: int = 1
    ) -> Optional[VideoResult]:
        """
        从图片生成动画视频

        Args:
            image_url: 首帧图片 URL
            prompt: 动画提示词（可选，默认使用信息图动画提示词）
            aspect_ratio: 视频比例
            model: 模型名称（可选）
            download: 是否下载到本地
            max_wait_time: 最大等待时间（秒）
            progress_callback: 进度回调函数 callback(progress: int, status: str)
            max_retries: 最大重试次数（默认1次）

        Returns:
            VideoResult 或 None
        """
        use_model = model or self.model
        use_prompt = prompt or self.get_default_animation_prompt()
        
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    logger.info(f"视频生成重试 ({attempt}/{max_retries}): {image_url[:50]}...")
                else:
                    logger.info(f"开始生成视频: {image_url[:80]}...")
                
                # 提交任务
                result = self._create_video_task(
                    model=use_model,
                    prompt=use_prompt,
                    first_frame_url=image_url,
                    aspect_ratio=aspect_ratio
                )
                
                # 检查 API 返回
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
                
                logger.info(f"视频任务已提交: {task_id}")
                
                # 等待完成
                final_result = self._wait_for_completion(
                    task_id, 
                    max_wait_time,
                    progress_callback=progress_callback
                )
                
                # 获取视频 URL
                video_data = final_result.get('data', {})
                video_url = video_data.get('url')
                if not video_url:
                    logger.error("未获取到视频 URL")
                    last_error = "未获取到视频 URL"
                    continue
                
                logger.info(f"视频生成成功: {video_url}")
                
                # 直接上传到 OSS（不经过本地）
                oss_url = None
                if download:
                    upload_result = self._upload_to_oss(video_url)
                    oss_url = upload_result.get('oss_url')
                
                return VideoResult(
                    url=video_url,
                    local_path=None,
                    task_id=task_id,
                    oss_url=oss_url
                )
                
            except Exception as e:
                last_error = str(e)
                logger.error(f"视频生成失败 (尝试 {attempt + 1}/{max_retries + 1}): {e}", exc_info=True)
                continue
        
        logger.error(f"视频生成最终失败，已重试 {max_retries} 次: {last_error}")
        return None

    def _create_video_task(
        self,
        model: str,
        prompt: str,
        first_frame_url: str,
        aspect_ratio: VideoAspectRatio = VideoAspectRatio.LANDSCAPE_16_9
    ) -> Dict[str, Any]:
        """创建视频生成任务"""
        if model not in self.SUPPORTED_MODELS:
            raise ValueError(f"不支持的模型: {model}. 支持的模型: {self.SUPPORTED_MODELS}")

        request_body = {
            "model": model,
            "prompt": prompt,
            "firstFrameUrl": first_frame_url,
            "aspectRatio": aspect_ratio.value,
            "webHook": "-1",  # 使用轮询方式
            "shutProgress": False
        }

        url = f"{self.api_base}/v1/video/veo"
        try:
            response = self.session.post(url, json=request_body, timeout=30)
            response.raise_for_status()
            result = response.json()
            if result is None:
                logger.error("API 返回空响应")
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
        max_wait_time: int = 600,
        poll_interval: int = 5,
        progress_callback: callable = None
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
                    logger.info(f"视频任务进度: {progress}%")
                    last_progress = progress
                    
                    # 调用进度回调
                    if progress_callback:
                        try:
                            progress_callback(progress, status)
                        except Exception as e:
                            logger.warning(f"进度回调失败: {e}")

                if status == VideoStatus.SUCCEEDED.value:
                    return result
                elif status == VideoStatus.FAILED.value:
                    raise RuntimeError(
                        f"视频任务失败: {data.get('failure_reason')} - {data.get('error')}"
                    )
            elif result.get('code') == -22:
                raise RuntimeError(f"任务不存在: {task_id}")

            time.sleep(poll_interval)

    def _upload_to_oss(self, video_url: str) -> dict:
        """
        直接将视频 URL 上传到 OSS（不经过本地文件）
        
        Returns:
            {'oss_url': str or None}
        """
        from .oss_service import get_oss_service
        oss_service = get_oss_service()
        
        if oss_service and oss_service.is_available:
            oss_result = oss_service.upload_video_from_url(video_url)
            if oss_result.get('success'):
                oss_url = oss_result.get('url')
                logger.info(f"视频已直接上传到 OSS: {oss_url}")
                return {'oss_url': oss_url}
            else:
                logger.warning(f"视频上传 OSS 失败: {oss_result.get('error')}")
        
        # OSS 不可用或上传失败
        return {'oss_url': None}


class UnifiedVideoService:
    """
    统一视频生成服务
    
    通过模型名称自动路由到对应的服务：
    - sora2, sora-2 -> Sora2Service
    - veo3, veo3.1-fast, veo3.1-pro -> Veo3Service
    """
    
    # 模型名称映射
    SORA2_MODELS = ['sora2', 'sora-2']
    VEO3_MODELS = ['veo3', 'veo3.1-fast', 'veo3.1-pro']
    
    def __init__(self, veo3_service: Optional[Veo3Service] = None, sora2_service=None):
        self.veo3_service = veo3_service
        self.sora2_service = sora2_service
        self._default_model = 'veo3'  # 默认使用 Veo3
        
        logger.info(f"UnifiedVideoService 初始化: veo3={veo3_service is not None}, sora2={sora2_service is not None}")
    
    def is_available(self, model: Optional[str] = None) -> bool:
        """检查服务是否可用"""
        if model:
            service = self._get_service_for_model(model)
            return service is not None and service.is_available()
        # 任一服务可用即可
        return (self.veo3_service and self.veo3_service.is_available()) or \
               (self.sora2_service and self.sora2_service.is_available())
    
    def _get_service_for_model(self, model: str):
        """根据模型名称获取对应的服务"""
        model_lower = model.lower()
        
        if model_lower in self.SORA2_MODELS:
            return self.sora2_service
        elif model_lower in self.VEO3_MODELS:
            return self.veo3_service
        else:
            # 默认使用 Veo3
            logger.warning(f"未知模型: {model}，使用默认 Veo3")
            return self.veo3_service
    
    def _get_model_name(self, model: str) -> str:
        """获取模型显示名称"""
        model_lower = model.lower()
        if model_lower in self.SORA2_MODELS:
            return "Sora2"
        elif model_lower in self.VEO3_MODELS:
            return "Veo3"
        return model
    
    def generate_from_image(
        self,
        image_url: str,
        prompt: Optional[str] = None,
        aspect_ratio: VideoAspectRatio = VideoAspectRatio.PORTRAIT_9_16,
        model: Optional[str] = None,
        download: bool = True,
        max_wait_time: int = 600,
        progress_callback: callable = None,
        max_retries: int = 1,
        remix_target_id: Optional[str] = None  # Sora2 续创作：上一个视频的 pid
    ) -> Optional[VideoResult]:
        """
        从图片生成动画视频（统一入口）

        Args:
            image_url: 首帧图片 URL
            prompt: 动画提示词
            aspect_ratio: 视频比例
            model: 模型名称（sora2/veo3/veo3.1-fast/veo3.1-pro）
            download: 是否上传到 OSS
            max_wait_time: 最大等待时间
            progress_callback: 进度回调
            max_retries: 最大重试次数
            remix_target_id: Sora2 续创作的目标视频 pid（可选）

        Returns:
            VideoResult 或 None（包含 pid 用于下一次续创作）
        """
        use_model = model or self._default_model
        service = self._get_service_for_model(use_model)
        model_name = self._get_model_name(use_model)
        
        if not service or not service.is_available():
            logger.error(f"[{model_name}] 服务不可用")
            return None
        
        if remix_target_id:
            logger.info(f"[{model_name}] 续创作模式: {image_url[:50]}... (基于 pid={remix_target_id})")
        else:
            logger.info(f"[{model_name}] 开始生成视频: {image_url[:50]}...")
        
        # 构建调用参数
        kwargs = {
            'image_url': image_url,
            'prompt': prompt,
            'aspect_ratio': aspect_ratio,
            'max_wait_time': max_wait_time,
            'progress_callback': progress_callback,
            'max_retries': max_retries
        }
        
        # Sora2 支持续创作
        if remix_target_id and use_model.lower() in self.SORA2_MODELS:
            kwargs['remix_target_id'] = remix_target_id
        
        logger.info(f"[{model_name}] 视频参数: aspect_ratio={aspect_ratio.value}")
        
        # 调用对应服务的 generate_from_image
        result = service.generate_from_image(**kwargs)
        
        if result:
            # 统一返回 VideoResult 格式
            return VideoResult(
                url=result.url,
                local_path=getattr(result, 'local_path', None),
                task_id=getattr(result, 'task_id', None),
                oss_url=getattr(result, 'oss_url', None),
                pid=getattr(result, 'pid', None)  # 保留 pid 用于续创作
            )
        
        return None
    
    @staticmethod
    def get_supported_models() -> dict:
        """获取支持的模型列表"""
        return {
            'sora2': {
                'name': 'Sora2',
                'description': 'OpenAI Sora2，支持 10-15 秒视频，角色系统，视频续作',
                'duration': [10, 15],
                'recommended': True
            },
            'veo3': {
                'name': 'Veo3',
                'description': 'Google Veo3，支持 5-8 秒视频',
                'duration': [5, 8],
                'recommended': False
            }
        }


# 全局服务实例
_veo3_service: Optional[Veo3Service] = None
_unified_video_service: Optional[UnifiedVideoService] = None


def get_video_service() -> Optional[UnifiedVideoService]:
    """获取统一视频生成服务实例"""
    return _unified_video_service


def get_veo3_service() -> Optional[Veo3Service]:
    """获取 Veo3 服务实例（向后兼容）"""
    return _veo3_service


def init_video_service(config: dict) -> Optional[UnifiedVideoService]:
    """
    从配置初始化视频生成服务

    Args:
        config: Flask app.config 字典

    Returns:
        UnifiedVideoService 实例或 None
    """
    global _veo3_service, _unified_video_service
    
    api_key = config.get('NANO_BANANA_API_KEY', '')
    if not api_key:
        logger.warning("未配置 NANO_BANANA_API_KEY，视频生成服务不可用")
        return None
    
    # 视频输出目录
    output_folder = config.get('VIDEO_OUTPUT_FOLDER', '')
    if not output_folder:
        base_output = config.get('OUTPUT_FOLDER', 'outputs')
        output_folder = os.path.join(base_output, 'videos')
    
    # 初始化 Veo3 服务
    _veo3_service = Veo3Service(
        api_key=api_key,
        api_base=config.get('NANO_BANANA_API_BASE', 'https://grsai.dakka.com.cn'),
        model=config.get('VEO3_MODEL', 'veo3.1-fast'),
        output_folder=output_folder
    )
    
    # 初始化 Sora2 服务
    from services.sora2_service import Sora2Service
    sora2_service = Sora2Service(
        api_key=api_key,
        api_base=config.get('NANO_BANANA_API_BASE', 'https://grsai.dakka.com.cn'),
        default_duration=config.get('SORA2_DURATION', 10),
        default_size=config.get('SORA2_SIZE', 'small')
    )
    
    # 创建统一服务
    _unified_video_service = UnifiedVideoService(
        veo3_service=_veo3_service,
        sora2_service=sora2_service
    )
    
    logger.info("统一视频生成服务已初始化: Veo3 + Sora2")
    return _unified_video_service
