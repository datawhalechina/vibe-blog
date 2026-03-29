"""
大纲扩展服务 - 基于书籍主题生成完整内容大纲
"""
import json
import logging
from typing import Dict, Any, List, Optional

from services.database_service import DatabaseService
from services.blog_generator.prompts import get_prompt_manager

logger = logging.getLogger(__name__)


class OutlineExpanderService:
    """大纲扩展服务"""
    
    def __init__(self, db: DatabaseService, llm_client=None, search_service=None):
        """
        初始化大纲扩展服务
        
        Args:
            db: 数据库服务
            llm_client: LLM 客户端
            search_service: 搜索服务
        """
        self.db = db
        self.llm = llm_client
        self.search = search_service
        self.prompt_manager = get_prompt_manager()
    
    def expand_outline(self, book_id: str) -> Dict[str, Any]:
        """
        扩展书籍大纲
        
        Args:
            book_id: 书籍 ID
            
        Returns:
            完整大纲字典
        """
        book = self.db.get_book(book_id)
        if not book:
            logger.error(f"书籍不存在: {book_id}")
            return {}
        
        existing_chapters = self.db.get_book_chapters(book_id)
        logger.info(f"扩展大纲: {book['title']}, 已有 {len(existing_chapters)} 个章节")
        
        # 1. 搜索相关资料（可选）
        search_results = []
        if self.search:
            try:
                search_results = self._search_related_content(book['title'], book.get('theme', 'general'))
            except Exception as e:
                logger.warning(f"搜索相关资料失败: {e}")
        
        # 2. 生成完整大纲
        full_outline = self._generate_full_outline(book, existing_chapters, search_results)
        
        # 3. 合并相似章节
        merged_outline = self._merge_similar_sections(full_outline, existing_chapters)
        
        # 4. 标记建设状态
        marked_outline = self._mark_build_status(merged_outline, existing_chapters)
        
        # 5. 保存到数据库
        self.db.update_book_full_outline(book_id, marked_outline)
        
        # 统计扩展后的章节数
        expanded_count = len(marked_outline.get('chapters', []))
        logger.info(f"大纲扩展完成: {book['title']}, 扩展后共 {expanded_count} 个章节")
        return marked_outline
    
    def _search_related_content(self, title: str, theme: str) -> List[Dict[str, Any]]:
        """搜索相关内容"""
        if not self.search:
            return []
        
        query = f"{title} 教程 入门 实战"
        try:
            results = self.search.search(query)
            return results[:10] if results else []
        except Exception as e:
            logger.warning(f"搜索失败: {e}")
            return []
    
    def _generate_full_outline(
        self,
        book: Dict[str, Any],
        existing: List[Dict[str, Any]],
        search_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """使用 LLM 生成完整大纲"""
        if not self.llm:
            # 无 LLM 时，使用现有大纲
            return self._build_outline_from_existing(book, existing)
        
        prompt = self.prompt_manager.render_outline_expander(
            book=book,
            existing_chapters=existing,
            search_results=search_results
        )
        
        try:
            response = self.llm.chat(messages=[{"role": "user", "content": prompt}])
            response_text = response if isinstance(response, str) else response.get('content', '')
            
            # 提取 JSON
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                return json.loads(response_text[json_start:json_end])
        except Exception as e:
            logger.error(f"生成大纲失败: {e}")
        
        # 降级：使用现有大纲
        return self._build_outline_from_existing(book, existing)
    
    def _build_outline_from_existing(
        self,
        book: Dict[str, Any],
        existing: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """从现有章节构建大纲"""
        # 尝试解析现有大纲
        if book.get('outline'):
            try:
                if isinstance(book['outline'], str):
                    return json.loads(book['outline'])
                return book['outline']
            except:
                pass
        
        # 从章节列表构建
        chapters_map = {}
        for ch in existing:
            idx = ch.get('chapter_index', 1)
            if idx not in chapters_map:
                chapters_map[idx] = {
                    'index': idx,
                    'title': ch.get('chapter_title', f'章节 {idx}'),
                    'sections': []
                }
            chapters_map[idx]['sections'].append({
                'index': ch.get('section_index', ''),
                'title': ch.get('section_title', ''),
                'type': 'single'
            })
        
        return {'chapters': list(chapters_map.values())}
    
    def _merge_similar_sections(
        self,
        outline: Dict[str, Any],
        existing: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """合并相似主题的章节为系列"""
        for chapter in outline.get('chapters', []):
            sections = chapter.get('sections', [])
            merged = []
            used = set()
            
            for i, section in enumerate(sections):
                if i in used:
                    continue
                
                # 如果已经是系列，直接添加
                if section.get('type') == 'series':
                    merged.append(section)
                    used.add(i)
                    continue
                
                # 查找相似的章节
                similar = [section]
                for j, other in enumerate(sections[i+1:], i+1):
                    if j in used:
                        continue
                    if other.get('type') == 'series':
                        continue
                    if self._is_similar(section.get('title', ''), other.get('title', '')):
                        similar.append(other)
                        used.add(j)
                
                if len(similar) > 1:
                    # 合并为系列
                    series_title = self._extract_series_title(similar)
                    merged.append({
                        'title': f"{series_title}系列",
                        'type': 'series',
                        'articles': [
                            {'order': idx+1, 'total': len(similar), 'title': s.get('title', '')}
                            for idx, s in enumerate(similar)
                        ]
                    })
                else:
                    section['type'] = 'single'
                    merged.append(section)
                
                used.add(i)
            
            chapter['sections'] = merged
        
        return outline
    
    def _is_similar(self, title1: str, title2: str) -> bool:
        """判断两个标题是否相似"""
        if not title1 or not title2:
            return False
        
        # 提取关键词
        def extract_keywords(title):
            # 移除常见词
            stop_words = {'的', '与', '和', '从', '到', '在', '是', '了', '：', ':', '-', '—'}
            words = set()
            for word in title.split():
                if word not in stop_words and len(word) > 1:
                    words.add(word)
            # 也按中文分词
            for i in range(len(title) - 1):
                if title[i:i+2] not in stop_words:
                    words.add(title[i:i+2])
            return words
        
        words1 = extract_keywords(title1)
        words2 = extract_keywords(title2)
        
        if not words1 or not words2:
            return False
        
        common = words1 & words2
        # 至少有 2 个共同关键词，或者共同词占比超过 50%
        return len(common) >= 2 or len(common) / min(len(words1), len(words2)) > 0.5
    
    def _extract_series_title(self, sections: List[Dict[str, Any]]) -> str:
        """提取系列标题"""
        titles = [s.get('title', '') for s in sections]
        if not titles:
            return "系列"
        
        # 找出共同的前缀
        first = titles[0]
        if '：' in first:
            return first.split('：')[0]
        if ':' in first:
            return first.split(':')[0]
        if ' ' in first:
            return first.split(' ')[0]
        
        return first[:15] if len(first) > 15 else first
    
    def _mark_build_status(
        self,
        outline: Dict[str, Any],
        existing: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """标记每个章节的建设状态"""
        # 构建现有章节映射
        existing_map = {}
        for ch in existing:
            title = ch.get('section_title', '')
            if title:
                existing_map[title] = ch
        
        for chapter in outline.get('chapters', []):
            for section in chapter.get('sections', []):
                if section.get('type') == 'series':
                    # 系列文章
                    all_built = True
                    for article in section.get('articles', []):
                        title = article.get('title', '')
                        if title in existing_map:
                            article['status'] = 'built'
                            article['blog_id'] = existing_map[title].get('blog_id')
                            article['chapter_id'] = existing_map[title].get('id')
                        else:
                            article['status'] = 'pending'
                            all_built = False
                    section['status'] = 'built' if all_built else 'partial'
                else:
                    # 单个章节
                    title = section.get('title', '')
                    if title in existing_map:
                        section['status'] = 'built'
                        section['blog_id'] = existing_map[title].get('blog_id')
                        section['chapter_id'] = existing_map[title].get('id')
                    else:
                        section['status'] = 'pending'
        
        return outline
