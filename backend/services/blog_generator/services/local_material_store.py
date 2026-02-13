"""
75.06 LocalMaterialStore — 本地博客素材库

文件存储 + JSON 索引，支持关键词搜索。
Crawl4AI 爬取的高质量博客文章缓存在本地，搜索时毫秒级命中。
"""
import json
import logging
import os
import re
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class LocalMaterialStore:
    """本地博客素材库 — Markdown 文件 + JSON 索引"""

    def __init__(self, base_dir: str = "materials"):
        self.base_dir = base_dir
        self.index_path = os.path.join(base_dir, "index.json")
        self._index: List[Dict] = []
        self._url_set: set = set()
        self._ensure_dir()
        self._load_index()

    def _ensure_dir(self):
        os.makedirs(self.base_dir, exist_ok=True)

    def _load_index(self):
        if os.path.exists(self.index_path):
            try:
                with open(self.index_path, "r", encoding="utf-8") as f:
                    self._index = json.load(f)
                self._url_set = {item["url"] for item in self._index}
            except (json.JSONDecodeError, KeyError):
                self._index = []
                self._url_set = set()
        else:
            self._index = []
            self._url_set = set()

    def _save_index(self):
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(self._index, f, ensure_ascii=False, indent=2)

    # ========== 写入 ==========

    def save(self, article: Dict) -> Optional[str]:
        """保存文章到本地素材库（按 URL 去重）

        Args:
            article: {url, domain, title, content_md, summary, keywords}

        Returns:
            保存的文件路径，已存在则返回 None
        """
        url = article.get("url", "")
        if not url or url in self._url_set:
            return None

        domain = article.get("domain", urlparse(url).netloc)
        slug = self._url_to_slug(url)
        domain_dir = os.path.join(self.base_dir, self._safe_dirname(domain))
        os.makedirs(domain_dir, exist_ok=True)

        # 保存 Markdown 文件
        md_path = os.path.join(domain_dir, f"{slug}.md")
        content = article.get("content_md", "")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(content)

        # 更新索引
        entry = {
            "url": url,
            "domain": domain,
            "title": article.get("title", ""),
            "summary": article.get("summary", ""),
            "keywords": article.get("keywords", []),
            "md_path": md_path,
            "char_count": len(content),
            "crawled_at": datetime.now().isoformat(),
        }
        self._index.append(entry)
        self._url_set.add(url)
        self._save_index()

        logger.info(f"素材库保存: {domain}/{slug} ({len(content)} chars)")
        return md_path

    # ========== 查询 ==========

    def search(self, query: str, limit: int = 10) -> List[Dict]:
        """关键词搜索本地素材库

        搜索策略：标题 + 摘要 + 关键词匹配，按匹配度排序
        """
        if not query or not query.strip():
            return []

        tokens = self._tokenize(query.lower())
        if not tokens:
            return []

        scored = []
        for entry in self._index:
            score = self._calc_score(entry, tokens)
            if score > 0:
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:limit]]

    def get_index(self) -> List[Dict]:
        """获取完整索引"""
        return list(self._index)

    def has_url(self, url: str) -> bool:
        """检查 URL 是否已存在"""
        return url in self._url_set

    def get_stats(self) -> Dict:
        """获取素材库统计"""
        domains: Dict[str, int] = {}
        for entry in self._index:
            d = entry.get("domain", "unknown")
            domains[d] = domains.get(d, 0) + 1
        return {"total": len(self._index), "domains": domains}

    # ========== 内部方法 ==========

    def _calc_score(self, entry: Dict, tokens: List[str]) -> float:
        """计算匹配分数"""
        score = 0.0
        title = (entry.get("title") or "").lower()
        summary = (entry.get("summary") or "").lower()
        keywords = [k.lower() for k in (entry.get("keywords") or [])]

        for token in tokens:
            if token in title:
                score += 3.0  # 标题权重最高
            if token in summary:
                score += 2.0
            if any(token in kw for kw in keywords):
                score += 1.5
        return score

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """简单分词：按空格 + 中文字符"""
        # 英文按空格分词
        tokens = re.findall(r'[a-z0-9]+|[\u4e00-\u9fff]+', text.lower())
        return [t for t in tokens if len(t) >= 2 or '\u4e00' <= t[0] <= '\u9fff']

    @staticmethod
    def _url_to_slug(url: str) -> str:
        """URL 转文件名 slug"""
        parsed = urlparse(url)
        path = parsed.path.strip("/").replace("/", "_")
        slug = re.sub(r'[^a-zA-Z0-9_\-]', '', path)
        return slug[:80] or "index"

    @staticmethod
    def _safe_dirname(domain: str) -> str:
        """域名转安全目录名"""
        return re.sub(r'[^a-zA-Z0-9.\-]', '_', domain)
