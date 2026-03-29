"""
知识服务 - 管理和融合多来源知识

一期简化策略：
- 整个文档作为 1 条知识，不分块
- 基于标题/文件名去重
- 文档知识优先于网络搜索

二期增强：
- 支持知识分块
- 两级结构：文档摘要 + 分块内容
- 图片摘要整合
"""
import os
import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Literal

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeItem:
    """知识条目（一期简化版）"""
    source_type: Literal['document', 'web_search']  # 来源类型
    title: str                                       # 标题
    content: str                                     # 内容（一期：整个文档内容）
    url: Optional[str] = None                        # 网络来源 URL
    file_name: Optional[str] = None                  # 文档文件名
    relevance_score: float = 0.0                     # 相关性评分
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'source_type': self.source_type,
            'title': self.title,
            'content': self.content,
            'url': self.url,
            'file_name': self.file_name,
            'relevance_score': self.relevance_score
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KnowledgeItem':
        """从字典创建"""
        return cls(
            source_type=data.get('source_type', 'document'),
            title=data.get('title', ''),
            content=data.get('content', ''),
            url=data.get('url'),
            file_name=data.get('file_name'),
            relevance_score=data.get('relevance_score', 0.0)
        )


class KnowledgeService:
    """
    知识服务（一期简化版）
    
    功能：
    - 将文档内容转换为知识条目
    - 融合文档知识和网络搜索知识
    - 简单去重
    """
    
    def __init__(self, max_content_length: int = 8000):
        """
        初始化知识服务
        
        Args:
            max_content_length: 单条知识最大长度（超过则截断）
        """
        self.max_content_length = max_content_length
        logger.info(f"KnowledgeService 初始化完成, max_content_length={max_content_length}")
    
    def prepare_document_knowledge(
        self, 
        documents: List[Dict[str, Any]]
    ) -> List[KnowledgeItem]:
        """
        将文档转换为知识条目（一期简化：整个文档 = 1 条知识）
        
        Args:
            documents: 文档列表，每个文档包含 {filename, markdown_content, ...}
        
        Returns:
            知识条目列表
        """
        items = []
        
        for doc in documents:
            filename = doc.get('filename', '')
            markdown = doc.get('markdown_content', '')
            
            if not markdown:
                logger.warning(f"文档 {filename} 内容为空，跳过")
                continue
            
            # 提取标题
            title = self._extract_title(markdown) or filename
            
            # 截断内容（一期简化）
            content = self._truncate_content(markdown)
            
            item = KnowledgeItem(
                source_type='document',
                title=title,
                content=content,
                file_name=filename,
                relevance_score=1.0  # 文档知识默认高相关性
            )
            items.append(item)
            
            logger.info(f"准备文档知识: {title}, 长度={len(content)}")
        
        return items
    
    def convert_search_results(
        self, 
        search_results: List[Dict[str, Any]]
    ) -> List[KnowledgeItem]:
        """
        将网络搜索结果转换为知识条目
        
        Args:
            search_results: 搜索结果列表
        
        Returns:
            知识条目列表
        """
        items = []
        
        for result in search_results:
            title = result.get('title', '')
            content = result.get('content', '')
            url = result.get('url', '')
            
            if not content:
                continue
            
            item = KnowledgeItem(
                source_type='web_search',
                title=title,
                content=content,
                url=url,
                relevance_score=0.5  # 网络搜索默认中等相关性
            )
            items.append(item)
        
        return items
    
    def get_merged_knowledge(
        self,
        document_knowledge: List[KnowledgeItem],
        web_knowledge: List[KnowledgeItem],
        max_items: int = 20
    ) -> List[KnowledgeItem]:
        """
        融合文档知识和网络搜索知识
        
        策略：
        1. 文档知识优先（最多 10 条）
        2. 网络知识补充
        3. 简单去重（基于标题/文件名）
        
        Args:
            document_knowledge: 文档知识列表
            web_knowledge: 网络搜索知识列表
            max_items: 最大返回条目数
        
        Returns:
            融合后的知识列表
        """
        result = []
        
        # 1. 添加文档知识（数量从配置读取）
        max_doc_items = int(os.getenv('KNOWLEDGE_MAX_DOC_ITEMS', '10'))
        doc_count = min(len(document_knowledge), max_doc_items)
        result.extend(document_knowledge[:doc_count])
        logger.info(f"添加文档知识: {doc_count} 条")
        
        # 2. 添加网络知识（去重）
        web_added = 0
        for web_item in web_knowledge:
            if len(result) >= max_items:
                break
            
            if not self._is_duplicate_simple(web_item, result):
                result.append(web_item)
                web_added += 1
        
        logger.info(f"添加网络知识: {web_added} 条")
        logger.info(f"融合完成: 共 {len(result)} 条知识")
        
        return result
    
    def summarize_for_prompt(
        self,
        knowledge_items: List[KnowledgeItem],
        max_total_length: int = 30000
    ) -> Dict[str, Any]:
        """
        将知识条目整理为 Prompt 可用的格式
        
        Args:
            knowledge_items: 知识条目列表
            max_total_length: 最大总长度
        
        Returns:
            {
                'background_knowledge': str,  # 背景知识文本
                'document_references': list,  # 文档来源列表
                'web_references': list        # 网络来源列表
            }
        """
        doc_refs = []
        web_refs = []
        knowledge_parts = []
        total_length = 0
        
        for item in knowledge_items:
            # 检查长度限制
            if total_length + len(item.content) > max_total_length:
                # 截断
                remaining = max_total_length - total_length
                if remaining > 500:
                    truncated = item.content[:remaining] + "\n...(内容已截断)"
                    knowledge_parts.append(f"### {item.title}\n\n{truncated}")
                break
            
            knowledge_parts.append(f"### {item.title}\n\n{item.content}")
            total_length += len(item.content)
            
            # 收集引用
            if item.source_type == 'document':
                doc_refs.append({
                    'title': item.title,
                    'file_name': item.file_name
                })
            else:
                web_refs.append({
                    'title': item.title,
                    'url': item.url
                })
        
        background_knowledge = "\n\n---\n\n".join(knowledge_parts)
        
        return {
            'background_knowledge': background_knowledge,
            'document_references': doc_refs,
            'web_references': web_refs
        }
    
    def _extract_title(self, markdown: str) -> Optional[str]:
        """从 Markdown 中提取标题"""
        # 尝试匹配 # 标题
        match = re.search(r'^#\s+(.+)$', markdown, re.MULTILINE)
        if match:
            return match.group(1).strip()
        
        # 尝试匹配第一行非空内容
        lines = markdown.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                # 截取前 50 个字符作为标题
                return line[:50] + ('...' if len(line) > 50 else '')
        
        return None
    
    def _truncate_content(self, content: str) -> str:
        """截断内容到最大长度"""
        if len(content) <= self.max_content_length:
            return content
        
        truncated = content[:self.max_content_length]
        return truncated + f"\n\n...(内容已截断，原文共 {len(content)} 字符)"
    
    def _is_duplicate_simple(
        self, 
        item: KnowledgeItem, 
        existing: List[KnowledgeItem]
    ) -> bool:
        """
        简单去重（一期）：基于标题/文件名
        
        Args:
            item: 待检查的知识条目
            existing: 已有的知识条目列表
        
        Returns:
            是否重复
        """
        for e in existing:
            # 同一文件
            if item.file_name and item.file_name == e.file_name:
                return True
            # 标题相同
            if item.title and item.title == e.title:
                return True
        return False
    
    # ========== 二期新增：两级结构检索 ==========
    
    def prepare_chunked_knowledge(
        self,
        documents: List[Dict[str, Any]],
        chunks: List[Dict[str, Any]],
        images: List[Dict[str, Any]] = None
    ) -> List[KnowledgeItem]:
        """
        准备分块知识（二期）
        
        两级结构：
        1. 文档级：摘要 + 元信息
        2. 分块级：具体内容片段
        
        Args:
            documents: 文档列表，包含 {filename, summary, ...}
            chunks: 分块列表，包含 {document_id, title, content, ...}
            images: 图片列表，包含 {document_id, caption, ...}
        
        Returns:
            知识条目列表
        """
        items = []
        images = images or []
        
        # 按文档 ID 分组
        doc_map = {doc.get('id'): doc for doc in documents}
        chunks_by_doc = {}
        images_by_doc = {}
        
        for chunk in chunks:
            doc_id = chunk.get('document_id')
            if doc_id not in chunks_by_doc:
                chunks_by_doc[doc_id] = []
            chunks_by_doc[doc_id].append(chunk)
        
        for img in images:
            doc_id = img.get('document_id')
            if doc_id not in images_by_doc:
                images_by_doc[doc_id] = []
            images_by_doc[doc_id].append(img)
        
        # 为每个文档创建知识条目
        for doc_id, doc in doc_map.items():
            filename = doc.get('filename', '')
            summary = doc.get('summary', '')
            doc_chunks = chunks_by_doc.get(doc_id, [])
            doc_images = images_by_doc.get(doc_id, [])
            
            # 1. 文档级摘要（如果有）
            if summary:
                items.append(KnowledgeItem(
                    source_type='document',
                    title=f"{filename} - 摘要",
                    content=summary,
                    file_name=filename,
                    relevance_score=1.0
                ))
            
            # 2. 分块级内容
            for chunk in doc_chunks:
                chunk_title = chunk.get('title', '')
                chunk_content = chunk.get('content', '')
                
                if not chunk_content:
                    continue
                
                # 截断过长内容
                content = self._truncate_content(chunk_content)
                
                items.append(KnowledgeItem(
                    source_type='document',
                    title=f"{filename} - {chunk_title}" if chunk_title else filename,
                    content=content,
                    file_name=filename,
                    relevance_score=0.9
                ))
            
            # 3. 图片摘要（作为补充知识）
            if doc_images:
                image_captions = []
                for img in doc_images:
                    caption = img.get('caption', '')
                    if caption:
                        page_num = img.get('page_num', 0)
                        image_captions.append(f"- 第{page_num}页图片: {caption}")
                
                if image_captions:
                    items.append(KnowledgeItem(
                        source_type='document',
                        title=f"{filename} - 图片内容",
                        content="\n".join(image_captions),
                        file_name=filename,
                        relevance_score=0.7
                    ))
        
        logger.info(f"准备分块知识: {len(items)} 条 (来自 {len(documents)} 个文档)")
        return items
    
    def get_merged_knowledge_v2(
        self,
        documents: List[Dict[str, Any]],
        chunks: List[Dict[str, Any]],
        images: List[Dict[str, Any]],
        web_knowledge: List[KnowledgeItem],
        max_items: int = 30
    ) -> List[KnowledgeItem]:
        """
        融合分块知识和网络搜索知识（二期）
        
        策略：
        1. 文档摘要优先
        2. 相关分块补充
        3. 网络知识填充
        
        Args:
            documents: 文档列表
            chunks: 分块列表
            images: 图片列表
            web_knowledge: 网络搜索知识
            max_items: 最大返回条目数
        
        Returns:
            融合后的知识列表
        """
        # 准备分块知识
        doc_knowledge = self.prepare_chunked_knowledge(documents, chunks, images)
        
        result = []
        max_doc_items = int(os.getenv('KNOWLEDGE_MAX_DOC_ITEMS', '10'))
        
        # 1. 添加文档知识（按相关性排序）
        doc_knowledge.sort(key=lambda x: x.relevance_score, reverse=True)
        doc_count = min(len(doc_knowledge), max_doc_items)
        result.extend(doc_knowledge[:doc_count])
        logger.info(f"添加文档知识: {doc_count} 条")
        
        # 2. 添加网络知识（去重）
        web_added = 0
        for web_item in web_knowledge:
            if len(result) >= max_items:
                break
            
            if not self._is_duplicate_simple(web_item, result):
                result.append(web_item)
                web_added += 1
        
        logger.info(f"添加网络知识: {web_added} 条")
        logger.info(f"融合完成 (v2): 共 {len(result)} 条知识")
        
        return result
    
    def summarize_for_prompt_v2(
        self,
        knowledge_items: List[KnowledgeItem],
        max_total_length: int = 30000
    ) -> Dict[str, Any]:
        """
        将知识条目整理为 Prompt 可用的格式（二期增强）
        
        增强：按文档分组展示
        
        Args:
            knowledge_items: 知识条目列表
            max_total_length: 最大总长度
        
        Returns:
            {
                'background_knowledge': str,
                'document_references': list,
                'web_references': list,
                'knowledge_stats': dict
            }
        """
        doc_refs = []
        web_refs = []
        
        # 按来源分组
        doc_items = [i for i in knowledge_items if i.source_type == 'document']
        web_items = [i for i in knowledge_items if i.source_type == 'web_search']
        
        knowledge_parts = []
        total_length = 0
        
        # 文档知识
        if doc_items:
            knowledge_parts.append("## 📚 文档知识\n")
            seen_files = set()
            
            for item in doc_items:
                if total_length + len(item.content) > max_total_length:
                    remaining = max_total_length - total_length
                    if remaining > 500:
                        truncated = item.content[:remaining] + "\n...(内容已截断)"
                        knowledge_parts.append(f"### {item.title}\n\n{truncated}")
                    break
                
                knowledge_parts.append(f"### {item.title}\n\n{item.content}")
                total_length += len(item.content)
                
                if item.file_name and item.file_name not in seen_files:
                    doc_refs.append({
                        'title': item.title.split(' - ')[0] if ' - ' in item.title else item.title,
                        'file_name': item.file_name
                    })
                    seen_files.add(item.file_name)
        
        # 网络知识
        if web_items and total_length < max_total_length:
            knowledge_parts.append("\n## 🌐 网络知识\n")
            
            for item in web_items:
                if total_length + len(item.content) > max_total_length:
                    break
                
                knowledge_parts.append(f"### {item.title}\n\n{item.content}")
                total_length += len(item.content)
                
                web_refs.append({
                    'title': item.title,
                    'url': item.url
                })
        
        background_knowledge = "\n\n".join(knowledge_parts)
        
        return {
            'background_knowledge': background_knowledge,
            'document_references': doc_refs,
            'web_references': web_refs,
            'knowledge_stats': {
                'doc_items': len(doc_items),
                'web_items': len(web_items),
                'total_length': total_length
            }
        }


# 全局单例
_knowledge_service: Optional[KnowledgeService] = None


def get_knowledge_service() -> KnowledgeService:
    """获取知识服务单例"""
    global _knowledge_service
    if _knowledge_service is None:
        _knowledge_service = KnowledgeService()
    return _knowledge_service


def init_knowledge_service(max_content_length: int = 8000) -> KnowledgeService:
    """初始化知识服务"""
    global _knowledge_service
    _knowledge_service = KnowledgeService(max_content_length=max_content_length)
    return _knowledge_service
