"""
arXiv 搜索服务 - 学术论文搜索
"""

import logging
import requests
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional
from urllib.parse import quote

logger = logging.getLogger(__name__)

# 全局 arXiv 服务实例
_arxiv_service: Optional['ArxivService'] = None


class ArxivService:
    """
    arXiv 搜索服务 - 用于搜索学术论文
    API 文档: https://info.arxiv.org/help/api/basics.html
    """
    
    BASE_URL = "https://export.arxiv.org/api/query"
    
    def __init__(self):
        """初始化 arXiv 服务"""
        pass
    
    def is_available(self) -> bool:
        """检查服务是否可用（arXiv API 免费无需 Key）"""
        return True
    
    def search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """
        搜索 arXiv 论文
        
        Args:
            query: 搜索关键词（英文效果更好）
            max_results: 最大结果数
            
        Returns:
            {
                'success': True/False,
                'results': [...],
                'summary': '...',
                'error': '...'
            }
        """
        try:
            logger.info(f"🔬 arXiv 搜索: {query}")
            
            # 构建请求参数
            params = {
                'search_query': f'all:{query}',
                'start': 0,
                'max_results': min(max_results, 20),
                'sortBy': 'relevance',
                'sortOrder': 'descending'
            }
            
            response = requests.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            
            # 解析 XML 响应
            results = self._parse_response(response.text)
            
            logger.info(f"🔬 arXiv 搜索完成，获取 {len(results)} 篇论文")
            
            return {
                'success': True,
                'results': results,
                'summary': self._generate_summary(results),
                'error': None,
                'source': 'arxiv'
            }
            
        except Exception as e:
            logger.error(f"arXiv 搜索失败: {e}")
            return {
                'success': False,
                'results': [],
                'summary': '',
                'error': str(e),
                'source': 'arxiv'
            }
    
    def _parse_response(self, xml_text: str) -> List[Dict[str, Any]]:
        """解析 arXiv API XML 响应"""
        results = []
        
        # 解析 XML
        root = ET.fromstring(xml_text)
        
        # arXiv 使用 Atom 命名空间
        ns = {
            'atom': 'http://www.w3.org/2005/Atom',
            'arxiv': 'http://arxiv.org/schemas/atom'
        }
        
        for entry in root.findall('atom:entry', ns):
            try:
                # 提取论文信息
                title = entry.find('atom:title', ns)
                summary = entry.find('atom:summary', ns)
                published = entry.find('atom:published', ns)
                link = entry.find("atom:link[@type='text/html']", ns)
                if link is None:
                    link = entry.find("atom:link[@rel='alternate']", ns)
                
                # 提取作者
                authors = []
                for author in entry.findall('atom:author', ns):
                    name = author.find('atom:name', ns)
                    if name is not None and name.text:
                        authors.append(name.text)
                
                # 提取 arXiv ID
                arxiv_id = entry.find('atom:id', ns)
                arxiv_id_text = ''
                if arxiv_id is not None and arxiv_id.text:
                    # 从 URL 中提取 ID，如 http://arxiv.org/abs/2401.12345
                    arxiv_id_text = arxiv_id.text.split('/')[-1]
                
                results.append({
                    'title': title.text.strip().replace('\n', ' ') if title is not None and title.text else '',
                    'url': link.get('href') if link is not None else '',
                    'content': summary.text.strip().replace('\n', ' ')[:1500] if summary is not None and summary.text else '',
                    'source': 'arXiv',
                    'publish_date': published.text[:10] if published is not None and published.text else '',
                    'authors': ', '.join(authors[:3]) + ('...' if len(authors) > 3 else ''),
                    'arxiv_id': arxiv_id_text
                })
                
            except Exception as e:
                logger.warning(f"解析 arXiv entry 失败: {e}")
                continue
        
        return results
    
    def _generate_summary(self, results: List[Dict[str, Any]]) -> str:
        """从搜索结果生成摘要"""
        if not results:
            return ''
        
        summary_parts = []
        for i, item in enumerate(results, 1):
            title = item.get('title', '')
            content = item.get('content', '')[:500]
            arxiv_id = item.get('arxiv_id', '')
            authors = item.get('authors', '')
            
            summary_parts.append(
                f"[论文 {i}] {title}\n"
                f"arXiv: {arxiv_id} | 作者: {authors}\n"
                f"摘要: {content}"
            )
        
        return '\n\n'.join(summary_parts)


def get_arxiv_service() -> Optional[ArxivService]:
    """获取 arXiv 服务实例"""
    global _arxiv_service
    if _arxiv_service is None:
        _arxiv_service = ArxivService()
    return _arxiv_service
