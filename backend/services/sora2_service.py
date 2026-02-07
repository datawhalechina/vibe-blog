"""
Sora2 视频生成服务
支持角色系统和视频续作
"""
import requests
import time
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class Sora2AspectRatio(Enum):
    """Sora2 支持的视频比例"""
    LANDSCAPE_16_9 = "16:9"
    PORTRAIT_9_16 = "9:16"


class Sora2Duration(Enum):
    """Sora2 支持的视频时长"""
    SHORT_10 = 10
    LONG_15 = 15


class Sora2Size(Enum):
    """Sora2 支持的清晰度"""
    SMALL = "small"
    LARGE = "large"


class VideoStatus(Enum):
    """任务状态"""
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass
class Sora2VideoResult:
    """Sora2 视频生成结果"""
    url: str
    pid: Optional[str] = None  # 用于视频续作
    task_id: Optional[str] = None
    oss_url: Optional[str] = None
    remove_watermark: bool = False


@dataclass
class Sora2CharacterResult:
    """Sora2 角色创建结果"""
    character_id: str
    task_id: Optional[str] = None


class Sora2Service:
    """Sora2 视频生成服务"""

    def __init__(
        self,
        api_key: str,
        api_base: str = "https://grsai.dakka.com.cn",
        default_duration: int = 10,
        default_size: str = "small"
    ):
        """
        初始化 Sora2 服务

        Args:
            api_key: API 密钥
            api_base: API 基础 URL
            default_duration: 默认视频时长（10 或 15 秒）
            default_size: 默认清晰度（small 或 large）
        """
        self.api_key = api_key
        self.api_base = api_base.rstrip('/')
        self.default_duration = default_duration
        self.default_size = default_size
        
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        })
        
        logger.info(f"Sora2Service 初始化完成: duration={default_duration}s, size={default_size}")

    def is_available(self) -> bool:
        """检查服务是否可用"""
        return bool(self.api_key)

    def generate_video(
        self,
        prompt: str,
        image_url: Optional[str] = None,
        aspect_ratio: Sora2AspectRatio = Sora2AspectRatio.PORTRAIT_9_16,
        duration: Optional[int] = None,
        size: Optional[str] = None,
        remix_target_id: Optional[str] = None,
        max_wait_time: int = 600,
        progress_callback: callable = None
    ) -> Optional[Sora2VideoResult]:
        """
        生成视频

        Args:
            prompt: 提示词
            image_url: 参考图 URL（可选）
            aspect_ratio: 视频比例
            duration: 视频时长（10 或 15 秒）
            size: 清晰度（small 或 large）
            remix_target_id: 视频续作的目标 ID（可选）
            max_wait_time: 最大等待时间（秒）
            progress_callback: 进度回调函数

        Returns:
            Sora2VideoResult 或 None
        """
        use_duration = duration or self.default_duration
        use_size = size or self.default_size
        
        logger.info(f"Sora2 开始生成视频: prompt={prompt[:50]}..., duration={use_duration}s")
        
        try:
            # 构建请求体
            request_body = {
                "model": "sora-2",
                "prompt": prompt,
                "aspectRatio": aspect_ratio.value,
                "duration": use_duration,
                "size": use_size,
                "webHook": "-1",  # 使用轮询方式
                "shutProgress": False
            }
            
            if image_url:
                request_body["url"] = image_url
            
            if remix_target_id:
                request_body["remixTargetId"] = remix_target_id
            
            # 提交任务
            url = f"{self.api_base}/v1/video/sora-video"
            response = self.session.post(url, json=request_body, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            if result.get('code') != 0:
                logger.error(f"Sora2 API 返回错误: {result}")
                return None
            
            task_id = result.get('data', {}).get('id')
            if not task_id:
                logger.error(f"Sora2 未获取到任务ID: {result}")
                return None
            
            logger.info(f"Sora2 任务已提交: {task_id}")
            
            # 等待完成
            final_result = self._wait_for_completion(
                task_id, 
                max_wait_time,
                progress_callback=progress_callback
            )
            
            # 解析结果
            data = final_result.get('data', {})
            results = data.get('results', [])
            
            if not results:
                logger.error("Sora2 未获取到视频结果")
                return None
            
            video_info = results[0]
            video_url = video_info.get('url')
            
            if not video_url:
                logger.error("Sora2 未获取到视频 URL")
                return None
            
            logger.info(f"Sora2 视频生成成功: {video_url}")
            
            # 上传到 OSS
            oss_url = None
            upload_result = self._upload_to_oss(video_url)
            oss_url = upload_result.get('oss_url')
            
            return Sora2VideoResult(
                url=video_url,
                pid=video_info.get('pid'),
                task_id=task_id,
                oss_url=oss_url,
                remove_watermark=video_info.get('removeWatermark', False)
            )
            
        except Exception as e:
            logger.error(f"Sora2 视频生成失败: {e}", exc_info=True)
            return None

    def generate_from_image(
        self,
        image_url: str,
        prompt: Optional[str] = None,
        aspect_ratio: Sora2AspectRatio = Sora2AspectRatio.PORTRAIT_9_16,
        duration: Optional[int] = None,
        size: Optional[str] = None,
        max_wait_time: int = 600,
        progress_callback: callable = None,
        max_retries: int = 1,
        remix_target_id: Optional[str] = None  # 续创作：上一个视频的 pid
    ) -> Optional[Sora2VideoResult]:
        """
        从图片生成视频（兼容 Veo3Service 接口）

        Args:
            image_url: 首帧图片 URL
            prompt: 动画提示词
            aspect_ratio: 视频比例
            duration: 视频时长
            size: 清晰度
            max_wait_time: 最大等待时间
            progress_callback: 进度回调
            max_retries: 最大重试次数
            remix_target_id: 续创作的目标视频 pid（可选，用于保持连贯性）

        Returns:
            Sora2VideoResult 或 None（包含 pid 用于下一次续创作）
        """
        # 如果没有提供 prompt，使用默认的动画提示词
        if not prompt:
            from services.blog_generator.prompts import get_prompt_manager
            prompt = get_prompt_manager().render_cover_video_prompt()
        
        if remix_target_id:
            logger.info(f"Sora2 续创作模式: 基于 pid={remix_target_id}")
        
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    logger.info(f"Sora2 视频生成重试 ({attempt}/{max_retries})")
                
                result = self.generate_video(
                    prompt=prompt,
                    image_url=image_url,
                    aspect_ratio=aspect_ratio,
                    duration=duration,
                    size=size,
                    remix_target_id=remix_target_id,  # 传递续创作 ID
                    max_wait_time=max_wait_time,
                    progress_callback=progress_callback
                )
                
                if result:
                    return result
                    
            except Exception as e:
                last_error = str(e)
                logger.error(f"Sora2 视频生成失败 (尝试 {attempt + 1}/{max_retries + 1}): {e}")
                continue
        
        logger.error(f"Sora2 视频生成最终失败: {last_error}")
        return None

    def upload_character(
        self,
        video_url: str,
        timestamps: str = "0,3",
        max_wait_time: int = 300,
        progress_callback: callable = None
    ) -> Optional[Sora2CharacterResult]:
        """
        从视频创建角色

        Args:
            video_url: 角色视频 URL
            timestamps: 视频范围（格式: "开始秒数,结束秒数"，最多3秒）
            max_wait_time: 最大等待时间
            progress_callback: 进度回调

        Returns:
            Sora2CharacterResult 或 None
        """
        logger.info(f"Sora2 创建角色: video={video_url[:50]}..., timestamps={timestamps}")
        
        try:
            request_body = {
                "url": video_url,
                "timestamps": timestamps,
                "webHook": "-1",
                "shutProgress": False
            }
            
            url = f"{self.api_base}/v1/video/sora-upload-character"
            response = self.session.post(url, json=request_body, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            if result.get('code') != 0:
                logger.error(f"Sora2 角色创建 API 返回错误: {result}")
                return None
            
            task_id = result.get('data', {}).get('id')
            if not task_id:
                logger.error(f"Sora2 角色创建未获取到任务ID: {result}")
                return None
            
            # 等待完成
            final_result = self._wait_for_completion(
                task_id, 
                max_wait_time,
                progress_callback=progress_callback
            )
            
            # 解析结果
            data = final_result.get('data', {})
            results = data.get('results', [])
            
            if not results:
                logger.error("Sora2 角色创建未获取到结果")
                return None
            
            character_id = results[0].get('character_id')
            if not character_id:
                logger.error("Sora2 未获取到角色 ID")
                return None
            
            logger.info(f"Sora2 角色创建成功: {character_id}")
            
            return Sora2CharacterResult(
                character_id=character_id,
                task_id=task_id
            )
            
        except Exception as e:
            logger.error(f"Sora2 角色创建失败: {e}", exc_info=True)
            return None

    def create_character_from_video(
        self,
        pid: str,
        timestamps: str = "0,3",
        max_wait_time: int = 300,
        progress_callback: callable = None
    ) -> Optional[Sora2CharacterResult]:
        """
        从已生成的视频创建角色

        Args:
            pid: 原视频 ID（生成视频后返回的 pid）
            timestamps: 视频范围
            max_wait_time: 最大等待时间
            progress_callback: 进度回调

        Returns:
            Sora2CharacterResult 或 None
        """
        logger.info(f"Sora2 从视频创建角色: pid={pid}, timestamps={timestamps}")
        
        try:
            request_body = {
                "pid": pid,
                "timestamps": timestamps,
                "webHook": "-1",
                "shutProgress": False
            }
            
            url = f"{self.api_base}/v1/video/sora-create-character"
            response = self.session.post(url, json=request_body, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            if result.get('code') != 0:
                logger.error(f"Sora2 角色创建 API 返回错误: {result}")
                return None
            
            task_id = result.get('data', {}).get('id')
            if not task_id:
                return None
            
            # 等待完成
            final_result = self._wait_for_completion(
                task_id, 
                max_wait_time,
                progress_callback=progress_callback
            )
            
            data = final_result.get('data', {})
            results = data.get('results', [])
            
            if not results:
                return None
            
            character_id = results[0].get('character_id')
            if not character_id:
                return None
            
            logger.info(f"Sora2 角色创建成功: {character_id}")
            
            return Sora2CharacterResult(
                character_id=character_id,
                task_id=task_id
            )
            
        except Exception as e:
            logger.error(f"Sora2 角色创建失败: {e}", exc_info=True)
            return None

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
                raise TimeoutError(f"Sora2 任务等待超时 (超过 {max_wait_time} 秒)")

            result = self._get_result(task_id)

            if result.get('code') == 0:
                data = result.get('data', {})
                status = data.get('status')
                progress = data.get('progress', 0)

                if progress != last_progress:
                    logger.info(f"Sora2 任务进度: {progress}%")
                    last_progress = progress
                    
                    if progress_callback:
                        try:
                            progress_callback(progress, status)
                        except Exception as e:
                            logger.warning(f"进度回调失败: {e}")

                if status == VideoStatus.SUCCEEDED.value:
                    return result
                elif status == VideoStatus.FAILED.value:
                    raise RuntimeError(
                        f"Sora2 任务失败: {data.get('failure_reason')} - {data.get('error')}"
                    )
            elif result.get('code') == -22:
                raise RuntimeError(f"Sora2 任务不存在: {task_id}")

            time.sleep(poll_interval)

    def _get_result(self, task_id: str) -> Dict[str, Any]:
        """获取任务结果"""
        url = f"{self.api_base}/v1/draw/result"
        response = self.session.post(url, json={"id": task_id})
        response.raise_for_status()
        return response.json()

    def _upload_to_oss(self, video_url: str) -> dict:
        """上传视频到 OSS"""
        from .oss_service import get_oss_service
        oss_service = get_oss_service()
        
        if oss_service and oss_service.is_available:
            oss_result = oss_service.upload_video_from_url(video_url)
            if oss_result.get('success'):
                oss_url = oss_result.get('url')
                logger.info(f"Sora2 视频已上传到 OSS: {oss_url}")
                return {'oss_url': oss_url}
            else:
                logger.warning(f"Sora2 视频上传 OSS 失败: {oss_result.get('error')}")
        
        return {'oss_url': None}


# 全局服务实例
_sora2_service: Optional[Sora2Service] = None


def get_sora2_service() -> Optional[Sora2Service]:
    """获取全局 Sora2 服务实例"""
    return _sora2_service


def init_sora2_service(config: dict) -> Optional[Sora2Service]:
    """
    从配置初始化 Sora2 服务

    Args:
        config: Flask app.config 字典

    Returns:
        Sora2Service 实例或 None
    """
    global _sora2_service
    
    api_key = config.get('NANO_BANANA_API_KEY', '')
    if not api_key:
        logger.warning("未配置 NANO_BANANA_API_KEY，Sora2 服务不可用")
        return None
    
    _sora2_service = Sora2Service(
        api_key=api_key,
        api_base=config.get('NANO_BANANA_API_BASE', 'https://grsai.dakka.com.cn'),
        default_duration=config.get('SORA2_DURATION', 10),
        default_size=config.get('SORA2_SIZE', 'small')
    )
    
    logger.info("Sora2 服务已初始化")
    return _sora2_service
