"""
通用发布器 - 配置驱动的多平台文章发布
"""

from playwright.async_api import async_playwright
from typing import Optional
from .workflow_engine import WorkflowEngine, PublishContext
import logging
import re

logger = logging.getLogger(__name__)


def extract_tags_from_content(content: str) -> list[str]:
    """从文章内容中提取标签（查找用 · 分隔的标签行）"""
    lines = content.split('\n')
    for line in lines:
        # 匹配包含多个 · 分隔符的行（至少2个标签）
        if '·' in line and len(line.split('·')) >= 2:
            tags = []
            for t in line.split('·'):
                tag = t.strip()
                # 去除 Markdown 特殊字符（##、**、*、`、[]等）
                tag = re.sub(r'^[#*`\[\]]+\s*', '', tag)
                tag = re.sub(r'\s*[#*`\[\]]+$', '', tag)
                if tag and len(tag) < 20:
                    tags.append(tag)
            if len(tags) >= 2:
                return tags[:5]  # 最多5个标签
    return []


class Publisher:
    """通用发布器（配置驱动）"""
    
    def __init__(self, config_dir: str = None):
        self.engine = WorkflowEngine(config_dir)
    
    def get_supported_platforms(self) -> list[str]:
        """获取支持的平台列表"""
        return self.engine.get_supported_platforms()
    
    async def publish(
        self,
        platform_id: str,
        cookies: list[dict],
        title: str,
        content: str,
        tags: Optional[list[str]] = None,
        category: Optional[str] = None,
        article_type: str = "original",
        pub_type: str = "public",
        headless: bool = True,
        images: Optional[list[str]] = None,
    ) -> dict:
        """
        发布文章到指定平台
        
        Args:
            platform_id: 平台 ID (csdn/zhihu/juejin/xiaohongshu)
            cookies: 登录 Cookie
            title: 文章标题
            content: 文章内容（Markdown）
            tags: 标签列表
            category: 分类
            article_type: 文章类型 (original/repost/translation)
            pub_type: 发布类型 (public/private)
            headless: 是否无头模式运行浏览器
            images: 图片路径列表（用于小红书等图片平台）
            
        Returns:
            dict: {"success": bool, "url": str, "message": str, "platform": str}
        """
        try:
            config = self.engine.load_config(platform_id)
        except FileNotFoundError:
            return {
                "success": False,
                "url": None,
                "message": f"不支持的平台: {platform_id}",
                "platform": platform_id
            }
        
        platform_name = config['platform']['name']
        editor_url = config['platform']['editor_url']
        
        # 在文章开头添加 Vibe-Blog 宣传语
        header = config.get('header', {})
        if header.get('enabled', True):
            header_text = header.get('text', '''---
> 注 : 本文纯由长文技术博客助手[Vibe-Blog](https://github.com/datawhalechina/vibe-blog)生成, 如果对你有帮助,你也想创作同样风格的技术博客, 欢迎关注开源项目: [Vibe-Blog](https://github.com/datawhalechina/vibe-blog). 
> 
> [Vibe-Blog](https://github.com/datawhalechina/vibe-blog)是一个基于多 Agent 架构的 AI 长文博客生成助手，具备深度调研、智能配图、Mermaid 图表、代码集成、智能专业排版等专业写作能力，旨在将晦涩的技术知识转化为通俗易懂的科普文章，让每个人都能轻松理解复杂技术，在 AI 时代扬帆起航.
---

''')
            content_with_header = header_text + content
        else:
            content_with_header = content
        
        # 在文章末尾添加脚注
        footer = config.get('footer', {})
        if footer.get('enabled', False):
            footer_text = footer.get('text', '')
            content_final = content_with_header + footer_text
        else:
            content_final = content_with_header
        
        # 如果没有传入标签，从内容中自动提取
        if not tags:
            tags = extract_tags_from_content(content)
            if tags:
                logger.info(f"[{platform_name}] 自动提取标签: {tags}")
        
        context = PublishContext(
            title=title,
            content=content_final,
            tags=tags or [],
            category=category or "",
            article_type=article_type,
            pub_type=pub_type,
            images=images or []
        )
        
        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch(
                    headless=headless,
                    args=["--no-sandbox", "--disable-setuid-sandbox"]
                )
                ctx = await browser.new_context(
                    viewport={"width": 1920, "height": 1080}
                )
                
                # 确保每个 Cookie 都有必要的字段
                normalized_cookies = []
                cookie_domain = config['platform'].get('cookie_domain', '.csdn.net')
                for cookie in cookies:
                    # 支持字典格式和字符串格式
                    if isinstance(cookie, dict):
                        c = {
                            "name": cookie.get("name", ""),
                            "value": cookie.get("value", ""),
                            "domain": cookie.get("domain", cookie_domain),
                            "path": cookie.get("path", "/"),
                        }
                    elif isinstance(cookie, str) and '=' in cookie:
                        # 解析 "name=value" 格式
                        eq_idx = cookie.index('=')
                        c = {
                            "name": cookie[:eq_idx].strip(),
                            "value": cookie[eq_idx+1:].strip(),
                            "domain": cookie_domain,
                            "path": "/",
                        }
                    else:
                        continue
                    normalized_cookies.append(c)
                
                await ctx.add_cookies(normalized_cookies)
                page = await ctx.new_page()
                
                logger.info(f"[{platform_name}] 导航到: {editor_url}")
                await page.goto(editor_url, timeout=60000)
                await page.wait_for_timeout(3000)
                
                login_check = config.get('login_check', {})
                if login_check.get('type') == 'url_not_contains':
                    if login_check['value'] in page.url.lower():
                        await browser.close()
                        return {
                            "success": False,
                            "url": None,
                            "message": f"Cookie 已过期，请重新登录 {platform_name}",
                            "platform": platform_name
                        }
                
                logger.info(f"[{platform_name}] 上传内容...")
                result = await self.engine.upload_content(page, config, context)
                if not result.success:
                    await browser.close()
                    return {
                        "success": False,
                        "url": None,
                        "message": f"内容上传失败: {result.message}",
                        "platform": platform_name
                    }
                
                logger.info(f"[{platform_name}] 执行发布工作流...")
                result = await self.engine.execute_workflow(page, config, context)
                if not result.success:
                    await browser.close()
                    return {
                        "success": False,
                        "url": None,
                        "message": f"发布流程失败: {result.message}",
                        "platform": platform_name
                    }
                
                article_url = await self.engine.get_result_url(page, config)
                
                await browser.close()
                
                if article_url:
                    logger.info(f"[{platform_name}] 发布成功: {article_url}")
                else:
                    logger.info(f"[{platform_name}] 发布完成，但未获取到文章 URL")
                
                return {
                    "success": True,
                    "url": article_url,
                    "message": "发布成功" if article_url else "发布完成（请到平台查看）",
                    "platform": platform_name
                }
                    
            except Exception as e:
                logger.error(f"[{platform_name}] 发布失败: {e}")
                return {
                    "success": False,
                    "url": None,
                    "message": f"发布失败: {str(e)}",
                    "platform": platform_name
                }
    
    async def publish_to_multiple(
        self,
        platforms: list[str],
        cookies_map: dict[str, list[dict]],
        title: str,
        content: str,
        tags: Optional[list[str]] = None,
        category: Optional[str] = None,
    ) -> list[dict]:
        """
        一键发布到多个平台
        
        Args:
            platforms: 平台 ID 列表
            cookies_map: 各平台的 Cookie，格式 {"csdn": [...], "zhihu": [...]}
            title: 文章标题
            content: 文章内容
            tags: 标签列表
            category: 分类
            
        Returns:
            list[dict]: 每个平台的发布结果
        """
        results = []
        for platform_id in platforms:
            cookies = cookies_map.get(platform_id, [])
            if not cookies:
                results.append({
                    "success": False,
                    "url": None,
                    "message": f"未配置 {platform_id} 的登录信息",
                    "platform": platform_id
                })
                continue
            
            result = await self.publish(
                platform_id=platform_id,
                cookies=cookies,
                title=title,
                content=content,
                tags=tags,
                category=category
            )
            results.append(result)
        
        return results
