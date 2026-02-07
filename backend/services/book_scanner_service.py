"""
书籍扫描服务 - 自动扫描博客库，聚合成教程书籍
"""
import json
import uuid
import logging
import os
from typing import Dict, Any, List, Optional

from services.database_service import DatabaseService
from services.blog_generator.prompts import get_prompt_manager

logger = logging.getLogger(__name__)

# 主题到图标的映射
THEME_ICONS = {
    'ai': '🤖',
    'web': '🌐',
    'data': '📊',
    'devops': '⚙️',
    'security': '🔐',
    'general': '📖'
}


class BookScannerService:
    """书籍扫描服务"""
    
    def __init__(self, db: DatabaseService, llm_client=None):
        """
        初始化书籍扫描服务
        
        Args:
            db: 数据库服务
            llm_client: LLM 客户端（用于智能决策）
        """
        self.db = db
        self.llm = llm_client
    
    def regenerate_all_books(self) -> Dict[str, Any]:
        """
        重新生成所有书籍（清空旧数据，重新聚合）
        
        流程：
        1. 获取旧书籍信息作为参考
        2. 清空所有书籍数据（books, book_chapters 表）
        3. 重置所有博客的 book_id 为 NULL
        4. 重新对所有博客进行分类聚合（参考旧书籍信息）
        5. 重新生成所有书籍信息（封面、大纲、首页等）
        
        Returns:
            重新生成结果统计
        """
        logger.info("========== 开始重新生成所有书籍 ==========")
        
        # 1. 获取旧书籍信息作为参考（包括大纲）
        logger.info("【步骤1】获取旧书籍信息作为参考...")
        old_books = self.db.list_books(status='active')
        old_books_info = []
        for book in old_books:
            # 获取旧书籍的大纲
            outline = book.get('outline', '')
            if isinstance(outline, str) and outline:
                try:
                    outline = json.loads(outline)
                except:
                    outline = {}
            
            old_books_info.append({
                'title': book.get('title', ''),
                'theme': book.get('theme', 'general'),
                'description': book.get('description', ''),
                'blogs_count': book.get('blogs_count', 0),
                'outline': outline  # 保存旧大纲
            })
        logger.info(f"获取到 {len(old_books_info)} 本旧书籍作为参考")
        
        # 2. 清空旧书籍数据
        logger.info("【步骤2】清空旧书籍数据...")
        self.db.clear_all_books()
        
        # 3. 重置所有博客的 book_id
        logger.info("【步骤3】重置所有博客的 book_id...")
        self.db.reset_all_blog_book_ids()
        
        # 4. 重新扫描聚合（传入旧书籍信息作为参考）
        logger.info("【步骤4】重新扫描聚合...")
        result = self._scan_with_reference(old_books_info)
        
        result['message'] = "重新生成完成：" + result.get('message', '')
        logger.info(f"========== 重新生成完成 ==========")
        
        return result
    
    def _scan_with_reference(self, old_books_info: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        带参考信息的扫描聚合
        
        Args:
            old_books_info: 旧书籍信息列表，作为分类参考
        
        Returns:
            扫描结果统计
        """
        logger.info("开始扫描博客库（带参考信息）...")
        
        # 1. 获取所有博客（此时都是未分配的）
        all_blogs = self.db.get_unassigned_blogs()
        logger.info(f"发现 {len(all_blogs)} 篇博客待分类")
        
        if not all_blogs:
            return {
                "status": "success",
                "message": "没有博客需要处理",
                "blogs_processed": 0,
                "books_created": 0,
                "books_updated": 0,
                "summaries_generated": 0
            }
        
        # 1.1 检查并补充缺失的摘要
        summaries_generated = self._ensure_blog_summaries(all_blogs)
        if summaries_generated > 0:
            logger.info(f"已为 {summaries_generated} 篇博客生成摘要")
        
        # ========== 第一步：分类汇总（带参考信息）==========
        logger.info("【第一步】开始博客分类（参考旧书籍信息）...")
        classification = self._classify_blogs_with_reference(all_blogs, old_books_info)
        
        # 应用分类结果（创建新书籍、关联博客到书籍）
        classification_result = self._apply_classification(classification, all_blogs, [])
        logger.info(f"分类完成: 创建 {classification_result['books_created']} 本新书, "
                   f"分配 {classification_result['blogs_assigned']} 篇博客")
        
        # ========== 第二步：生成大纲（参考旧书籍大纲）==========
        books_to_update = classification_result.get('books_to_update', [])
        total_books = len(books_to_update)
        logger.info(f"【第二步】开始生成书籍大纲，共 {total_books} 本书籍待处理...")
        
        outlines_generated = 0
        
        for idx, book_id in enumerate(books_to_update, 1):
            try:
                # 查找是否有相似的旧书籍大纲可参考
                book = self.db.get_book(book_id)
                book_title = book.get('title', book_id) if book else book_id
                old_outline_ref = self._find_similar_old_outline(book, old_books_info) if book else None
                
                logger.info(f"📚 开始生成书籍大纲: [{idx}/{total_books}]: {book_title}")
                self._generate_book_outline(book_id, old_outline_ref)
                outlines_generated += 1
                logger.info(f"📚 生成书籍大纲完成: [{idx}/{total_books}]: {book_title}")
            except Exception as e:
                logger.warning(f"📚 生成书籍大纲失败: {book_id}, {e}")
        
        result = {
            "status": "success",
            "message": f"扫描完成",
            "blogs_processed": len(all_blogs),
            "books_created": classification_result['books_created'],
            "books_updated": outlines_generated,
            "summaries_generated": summaries_generated
        }
        
        logger.info(f"扫描完成: 处理 {result['blogs_processed']} 篇博客, "
                   f"创建 {result['books_created']} 本新书, "
                   f"更新 {result['books_updated']} 本书大纲")
        
        return result
    
    def _find_similar_old_outline(
        self,
        new_book: Dict[str, Any],
        old_books_info: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        查找与新书籍相似的旧书籍大纲
        
        Args:
            new_book: 新书籍信息
            old_books_info: 旧书籍信息列表
        
        Returns:
            相似的旧书籍大纲，如果没有则返回 None
        """
        if not new_book or not old_books_info:
            return None
        
        new_title = new_book.get('title', '').lower()
        new_theme = new_book.get('theme', '')
        
        # 查找标题相似或主题相同的旧书籍
        for old_book in old_books_info:
            old_title = old_book.get('title', '').lower()
            old_theme = old_book.get('theme', '')
            old_outline = old_book.get('outline', {})
            
            if not old_outline:
                continue
            
            # 标题包含关系或主题相同
            if (new_title in old_title or old_title in new_title or 
                (new_theme and new_theme == old_theme and new_theme != 'general')):
                logger.info(f"找到相似旧书籍大纲: 《{old_book['title']}》 -> 《{new_book['title']}》")
                return old_outline
        
        return None
    
    def _classify_blogs_with_reference(
        self,
        blogs: List[Dict[str, Any]],
        old_books_info: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        带参考信息的博客分类
        
        Args:
            blogs: 待分类的博客列表
            old_books_info: 旧书籍信息作为参考
        
        Returns:
            分类结果
        """
        if not self.llm:
            logger.warning("LLM 客户端未配置，使用默认分类策略")
            return self._default_classification(blogs)
        
        # 构建博客信息
        blogs_info = []
        for blog in blogs:
            real_title = self._extract_blog_title(blog)
            summary = blog.get('summary', '') or blog.get('markdown_content', '')[:300]
            blogs_info.append(
                f"博客ID: {blog['id']}\n"
                f"标题: {real_title}\n"
                f"摘要: {summary[:200]}"
            )
        
        # 构建旧书籍参考信息
        reference_books_info = ""
        if old_books_info:
            reference_items = []
            for book in old_books_info:
                reference_items.append(
                    f"- 《{book['title']}》({book['theme']}) - {book.get('blogs_count', 0)}篇博客"
                )
            reference_books_info = "\n".join(reference_items)
        
        prompt_manager = get_prompt_manager()
        prompt = prompt_manager.render_book_classifier(
            existing_books_info="暂无现有书籍（重新生成模式）",
            blogs_info="\n---\n".join(blogs_info),
            reference_books_info=reference_books_info
        )
        
        try:
            response = self.llm.chat(messages=[{"role": "user", "content": prompt}])
            response_text = response if isinstance(response, str) else response.get('content', '')
            
            # 提取 JSON
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                classification = json.loads(response_text[json_start:json_end])
            else:
                raise json.JSONDecodeError("No JSON found", response_text, 0)
            
            logger.info(f"LLM 分类完成: {len(classification.get('classifications', []))} 条分类, "
                       f"{len(classification.get('new_books', []))} 本新书")
            return classification
            
        except Exception as e:
            logger.error(f"LLM 分类失败: {e}")
            return self._default_classification(blogs)
    
    def _refresh_existing_books(self, books: List[Dict[str, Any]]) -> int:
        """
        强制刷新现有书籍的大纲
        
        Args:
            books: 书籍列表
            
        Returns:
            刷新的书籍数量
        """
        count = 0
        for book in books:
            try:
                result = self.rescan_book(book['id'])
                if result.get('status') == 'success':
                    count += 1
                    logger.info(f"刷新书籍大纲: {book['title']}")
            except Exception as e:
                logger.warning(f"刷新书籍大纲失败: {book['id']}, {e}")
        return count
    
    def _remove_code_blocks(self, content: str) -> str:
        """
        移除 Markdown 内容中的代码块，只保留文本
        
        Args:
            content: Markdown 内容
        
        Returns:
            移除代码块后的文本
        """
        import re
        # 移除 ```...``` 代码块
        content = re.sub(r'```[\s\S]*?```', '', content)
        # 移除行内代码 `...`
        content = re.sub(r'`[^`]+`', '', content)
        # 移除多余的空行
        content = re.sub(r'\n{3,}', '\n\n', content)
        return content.strip()
    
    def _extract_blog_title(self, blog: Dict[str, Any]) -> str:
        """
        从博客中提取真实标题
        
        优先从 markdown_content 的第一个 # 标题提取，
        如果没有则使用 topic（用户输入的 query）
        
        Args:
            blog: 博客记录
        
        Returns:
            博客标题
        """
        import re
        content = blog.get('markdown_content', '') or ''
        
        # 尝试从 Markdown 内容提取第一个 # 标题
        match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        
        # 降级：使用 topic
        return blog.get('topic', '无标题')
    
    def _ensure_blog_summaries(self, blogs: List[Dict[str, Any]]) -> int:
        """
        确保所有博客都有摘要，如果没有则生成
        
        Args:
            blogs: 博客列表
        
        Returns:
            生成摘要的数量
        """
        if not self.llm:
            return 0
        
        from services.blog_generator.blog_service import extract_article_summary
        
        count = 0
        for blog in blogs:
            # 检查是否已有摘要
            if blog.get('summary'):
                continue
            
            # 生成摘要
            try:
                content = blog.get('markdown_content', '') or ''
                
                # 移除代码块，只保留文本内容用于摘要生成
                content_without_code = self._remove_code_blocks(content)
                
                summary = extract_article_summary(
                    llm_client=self.llm,
                    title=blog.get('topic', ''),
                    content=content_without_code,
                    max_length=500
                )
                
                if summary:
                    self.db.update_history_summary(blog['id'], summary)
                    blog['summary'] = summary  # 更新内存中的数据
                    count += 1
                    logger.info(f"生成博客摘要: {blog['id']} - {blog.get('topic', '')[:30]}")
            except Exception as e:
                logger.warning(f"生成博客摘要失败: {blog['id']}, {e}")
        
        return count
    
    def _get_existing_books_with_details(self) -> List[Dict[str, Any]]:
        """获取现有书籍及其详细信息"""
        books = self.db.list_books(status='active')
        
        for book in books:
            # 获取章节信息
            book['chapters'] = self.db.get_book_chapters(book['id'])
            # 获取关联的博客
            book['related_blogs'] = self.db.get_blogs_by_book(book['id'])
            # 解析大纲
            if book.get('outline'):
                try:
                    book['outline'] = json.loads(book['outline'])
                except json.JSONDecodeError:
                    book['outline'] = None
        
        return books
    
    # ========== 第一步：博客分类 ==========
    
    def _classify_blogs(
        self,
        unassigned_blogs: List[Dict[str, Any]],
        existing_books: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        第一步：调用 LLM 对博客进行分类
        
        Args:
            unassigned_blogs: 未分配的博客列表
            existing_books: 现有书籍列表
        
        Returns:
            分类结果
        """
        if not self.llm:
            logger.warning("LLM 客户端未配置，使用默认分类策略")
            return self._default_classification(unassigned_blogs, existing_books)
        
        # 构建博客信息（只需要标题和摘要）
        blogs_info = []
        for blog in unassigned_blogs:
            summary = blog.get('summary', '') or blog.get('markdown_content', '')[:300]
            blogs_info.append(f"博客ID: {blog['id']}\n标题: {blog.get('topic', '无标题')}\n摘要: {summary[:200]}")
        
        # 构建现有书籍信息
        books_info = []
        for book in existing_books:
            books_info.append(f"书籍ID: {book['id']}\n标题: {book['title']}\n主题: {book.get('theme', 'general')}\n描述: {book.get('description', '无')}")
        
        prompt_manager = get_prompt_manager()
        prompt = prompt_manager.render_book_classifier(
            existing_books_info="\n---\n".join(books_info) if books_info else "暂无现有书籍",
            blogs_info="\n---\n".join(blogs_info)
        )
        
        try:
            response = self.llm.chat(messages=[{"role": "user", "content": prompt}])
            response_text = response if isinstance(response, str) else response.get('content', '')
            
            # 提取 JSON
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                classification = json.loads(response_text[json_start:json_end])
            else:
                raise json.JSONDecodeError("No JSON found", response_text, 0)
                
            logger.info(f"LLM 分类完成: {len(classification.get('classifications', []))} 篇博客, "
                       f"{len(classification.get('new_books', []))} 本新书")
            return classification
            
        except Exception as e:
            logger.error(f"LLM 分类失败: {e}")
            return self._default_classification(unassigned_blogs, existing_books)
    
    def _default_classification(
        self,
        unassigned_blogs: List[Dict[str, Any]],
        existing_books: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """默认分类策略（无 LLM 时使用）"""
        if not unassigned_blogs:
            return {"classifications": [], "new_books": []}
        
        # 简单策略：创建一本通用书籍
        return {
            "classifications": [
                {
                    "blog_id": blog['id'],
                    "blog_title": blog.get('topic', ''),
                    "target_book": "new_book_1",
                    "reasoning": "默认分类"
                }
                for blog in unassigned_blogs
            ],
            "new_books": [{
                "temp_id": "new_book_1",
                "title": "技术博客合集",
                "theme": "general",
                "description": "自动聚合的技术博客文章"
            }]
        }
    
    def _apply_classification(
        self,
        classification: Dict[str, Any],
        unassigned_blogs: List[Dict[str, Any]],
        existing_books: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        应用分类结果：创建新书籍、关联博客到书籍
        
        Returns:
            {books_created, blogs_assigned, books_to_update}
        """
        result = {
            "books_created": 0,
            "blogs_assigned": 0,
            "books_to_update": []
        }
        
        blog_map = {blog['id']: blog for blog in unassigned_blogs}
        book_name_to_id = {}  # 书籍名称 -> book_id 映射
        book_blogs = {}  # book_id -> [blog_ids]
        
        # 构建 new_book_* 临时 ID 到书籍信息的映射
        new_books_map = {}
        for new_book in classification.get('new_books', []):
            temp_id = new_book.get('temp_id', '')
            new_books_map[temp_id] = new_book
        
        for item in classification.get('classifications', []):
            blog_id = item.get('blog_id')
            target_book = item.get('target_book', '')
            
            if not blog_id or blog_id not in blog_map:
                continue
            
            book_id = None
            book_title = ''
            book_theme = 'general'
            
            # 检查是否是 new_book_* 格式的临时 ID
            if target_book.startswith('new_book_'):
                # 从 new_books 列表中获取书籍信息
                new_book_info = new_books_map.get(target_book, {})
                book_title = new_book_info.get('title', target_book)
                book_theme = new_book_info.get('theme', 'general')
            else:
                # LLM 直接返回书籍名称
                book_title = target_book.strip('《》')
                if '(' in book_title:
                    # 提取主题
                    parts = book_title.split('(')
                    book_title = parts[0].strip()
                    theme_part = parts[1].lower().rstrip(')')
                    if 'ai' in theme_part:
                        book_theme = 'ai'
                    elif 'data' in theme_part:
                        book_theme = 'data'
                    elif 'web' in theme_part:
                        book_theme = 'web'
                    elif 'devops' in theme_part:
                        book_theme = 'devops'
                    elif 'security' in theme_part:
                        book_theme = 'security'
            
            # 查找已创建的同名书籍
            book_id = book_name_to_id.get(book_title)
            
            if not book_id:
                # 尝试模糊匹配
                for name, bid in book_name_to_id.items():
                    if book_title in name or name in book_title:
                        book_id = bid
                        break
            
            if not book_id:
                # 创建新书籍
                book_id = f"book_{uuid.uuid4().hex[:12]}"
                self.db.create_book(book_id, book_title, book_theme, '')
                book_name_to_id[book_title] = book_id
                result['books_created'] += 1
                result['books_to_update'].append(book_id)
                logger.info(f"创建新书籍: {book_id} - {book_title} ({book_theme})")
                
                # 生成封面
                try:
                    self.generate_book_cover(book_id)
                except Exception as e:
                    logger.warning(f"生成封面失败: {book_id}, {e}")
            
            # 记录博客归属
            if book_id not in book_blogs:
                book_blogs[book_id] = []
            book_blogs[book_id].append(blog_id)
            result['blogs_assigned'] += 1
        
        # 为每本书创建临时章节（后续大纲生成会覆盖）
        for book_id, blog_ids in book_blogs.items():
            chapters = []
            for idx, bid in enumerate(blog_ids):
                blog = blog_map.get(bid, {})
                chapters.append({
                    'chapter_index': idx + 1,
                    'chapter_title': blog.get('topic', f'章节 {idx + 1}'),
                    'section_index': f"{idx + 1}.1",
                    'section_title': blog.get('topic', f'内容 {idx + 1}'),
                    'blog_id': bid,
                    'has_content': 1,
                    'word_count': len(blog.get('markdown_content', ''))
                })
            
            self.db.save_book_chapters(book_id, chapters)
            
            # 更新博客的 book_id
            for bid in blog_ids:
                self.db.update_history_book_id(bid, book_id)
        
        return result
    
    # ========== 第二步：生成大纲 ==========
    
    def _generate_book_outline(self, book_id: str, old_outline_ref: Dict[str, Any] = None) -> bool:
        """
        第二步：为单本书籍生成教程大纲
        
        Args:
            book_id: 书籍ID
            old_outline_ref: 旧书籍大纲参考（可选）
        
        Returns:
            是否成功
        """
        book = self.db.get_book(book_id)
        if not book:
            logger.warning(f"书籍不存在: {book_id}")
            return False
        
        # 获取该书籍下的所有博客
        blogs = self.db.get_blogs_by_book(book_id)
        if not blogs:
            logger.warning(f"书籍没有关联博客: {book_id}")
            return False
        
        if not self.llm:
            logger.warning("LLM 客户端未配置，跳过大纲生成")
            return False
        
        # 构建博客信息（使用真实标题）
        blogs_info = []
        for blog in blogs:
            # 提取真实标题
            real_title = self._extract_blog_title(blog)
            summary = blog.get('summary', '') or blog.get('markdown_content', '')[:500]
            blogs_info.append(
                f"博客ID: {blog['id']}\n"
                f"标题: {real_title}\n"
                f"字数: {len(blog.get('markdown_content', ''))}\n"
                f"摘要: {summary[:300]}"
            )
        
        # 构建旧大纲参考信息
        old_outline_info = ""
        if old_outline_ref and old_outline_ref.get('chapters'):
            old_chapters = []
            for ch in old_outline_ref.get('chapters', []):
                ch_title = ch.get('title', '')
                sections = [s.get('title', '') for s in ch.get('sections', [])]
                old_chapters.append(f"- {ch_title}: {', '.join(sections[:3])}")
            old_outline_info = "\n【参考：之前的章节结构】\n" + "\n".join(old_chapters[:5]) + "\n（可参考但根据实际博客内容调整）\n"
        
        prompt_manager = get_prompt_manager()
        prompt = prompt_manager.render_book_outline_generator(
            book_title=book['title'],
            book_theme=book.get('theme', 'general'),
            book_description=book.get('description', '') + old_outline_info,
            blogs_info="\n---\n".join(blogs_info)
        )
        
        try:
            response = self.llm.chat(messages=[{"role": "user", "content": prompt}])
            response_text = response if isinstance(response, str) else response.get('content', '')
            
            # 提取 JSON
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                result = json.loads(response_text[json_start:json_end])
            else:
                raise json.JSONDecodeError("No JSON found", response_text, 0)
            
            outline = result.get('outline', {})
            
            # 保存大纲
            self.db.update_book(
                book_id,
                outline=json.dumps(outline, ensure_ascii=False)
            )
            
            # 构建博客ID到真实标题的映射
            blog_titles = {blog['id']: self._extract_blog_title(blog) for blog in blogs}
            
            # 更新章节结构（使用博客真实标题）
            chapters = self._outline_to_chapters(outline, blog_titles)
            self.db.save_book_chapters(book_id, chapters)
            
            # 更新书籍统计
            self.db.update_book(
                book_id,
                chapters_count=len(outline.get('chapters', [])),
                blogs_count=len(blogs),
                total_word_count=sum(len(b.get('markdown_content', '')) for b in blogs)
            )
            
            # 生成首页内容（包含大纲扩展）
            try:
                from services.homepage_generator_service import HomepageGeneratorService
                from services.outline_expander_service import OutlineExpanderService
                
                # 初始化大纲扩展服务
                outline_expander = OutlineExpanderService(self.db, self.llm)
                homepage_service = HomepageGeneratorService(self.db, self.llm, outline_expander)
                homepage_service.generate_homepage(book_id)
                logger.info(f"生成书籍首页: {book_id}")
            except Exception as e:
                logger.warning(f"生成首页失败: {e}")
            
            logger.info(f"大纲生成完成: {book['title']}, {len(chapters)} 个章节")
            return True
            
        except Exception as e:
            logger.error(f"生成大纲失败: {book_id}, {e}")
            return False
    
    def _outline_to_chapters(self, outline: Dict[str, Any], blog_titles: Dict[str, str] = None) -> List[Dict[str, Any]]:
        """
        将大纲结构转换为章节列表（支持系列文章）
        
        Args:
            outline: 大纲字典
            blog_titles: 博客ID到原始标题的映射，用于覆盖LLM生成的标题
            
        Returns:
            章节列表
        """
        chapters = []
        used_blog_ids = set()  # 防止同一博客重复出现
        blog_titles = blog_titles or {}
        
        for chapter in outline.get('chapters', []):
            chapter_index = chapter.get('index', 1)
            chapter_title = chapter.get('title', '')
            
            for section in chapter.get('sections', []):
                section_type = section.get('type', 'single')
                
                if section_type == 'series':
                    # 系列文章：展开为多个章节记录
                    for article in section.get('articles', []):
                        blog_id = article.get('blog_id')
                        # 跳过重复的博客
                        if blog_id and blog_id in used_blog_ids:
                            logger.warning(f"跳过重复的博客: {blog_id}")
                            continue
                        if blog_id:
                            used_blog_ids.add(blog_id)
                        
                        # 优先使用博客原始标题
                        section_title = blog_titles.get(blog_id) or article.get('title', '')
                        
                        chapters.append({
                            'chapter_index': chapter_index,
                            'chapter_title': chapter_title,
                            'section_index': f"{section.get('index', '')}.{article.get('order', 1)}",
                            'section_title': section_title,
                            'blog_id': blog_id,
                            'word_count': 0,  # 后续可以从博客获取
                            'series_title': section.get('title', ''),
                            'series_order': article.get('order', 1),
                            'series_total': article.get('total', 1)
                        })
                else:
                    # 单篇文章
                    blog_id = section.get('blog_id')
                    # 跳过重复的博客
                    if blog_id and blog_id in used_blog_ids:
                        logger.warning(f"跳过重复的博客: {blog_id}")
                        continue
                    if blog_id:
                        used_blog_ids.add(blog_id)
                    
                    # 优先使用博客原始标题
                    section_title = blog_titles.get(blog_id) or section.get('title', '')
                    
                    chapters.append({
                        'chapter_index': chapter_index,
                        'chapter_title': chapter_title,
                        'section_index': section.get('index', ''),
                        'section_title': section_title,
                        'blog_id': blog_id,
                        'word_count': 0
                    })
        
        return chapters
    
    def rescan_book(self, book_id: str) -> Dict[str, Any]:
        """
        重新扫描单本书籍，智能优化大纲
        
        Args:
            book_id: 书籍 ID
        
        Returns:
            更新结果
        """
        book = self.db.get_book(book_id)
        if not book:
            return {"status": "error", "message": "书籍不存在"}
        
        # 获取书籍关联的博客
        blogs = self.db.get_blogs_by_book(book_id)
        
        if not blogs:
            return {"status": "success", "message": "书籍没有关联的博客"}
        
        # 调用 LLM 重新生成大纲（智能优化）
        if self.llm:
            new_outline = self._regenerate_outline(book, blogs)
            if new_outline:
                # 保存优化后的大纲
                self.db.update_book(book_id, outline=json.dumps(new_outline, ensure_ascii=False))
                
                # 构建博客ID到真实标题的映射
                blog_titles = {blog['id']: self._extract_blog_title(blog) for blog in blogs}
                
                # 根据新大纲重建章节列表（使用博客真实标题）
                new_chapters = self._outline_to_chapters(new_outline, blog_titles)
                if new_chapters:
                    self.db.save_book_chapters(book_id, new_chapters)
                    
                    # 更新统计
                    total_word_count = sum(c.get('word_count', 0) for c in new_chapters)
                    blogs_count = len([c for c in new_chapters if c.get('blog_id')])
                    chapters_count = len(set(c.get('chapter_index') for c in new_chapters))
                    
                    self.db.update_book(
                        book_id,
                        chapters_count=chapters_count,
                        total_word_count=total_word_count,
                        blogs_count=blogs_count
                    )
                    
                    logger.info(f"书籍大纲已优化: {book['title']}, {chapters_count} 章, {blogs_count} 篇博客")
                    
                    # 重新生成首页内容（包含大纲扩展）
                    try:
                        from services.homepage_generator_service import HomepageGeneratorService
                        from services.outline_expander_service import OutlineExpanderService
                        
                        outline_expander = OutlineExpanderService(self.db, self.llm)
                        homepage_service = HomepageGeneratorService(self.db, self.llm, outline_expander)
                        homepage_service.generate_homepage(book_id)
                        logger.info(f"书籍首页已更新: {book['title']}")
                    except Exception as e:
                        logger.warning(f"更新首页失败: {e}")
        
        return {
            "status": "success",
            "message": f"书籍 {book['title']} 已更新",
            "blogs_count": len(blogs)
        }
    
    def _regenerate_outline(self, book: Dict[str, Any], blogs: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """重新生成书籍大纲（支持智能优化）"""
        if not self.llm:
            return None
        
        blogs_info = []
        for blog in blogs:
            content = blog.get('markdown_content', '') or ''
            
            # 优先使用已保存的摘要
            summary = blog.get('summary', '')
            
            # 提取博客大纲
            outline = blog.get('outline', '')
            outline_summary = ''
            if outline:
                try:
                    outline_data = json.loads(outline) if isinstance(outline, str) else outline
                    sections = outline_data.get('sections', [])
                    outline_summary = ', '.join([s.get('title', '') for s in sections[:5]])
                except:
                    pass
            
            # 如果没有摘要，使用内容前 300 字
            if not summary:
                summary = content[:300].replace('\n', ' ') if content else ""
            
            blog_entry = f"""- 标题: {blog.get('topic', '无标题')}
  ID: {blog['id']}
  字数: {len(content)}
  章节: {outline_summary if outline_summary else '无'}
  摘要: {summary}"""
            blogs_info.append(blog_entry)
        
        prompt = f"""为以下书籍智能优化大纲：

书籍标题: {book['title']}
书籍描述: {book.get('description', '无')}

包含的博客:
{chr(10).join(blogs_info)}

【大纲优化策略】
1. **合并相似章节**：主题相似的博客合并为系列（如 "Redis 入门系列"）
2. **调整章节顺序**：按从入门到进阶的逻辑顺序排列
3. **系列文章标记**：相同主题的多篇博客使用 type: "series"

输出 JSON 格式：
{{
    "chapters": [
        {{
            "index": 1,
            "title": "章节标题",
            "sections": [
                {{"index": "1.1", "title": "单篇标题", "blog_id": "...", "type": "single"}},
                {{
                    "index": "1.2",
                    "title": "系列标题",
                    "type": "series",
                    "articles": [
                        {{"order": 1, "total": 2, "title": "第1篇", "blog_id": "..."}},
                        {{"order": 2, "total": 2, "title": "第2篇", "blog_id": "..."}}
                    ]
                }}
            ]
        }}
    ]
}}

直接返回 JSON。"""
        
        try:
            response = self.llm.chat(messages=[{"role": "user", "content": prompt}])
            response_text = response if isinstance(response, str) else response.get('content', '')
            
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                return json.loads(response_text[json_start:json_end])
        except Exception as e:
            logger.error(f"重新生成大纲失败: {e}")
        
        return None
    
    def generate_book_introduction(self, book_id: str) -> Optional[str]:
        """
        使用 LLM 生成书籍简介
        
        Args:
            book_id: 书籍 ID
        
        Returns:
            生成的简介文本
        """
        book = self.db.get_book(book_id)
        if not book:
            return None
        
        # 获取书籍关联的博客
        blogs = self.db.get_blogs_by_book(book_id)
        
        if not self.llm:
            return f"《{book['title']}》是一本关于{book.get('theme', '技术')}的教程书籍，包含 {len(blogs)} 篇精选博客文章。"
        
        # 构建章节信息
        chapters = self.db.get_book_chapters(book_id)
        chapters_grouped = {}
        for ch in chapters:
            idx = ch.get('chapter_index', 1)
            if idx not in chapters_grouped:
                chapters_grouped[idx] = {
                    'index': idx,
                    'title': ch.get('chapter_title', f'章节 {idx}'),
                    'sections': []
                }
            chapters_grouped[idx]['sections'].append({
                'index': ch.get('section_index', ''),
                'title': ch.get('section_title', '')
            })
        
        chapters_list = list(chapters_grouped.values())
        
        # 使用模板渲染 Prompt
        prompt_manager = get_prompt_manager()
        prompt = prompt_manager.render_book_introduction(
            book_title=book['title'],
            book_theme=book.get('theme', 'general'),
            chapters_count=len(chapters_list),
            chapters=chapters_list
        )
        
        try:
            response = self.llm.chat(messages=[{"role": "user", "content": prompt}])
            introduction = response if isinstance(response, str) else response.get('content', '')
            
            # 更新书籍描述
            if introduction:
                self.db.update_book(book_id, description=introduction.strip())
            
            return introduction.strip()
        except Exception as e:
            logger.error(f"生成书籍简介失败: {e}")
            return None
    
    def generate_book_cover(self, book_id: str) -> Optional[str]:
        """
        使用 nanoBanana 生成书籍封面
        
        Args:
            book_id: 书籍 ID
        
        Returns:
            封面图片 URL
        """
        book = self.db.get_book(book_id)
        if not book:
            logger.error(f"书籍不存在: {book_id}")
            return None
        
        # 检查是否已有封面
        if book.get('cover_image'):
            logger.info(f"书籍已有封面: {book_id}")
            return book['cover_image']
        
        try:
            # 导入图片服务
            from services.image_service import NanoBananaService, AspectRatio, ImageSize
            
            # 获取配置
            api_key = os.getenv('NANO_BANANA_API_KEY')
            api_base = os.getenv('NANO_BANANA_API_BASE', 'https://grsai.dakka.com.cn')
            model = os.getenv('NANO_BANANA_MODEL', 'nano-banana-pro')
            
            if not api_key:
                logger.warning("NANO_BANANA_API_KEY 未配置，跳过封面生成")
                return None
            
            image_service = NanoBananaService(
                api_key=api_key,
                api_base=api_base,
                model=model,
                output_folder="outputs/covers"
            )
            
            # 构建封面生成 Prompt - kawaii 风格
            theme = book.get('theme', 'general')
            theme_icon = THEME_ICONS.get(theme, '📖')
            
            # 主题对应的吉祥物描述
            theme_mascots = {
                'ai': 'a cute kawaii robot mascot with antenna, holding a glowing brain or neural network symbol',
                'web': 'a cute kawaii globe character with happy face, surrounded by connection lines',
                'data': 'a cute kawaii database mascot with charts and graphs floating around',
                'devops': 'a cute kawaii gear/cog character with tools and deployment symbols',
                'security': 'a cute kawaii shield mascot with a lock symbol, looking protective',
                'general': 'a cute kawaii book character with sparkles and stars'
            }
            mascot_desc = theme_mascots.get(theme, theme_mascots['general'])
            
            cover_prompt = f"""A cute kawaii-style mascot illustration for a tech tutorial book cover:

{mascot_desc}

Style requirements:
- Chibi/kawaii proportions with big head and small body
- Warm, friendly color palette (orange, yellow, soft pink, light blue)
- Simple clean background with small decorative elements (stars, gears, sparkles)
- Flat illustration style, soft pastel colors
- Centered composition, logo design suitable for book cover
- Minimalist, friendly and approachable aesthetic
- Professional yet playful tech tutorial vibe
- No text, only the mascot character and decorative elements"""
            
            logger.info(f"开始生成书籍封面: {book['title']}")
            
            # 调用 nanoBanana 生成封面
            result = image_service.generate(
                prompt=cover_prompt,
                aspect_ratio=AspectRatio.PORTRAIT_3_4,
                image_size=ImageSize.SIZE_2K,
                download=True
            )
            
            if result and result.url:
                # 保存封面 URL 到数据库
                # 优先使用本地路径（如果有的话）
                cover_url = f"/outputs/covers/{os.path.basename(result.local_path)}" if result.local_path else result.url
                self.db.update_book(book_id, cover_image=cover_url)
                logger.info(f"书籍封面生成成功: {book_id} -> {cover_url}")
                return cover_url
            else:
                logger.warning(f"书籍封面生成失败: {book_id}")
                return None
                
        except Exception as e:
            logger.error(f"生成书籍封面失败: {e}", exc_info=True)
            return None
    
    def generate_covers_for_all_books(self) -> Dict[str, Any]:
        """
        为所有没有封面的书籍生成封面
        
        Returns:
            生成结果统计
        """
        books = self.db.list_books(status='active')
        
        result = {
            "total": len(books),
            "generated": 0,
            "skipped": 0,
            "failed": 0,
            "details": []
        }
        
        for book in books:
            if book.get('cover_image'):
                result['skipped'] += 1
                result['details'].append({
                    "book_id": book['id'],
                    "title": book['title'],
                    "status": "skipped",
                    "reason": "已有封面"
                })
                continue
            
            cover_url = self.generate_book_cover(book['id'])
            
            if cover_url:
                result['generated'] += 1
                result['details'].append({
                    "book_id": book['id'],
                    "title": book['title'],
                    "status": "success",
                    "cover_url": cover_url
                })
            else:
                result['failed'] += 1
                result['details'].append({
                    "book_id": book['id'],
                    "title": book['title'],
                    "status": "failed"
                })
        
        logger.info(f"批量生成封面完成: 成功 {result['generated']}, 跳过 {result['skipped']}, 失败 {result['failed']}")
        return result
