"""
视频序列编排服务 - 多图片合并成动画讲解视频

核心功能：
1. 图片序列分析
2. 转场规划
3. 时序规划
4. 动画指令生成
5. 并行视频生成
6. 视频合成
"""

import asyncio
import logging
import os
import subprocess
import tempfile
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional, Callable

logger = logging.getLogger(__name__)


class TransitionType(Enum):
    """转场类型"""
    FADE = "fade"
    CROSSFADE = "crossfade"
    SLIDE_LEFT = "slide_left"
    SLIDE_RIGHT = "slide_right"
    ZOOM = "zoom"
    DISSOLVE = "dissolve"


@dataclass
class VideoSlide:
    """视频幻灯片（对应一张图片）"""
    index: int
    image_url: str
    content: str
    title: str = ""
    
    # 时间控制
    duration: float = 5.0  # 秒
    
    # 动画控制
    animation_prompt: str = ""
    animation_style: str = "ghibli_summer"
    
    # 转场
    transition_in: TransitionType = TransitionType.FADE
    transition_out: TransitionType = TransitionType.CROSSFADE
    transition_duration: float = 0.5  # 秒
    
    # 生成结果
    video_url: Optional[str] = None


@dataclass
class VideoTimeline:
    """视频时间线"""
    name: str
    total_duration: float = 0.0
    fps: int = 30
    resolution: str = "1080x1920"  # 竖屏 9:16
    
    slides: List[VideoSlide] = field(default_factory=list)
    
    # 音频
    bgm_url: Optional[str] = None
    bgm_volume: float = 0.3
    
    # 输出
    output_url: Optional[str] = None


class VideoSequenceOrchestrator:
    """
    视频序列编排器
    
    核心职责：
    1. 分析图片序列
    2. 规划转场和时序
    3. 生成动画指令
    4. 协调视频生成
    5. 合成最终视频
    """
    
    def __init__(
        self,
        llm_client,
        video_service,  # UnifiedVideoService（统一入口）
        prompt_manager,
        oss_service=None,
        video_model: str = "veo3"  # 默认使用 veo3
    ):
        self.llm = llm_client
        self.video_service = video_service  # UnifiedVideoService
        self.prompt_manager = prompt_manager
        self.oss_service = oss_service
        self.video_model = video_model
        
        # FFmpeg 路径
        self.ffmpeg_path = "ffmpeg"
        
        logger.info(f"VideoSequenceOrchestrator 初始化完成, 视频模型: {video_model}")
    
    async def orchestrate(
        self,
        images: List[str],
        scripts: List[str],
        style: str = "ghibli_summer",
        target_duration: float = 60.0,
        bgm_url: Optional[str] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        video_model: Optional[str] = None  # 可覆盖默认模型
    ) -> Optional[str]:
        """
        编排完整的视频生成流程
        
        Args:
            images: 图片 URL 列表
            scripts: 对应的文案列表
            style: 动画风格
            target_duration: 目标总时长（秒）
            bgm_url: 背景音乐 URL（可选）
            progress_callback: 进度回调 callback(progress: int, status: str)
        
        Returns:
            最终视频 URL 或 None
        """
        if len(images) != len(scripts):
            logger.error(f"图片数量({len(images)})与文案数量({len(scripts)})不匹配")
            return None
        
        if len(images) == 0:
            logger.error("图片列表为空")
            return None
        
        # 确定使用的视频模型
        use_model = video_model or self.video_model
        logger.info(f"开始编排视频序列: {len(images)} 张图片, 目标时长 {target_duration}s, 风格 {style}, 模型 {use_model}")
        
        try:
            # Step 1: 创建时间线
            self._report_progress(progress_callback, 5, "创建时间线...")
            timeline = await self._create_timeline(images, scripts, style, target_duration)
            
            # Step 2: 生成全局风格指导
            self._report_progress(progress_callback, 10, "生成风格指导...")
            global_style_guide = await self._generate_global_style_guide(timeline, style)
            
            # Step 3: 为每个幻灯片生成动画 Prompt
            self._report_progress(progress_callback, 15, "生成动画指令...")
            await self._generate_animation_prompts(timeline, global_style_guide, style)
            
            # Step 4: 并行生成视频片段
            self._report_progress(progress_callback, 20, "生成视频片段...")
            await self._generate_video_segments(timeline, progress_callback, use_model)
            
            # Step 5: 合成最终视频
            self._report_progress(progress_callback, 85, "合成视频...")
            timeline.bgm_url = bgm_url
            final_video_url = await self._compose_final_video(timeline)
            
            self._report_progress(progress_callback, 100, "完成")
            
            logger.info(f"视频序列编排完成: {final_video_url}")
            return final_video_url
            
        except Exception as e:
            logger.error(f"视频序列编排失败: {e}", exc_info=True)
            return None
    
    def _report_progress(
        self,
        callback: Optional[Callable[[int, str], None]],
        progress: int,
        status: str
    ):
        """报告进度"""
        logger.info(f"进度: {progress}% - {status}")
        if callback:
            try:
                callback(progress, status)
            except Exception as e:
                logger.warning(f"进度回调失败: {e}")
    
    async def _create_timeline(
        self,
        images: List[str],
        scripts: List[str],
        style: str,
        target_duration: float
    ) -> VideoTimeline:
        """
        创建视频时间线
        
        根据文案长度分配每个幻灯片的时长
        """
        timeline = VideoTimeline(
            name="讲解视频",
            resolution="1080x1920"  # 竖屏
        )
        
        # 计算每个幻灯片的时长（根据文案长度加权）
        total_chars = sum(len(s) for s in scripts)
        if total_chars == 0:
            total_chars = len(scripts)  # 避免除零
        
        # 预留转场时间
        transition_time = 0.5 * (len(images) - 1)
        available_duration = target_duration - transition_time
        
        # 最小时长 3 秒，最大时长 15 秒
        min_duration = 3.0
        max_duration = 15.0
        
        for i, (image, script) in enumerate(zip(images, scripts)):
            # 根据文案长度计算时长
            char_ratio = len(script) / total_chars if total_chars > 0 else 1.0 / len(scripts)
            duration = available_duration * char_ratio
            duration = max(min_duration, min(max_duration, duration))
            
            # 选择转场效果
            transition_in, transition_out = self._select_transitions(i, len(images))
            
            slide = VideoSlide(
                index=i,
                image_url=image,
                content=script,
                title=script.split('\n')[0][:50] if script else f"第{i+1}页",
                duration=duration,
                animation_style=style,
                transition_in=transition_in,
                transition_out=transition_out
            )
            
            timeline.slides.append(slide)
        
        # 计算总时长
        timeline.total_duration = sum(s.duration for s in timeline.slides) + transition_time
        
        logger.info(f"时间线创建完成: {len(timeline.slides)} 个幻灯片, 总时长 {timeline.total_duration:.1f}s")
        return timeline
    
    def _select_transitions(self, index: int, total: int) -> tuple:
        """
        选择转场效果
        
        规则：
        - 第一页：fade_in
        - 最后一页：fade_out
        - 中间页：crossfade
        """
        if index == 0:
            transition_in = TransitionType.FADE
        else:
            transition_in = TransitionType.CROSSFADE
        
        if index == total - 1:
            transition_out = TransitionType.FADE
        else:
            transition_out = TransitionType.CROSSFADE
        
        return transition_in, transition_out
    
    async def _generate_global_style_guide(
        self,
        timeline: VideoTimeline,
        style: str
    ) -> str:
        """
        生成全局风格指导
        
        确保所有幻灯片的动画风格一致
        """
        # 预定义的风格指导
        style_guides = {
            "ghibli_summer": """
# 全局风格指导 - 宫崎骏夏日风格

## 动画特点
- 整体风格：温暖、柔和、充满生活气息
- 动画节奏：舒缓、温和、不急躁
- 色调：保持原图的温暖色调

## 动画元素
- 人物/角色：轻微浮动 + 温和摇晃（幅度小于 5px）
- 自然元素：缓慢摇晃，仿佛微风吹动
- 光线/光晕：脉冲发光，强调关键信息
- 文字/标签：微微浮动

## 动画节奏
- 所有动画速度：0.5x 正常速度
- 动画循环：平滑、无明显断点
- 关键信息强调：1-2 秒

## 禁止事项
- 不要有剧烈的运动
- 不要改变原图的颜色和布局
- 不要添加新的元素
""",
            "cartoon": """
# 全局风格指导 - 卡通风格

## 动画特点
- 整体风格：活泼、生动、富有表现力
- 动画节奏：适中、有节奏感
- 色调：保持原图的鲜艳色彩

## 动画元素
- 人物/角色：轻微弹跳 + 眨眼
- 图标/符号：缓慢旋转或缩放
- 箭头/指示：温和摇晃
- 强调元素：脉冲发光

## 动画节奏
- 所有动画速度：0.7x 正常速度
- 动画循环：平滑
""",
            "scientific": """
# 全局风格指导 - 科普风格

## 动画特点
- 整体风格：清晰、专业、强调信息传递
- 动画节奏：稳定、有条理
- 色调：保持原图的专业色调

## 动画元素
- 数据/图表：数据流动效果
- 箭头/连接线：光点沿线流动
- 节点/圆形：脉冲效果
- 文字：逐字出现或高亮

## 动画节奏
- 所有动画速度：0.6x 正常速度
- 强调关键信息点
"""
        }
        
        return style_guides.get(style, style_guides["ghibli_summer"])
    
    async def _generate_animation_prompts(
        self,
        timeline: VideoTimeline,
        global_style_guide: str,
        style: str
    ):
        """
        为每个幻灯片生成动画 Prompt
        
        考虑上下文连贯性
        """
        total = len(timeline.slides)
        
        for i, slide in enumerate(timeline.slides):
            # 获取上下文信息
            prev_content = timeline.slides[i-1].content if i > 0 else None
            next_content = timeline.slides[i+1].content if i < total - 1 else None
            
            # 生成动画 Prompt
            prompt = self._build_animation_prompt(
                slide=slide,
                prev_content=prev_content,
                next_content=next_content,
                global_style_guide=global_style_guide,
                index=i,
                total=total
            )
            
            slide.animation_prompt = prompt
        
        logger.info(f"已为 {total} 个幻灯片生成动画 Prompt")
    
    def _build_animation_prompt(
        self,
        slide: VideoSlide,
        prev_content: Optional[str],
        next_content: Optional[str],
        global_style_guide: str,
        index: int,
        total: int
    ) -> str:
        """
        构建单个幻灯片的动画 Prompt
        """
        # 基础动画指令
        base_prompt = """
Add smooth, gentle animations to this educational illustration:
- All characters/people: gentle swaying, subtle breathing motion
- Icons and symbols: slow rotation or gentle pulsing
- Arrows and lines: subtle glow effect, energy flow along the path
- Text labels: gentle floating motion
- Background elements: slow, subtle movement
- Emphasis elements: soft pulsing glow

Animation requirements:
- Keep all original elements, colors, and layout unchanged
- Smooth, professional, non-distracting animations
- Animation speed: 0.5x normal (very gentle)
- Loopable, seamless transitions
- Duration: {duration} seconds
"""
        
        # 根据位置添加特殊指令
        position_hint = ""
        if index == 0:
            position_hint = "\nThis is the opening slide - start with a gentle fade-in effect."
        elif index == total - 1:
            position_hint = "\nThis is the closing slide - end with a gentle fade-out effect."
        
        # 连贯性提示
        continuity_hint = ""
        if prev_content:
            continuity_hint += f"\nPrevious slide topic: {prev_content[:100]}..."
        if next_content:
            continuity_hint += f"\nNext slide topic: {next_content[:100]}..."
        
        if continuity_hint:
            continuity_hint = "\n\nContext for visual continuity:" + continuity_hint + "\nMaintain consistent animation style with adjacent slides."
        
        return base_prompt.format(duration=slide.duration) + position_hint + continuity_hint
    
    async def _generate_video_segments(
        self,
        timeline: VideoTimeline,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        video_model: str = "sora2"
    ):
        """
        串行生成视频片段（Sora2 续创作模式）
        
        Sora2 支持续创作：每个视频基于上一个视频的 pid 继续生成
        这样可以保持视频片段之间的连贯性
        """
        if not self.video_service or not self.video_service.is_available(video_model):
            logger.error(f"视频服务不可用: {video_model}")
            return
        
        model_name = video_model.upper()
        is_sora2 = video_model.lower() in ['sora2', 'sora-2']
        
        if is_sora2:
            logger.info(f"使用 {model_name} 串行续创作模式生成视频片段")
        else:
            logger.info(f"使用 {model_name} 生成视频片段")
        
        total = len(timeline.slides)
        last_pid = None  # 上一个视频的 pid，用于续创作
        
        for i, slide in enumerate(timeline.slides):
            logger.info(f"[{model_name}] 生成视频片段 {slide.index + 1}/{total}" + 
                       (f" (续创作 pid={last_pid})" if last_pid else ""))
            
            try:
                # 在线程池中执行同步的视频生成
                loop = asyncio.get_event_loop()
                
                # 构建生成参数
                def generate_video():
                    return self.video_service.generate_from_image(
                        image_url=slide.image_url,
                        prompt=slide.animation_prompt,
                        model=video_model,
                        max_retries=1,
                        remix_target_id=last_pid if is_sora2 else None  # Sora2 续创作
                    )
                
                result = await loop.run_in_executor(None, generate_video)
                
                if result and result.oss_url:
                    slide.video_url = result.oss_url
                    # 保存 pid 用于下一次续创作
                    if is_sora2 and result.pid:
                        last_pid = result.pid
                        logger.info(f"[{model_name}] 视频片段 {slide.index + 1} 生成成功, pid={result.pid}")
                    else:
                        logger.info(f"[{model_name}] 视频片段 {slide.index + 1} 生成成功")
                elif result and result.url:
                    slide.video_url = result.url
                    if is_sora2 and result.pid:
                        last_pid = result.pid
                    logger.info(f"[{model_name}] 视频片段 {slide.index + 1} 生成成功（使用原始 URL）")
                else:
                    logger.error(f"[{model_name}] 视频片段 {slide.index + 1} 生成失败")
                    # 续创作链断裂，重置 pid
                    last_pid = None
                    
            except Exception as e:
                logger.error(f"[{model_name}] 视频片段 {slide.index + 1} 生成异常: {e}")
                last_pid = None  # 续创作链断裂
            
            # 报告进度
            progress = 20 + int(65 * (i + 1) / total)
            self._report_progress(
                progress_callback,
                progress,
                f"[{model_name}] 生成视频片段 {i + 1}/{total}"
            )
        
        # 统计成功数量
        success_count = sum(1 for s in timeline.slides if s.video_url)
        logger.info(f"[{model_name}] 视频片段生成完成: {success_count}/{total} 成功")
    
    async def _compose_final_video(self, timeline: VideoTimeline) -> Optional[str]:
        """
        合成最终视频
        
        使用 FFmpeg 拼接视频片段，添加转场效果
        """
        # 过滤出成功生成的视频
        valid_slides = [s for s in timeline.slides if s.video_url]
        
        if not valid_slides:
            logger.error("没有可用的视频片段")
            return None
        
        logger.info(f"开始合成视频: {len(valid_slides)} 个片段")
        
        # 创建持久输出目录
        output_dir = os.path.join(os.path.dirname(__file__), '..', 'static', 'videos')
        os.makedirs(output_dir, exist_ok=True)
        output_dir = os.path.abspath(output_dir)
        
        try:
            # 创建临时目录用于下载
            with tempfile.TemporaryDirectory() as temp_dir:
                # 下载所有视频片段
                local_videos = []
                for i, slide in enumerate(valid_slides):
                    local_path = os.path.join(temp_dir, f"segment_{i}.mp4")
                    if await self._download_video(slide.video_url, local_path):
                        local_videos.append(local_path)
                    else:
                        logger.warning(f"下载视频片段 {i} 失败，跳过")
                
                if not local_videos:
                    logger.error("没有成功下载的视频片段")
                    return None
                
                # 生成输出文件路径（保存到持久目录）
                output_filename = f"merged_{uuid.uuid4().hex[:8]}.mp4"
                output_path = os.path.join(output_dir, output_filename)
                
                # 使用 FFmpeg 合成
                if len(local_videos) == 1:
                    # 只有一个视频，直接复制
                    import shutil
                    shutil.copy(local_videos[0], output_path)
                else:
                    # 多个视频，使用 concat 合成
                    await self._ffmpeg_concat(local_videos, output_path, timeline)
                
                logger.info(f"视频已保存到本地: {output_path}")
                
                # 上传到 OSS
                logger.info(f"准备上传视频到 OSS, 文件路径: {output_path}")
                logger.info(f"OSS 服务状态: oss_service={self.oss_service is not None}, is_available={getattr(self.oss_service, 'is_available', False) if self.oss_service else False}")
                
                if self.oss_service and self.oss_service.is_available:
                    logger.info("开始上传视频到 OSS...")
                    result = self.oss_service.upload_file(output_path)
                    logger.info(f"OSS 上传结果: {result}")
                    if result.get('success'):
                        final_url = result.get('url')
                        logger.info(f"视频已上传到 OSS: {final_url}")
                        return final_url
                    else:
                        logger.error(f"OSS 上传失败: {result}")
                
                # OSS 不可用，返回本地静态文件路径
                local_url = f"/static/videos/{output_filename}"
                logger.info(f"OSS 不可用，返回本地路径: {local_url}")
                return local_url
                
        except Exception as e:
            logger.error(f"视频合成失败: {e}", exc_info=True)
            return None
    
    async def _download_video(self, url: str, local_path: str) -> bool:
        """下载视频到本地"""
        import requests
        
        try:
            response = requests.get(url, timeout=60, stream=True)
            response.raise_for_status()
            
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return True
        except Exception as e:
            logger.error(f"下载视频失败: {url}, 错误: {e}")
            return False
    
    async def _ffmpeg_concat(
        self,
        video_paths: List[str],
        output_path: str,
        timeline: VideoTimeline
    ):
        """
        使用 FFmpeg 拼接视频
        
        添加转场效果（crossfade）
        """
        # 创建 concat 文件列表
        concat_file = output_path.replace('.mp4', '_concat.txt')
        with open(concat_file, 'w') as f:
            for path in video_paths:
                f.write(f"file '{path}'\n")
        
        # 简单拼接（不带转场）
        # 如果需要转场效果，可以使用 xfade 滤镜，但会更复杂
        cmd = [
            self.ffmpeg_path,
            '-y',  # 覆盖输出
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_file,
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '23',
            '-c:a', 'aac',
            '-b:a', '128k',
            output_path
        ]
        
        logger.info(f"执行 FFmpeg 命令: {' '.join(cmd)}")
        
        # 执行命令
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: subprocess.run(cmd, capture_output=True, text=True)
        )
        
        if result.returncode != 0:
            logger.error(f"FFmpeg 执行失败: {result.stderr}")
            raise RuntimeError(f"FFmpeg 执行失败: {result.stderr}")
        
        logger.info("FFmpeg 拼接完成")
        
        # 清理临时文件
        os.remove(concat_file)


# 全局服务实例
_video_sequence_service: Optional[VideoSequenceOrchestrator] = None


def get_video_sequence_service() -> Optional[VideoSequenceOrchestrator]:
    """获取全局视频序列服务实例"""
    return _video_sequence_service


def init_video_sequence_service(
    llm_client,
    video_service,
    prompt_manager,
    oss_service=None
) -> VideoSequenceOrchestrator:
    """
    初始化视频序列服务
    
    Args:
        llm_client: LLM 客户端
        video_service: 视频生成服务
        prompt_manager: Prompt 管理器
        oss_service: OSS 服务（可选）
    
    Returns:
        VideoSequenceOrchestrator 实例
    """
    global _video_sequence_service
    
    _video_sequence_service = VideoSequenceOrchestrator(
        llm_client=llm_client,
        video_service=video_service,
        prompt_manager=prompt_manager,
        oss_service=oss_service
    )
    
    logger.info("视频序列服务已初始化")
    return _video_sequence_service
