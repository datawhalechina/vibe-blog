"""
动画 Prompt 测试脚本

验证点：
1. ANIMATION_PROMPT 是否正确定义
2. 动画 Prompt 是否传入 Veo3 API
3. 单图模式和多图序列模式都传入动画 Prompt
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestAnimationPrompt:
    """测试动画 Prompt 功能"""
    
    def test_animation_prompt_defined(self):
        """测试 ANIMATION_PROMPT 常量是否定义"""
        from services.blog_generator.blog_service import BlogService
        
        # 验证 ANIMATION_PROMPT 存在
        assert hasattr(BlogService, 'ANIMATION_PROMPT')
        
        # 验证 Prompt 内容
        prompt = BlogService.ANIMATION_PROMPT
        assert isinstance(prompt, str)
        assert len(prompt) > 100
        
        # 验证关键内容
        assert "Add subtle animations" in prompt or "动画" in prompt
        assert "text" in prompt.lower() or "文字" in prompt
        assert "static" in prompt.lower() or "静态" in prompt
    
    def test_animation_prompt_content(self):
        """测试动画 Prompt 的具体内容"""
        from services.blog_generator.blog_service import BlogService
        
        prompt = BlogService.ANIMATION_PROMPT
        
        # 验证中文变形保护
        assert "CRITICAL" in prompt or "关键" in prompt
        assert "TEXT" in prompt or "文字" in prompt
        assert "static" in prompt.lower()
        
        # 验证动画元素
        assert "Gears" in prompt or "齿轮" in prompt
        assert "Arrows" in prompt or "箭头" in prompt
        assert "Icons" in prompt or "图标" in prompt
    
    def test_single_image_mode_passes_animation_prompt(self):
        """测试单图模式是否传入动画 Prompt"""
        import inspect
        from services.blog_generator.blog_service import BlogService
        
        # 获取 _generate_cover_video 方法源码
        source = inspect.getsource(BlogService._generate_cover_video)
        
        # 验证单图模式传入 ANIMATION_PROMPT
        assert "self.ANIMATION_PROMPT" in source
        assert "prompt=self.ANIMATION_PROMPT" in source
    
    def test_sequence_video_mode_passes_animation_prompt(self):
        """测试多图序列模式是否传入动画 Prompt"""
        import inspect
        from services.blog_generator.blog_service import BlogService
        
        # 获取 _generate_sequence_video 方法源码
        source = inspect.getsource(BlogService._generate_sequence_video)
        
        # 验证多图序列模式传入 ANIMATION_PROMPT
        assert "self.ANIMATION_PROMPT" in source
        assert "prompt=self.ANIMATION_PROMPT" in source
    
    def test_animation_prompt_passed_to_video_service(self):
        """测试动画 Prompt 是否正确传给视频服务"""
        import inspect
        from services.blog_generator.blog_service import BlogService
        
        # 获取 _generate_cover_video 方法源码
        source = inspect.getsource(BlogService._generate_cover_video)
        
        # 验证调用 video_service.generate_from_image 时传入 prompt
        assert "video_service.generate_from_image" in source
        assert "prompt=" in source
    
    def test_animation_prompt_format(self):
        """测试动画 Prompt 的格式是否正确"""
        from services.blog_generator.blog_service import BlogService
        
        prompt = BlogService.ANIMATION_PROMPT
        
        # 验证是英文 Prompt（Veo3 API 要求）
        assert prompt[0].isupper()  # 首字母大写
        
        # 验证包含具体指导
        lines = prompt.split('\n')
        assert len(lines) > 3  # 至少有多行内容
        
        # 验证包含时长指导
        assert "6-8" in prompt or "seconds" in prompt.lower()
    
    def test_animation_prompt_protects_chinese_text(self):
        """测试动画 Prompt 是否保护中文文字"""
        from services.blog_generator.blog_service import BlogService
        
        prompt = BlogService.ANIMATION_PROMPT
        
        # 关键保护条款
        assert "CRITICAL" in prompt
        assert "TEXT" in prompt
        assert "static" in prompt.lower()
        assert "Do NOT animate" in prompt or "不要动画" in prompt
        
        # 验证明确禁止中文变形
        assert "Chinese" in prompt or "text" in prompt.lower()


class TestAnimationIntegration:
    """集成测试：验证动画 Prompt 在完整流程中的使用"""
    
    def test_cover_video_generation_with_animation(self):
        """测试封面视频生成是否使用动画 Prompt"""
        import inspect
        from services.blog_generator.blog_service import BlogService
        
        # 获取方法源码
        source = inspect.getsource(BlogService._generate_cover_video)
        
        # 验证流程
        assert "section_images" in source  # 支持多图序列
        assert "self.ANIMATION_PROMPT" in source  # 传入动画 Prompt
        assert "video_service.generate_from_image" in source  # 调用视频服务
    
    def test_sequence_video_generation_with_animation(self):
        """测试多图序列视频生成是否使用动画 Prompt"""
        import inspect
        from services.blog_generator.blog_service import BlogService
        
        # 获取方法源码
        source = inspect.getsource(BlogService._generate_sequence_video)
        
        # 验证流程
        assert "cover_image_url" in source  # 封面图
        assert "section_images" in source  # 章节配图
        assert "self.ANIMATION_PROMPT" in source  # 动画 Prompt
        assert "generate_veo3_video" in source  # 生成视频函数


class TestAnimationPromptValidation:
    """验证动画 Prompt 的有效性"""
    
    def test_animation_prompt_not_empty(self):
        """测试动画 Prompt 不为空"""
        from services.blog_generator.blog_service import BlogService
        
        prompt = BlogService.ANIMATION_PROMPT
        assert prompt
        assert len(prompt) > 50
    
    def test_animation_prompt_is_string(self):
        """测试动画 Prompt 是字符串"""
        from services.blog_generator.blog_service import BlogService
        
        prompt = BlogService.ANIMATION_PROMPT
        assert isinstance(prompt, str)
    
    def test_animation_prompt_english(self):
        """测试动画 Prompt 是英文（Veo3 API 要求）"""
        from services.blog_generator.blog_service import BlogService
        
        prompt = BlogService.ANIMATION_PROMPT
        
        # 验证主要内容是英文
        english_words = ['Add', 'animations', 'text', 'static', 'CRITICAL']
        found_english = sum(1 for word in english_words if word in prompt)
        assert found_english >= 3  # 至少有 3 个英文关键词


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
