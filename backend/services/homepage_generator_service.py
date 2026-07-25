"""
书籍首页内容生成服务
"""
import json
import logging
from typing import Dict, Any, Optional

from services.database_service import DatabaseService
from services.outline_expander_service import OutlineExpanderService
from services.blog_generation import get_prompt_manager

logger = logging.getLogger(__name__)


class HomepageGeneratorService:
    """书籍首页内容生成服务"""
    
    def __init__(
        self,
        db: DatabaseService,
        llm_client=None,
        outline_expander: OutlineExpanderService = None
    ):
        """
        初始化首页生成服务
        
        Args:
            db: 数据库服务
            llm_client: LLM 客户端
            outline_expander: 大纲扩展服务
        """
        self.db = db
        self.llm = llm_client
        self.outline_expander = outline_expander
        self.prompt_manager = get_prompt_manager()
    
    def generate_homepage(self, book_id: str) -> Dict[str, Any]:
        """
        生成书籍首页内容
        
        Args:
            book_id: 书籍 ID
            
        Returns:
            首页内容字典
        """
        book = self.db.get_book(book_id)
        if not book:
            logger.error(f"书籍不存在: {book_id}")
            return {}
        
        logger.info(f"生成首页: {book['title']}")
        
        # 1. 扩展大纲（如果有扩展服务）
        full_outline = None
        if self.outline_expander:
            try:
                full_outline = self.outline_expander.expand_outline(book_id)
            except Exception as e:
                logger.warning(f"扩展大纲失败: {e}")
        
        # 如果没有扩展大纲，使用现有大纲
        if not full_outline:
            full_outline = self._get_existing_outline(book)
        
        # 2. 生成首页各模块内容
        homepage_content = self._generate_homepage_content(book, full_outline)
        
        # 3. 保存到数据库
        if homepage_content:
            self.db.update_book_homepage(book_id, homepage_content)
            logger.info(f"首页生成完成: {book['title']}")
        
        return homepage_content
    
    def _get_existing_outline(self, book: Dict[str, Any]) -> Dict[str, Any]:
        """获取现有大纲"""
        # 优先使用 full_outline
        if book.get('full_outline'):
            try:
                if isinstance(book['full_outline'], str):
                    return json.loads(book['full_outline'])
                return book['full_outline']
            except:
                pass
        
        # 其次使用 outline
        if book.get('outline'):
            try:
                if isinstance(book['outline'], str):
                    return json.loads(book['outline'])
                return book['outline']
            except:
                pass
        
        return {'chapters': []}
    
    def _generate_homepage_content(
        self,
        book: Dict[str, Any],
        outline: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成首页内容"""
        if not self.llm:
            # 无 LLM 时，使用默认内容
            return self._generate_default_homepage(book, outline)
        
        prompt = self.prompt_manager.render_homepage_generator(
            book=book,
            outline=outline
        )
        
        try:
            response = self.llm.chat(messages=[{"role": "user", "content": prompt}])
            response_text = response if isinstance(response, str) else response.get('content', '')
            
            # 提取 JSON
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                homepage = json.loads(response_text[json_start:json_end])
                # 添加大纲
                homepage['outline'] = outline
                return homepage
        except Exception as e:
            logger.error(f"生成首页内容失败: {e}")
        
        # 降级：使用默认内容
        return self._generate_default_homepage(book, outline)
    
    def _generate_default_homepage(
        self,
        book: Dict[str, Any],
        outline: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成默认首页内容"""
        theme = book.get('theme', 'general')
        theme_names = {
            'ai': 'AI 与机器学习',
            'web': 'Web 开发',
            'data': '数据技术',
            'devops': 'DevOps 与运维',
            'security': '安全技术',
            'general': '技术'
        }
        theme_name = theme_names.get(theme, '技术')
        
        return {
            'slogan': f'{theme_name}实战指南，从入门到精通',
            'introduction': book.get('description', f'《{book["title"]}》是一本关于{theme_name}的教程书籍。'),
            'highlights': [
                {'icon': '📚', 'title': '体系化内容', 'description': f'包含 {book.get("chapters_count", 0)} 个章节，{book.get("blogs_count", 0)} 篇精选博客'},
                {'icon': '💡', 'title': '实战导向', 'description': '每个章节都有实际案例和代码示例'},
                {'icon': '🚀', 'title': '持续更新', 'description': '内容持续更新，紧跟技术发展'}
            ],
            'target_audience': [
                f'对{theme_name}感兴趣的开发者',
                '希望系统学习相关技术的工程师',
                '想要提升技术能力的技术人员'
            ],
            'prerequisites': [
                '具备基础编程能力',
                '了解相关领域的基本概念'
            ],
            'outline': outline
        }
