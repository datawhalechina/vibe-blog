"""
41.09 跨章节语义去重 — 检测并消除章节间重复内容

在 Writer 完成后、Reviewer 之前运行：
1. 将每个章节按段落切分
2. 用 embedding 计算段落间相似度
3. 相似度超过阈值的段落标记为重复
4. 保留首次出现的段落，后续重复段落由 LLM 改写或删除

环境变量：
- CROSS_SECTION_DEDUP_ENABLED: 是否启用（默认 false）
- DEDUP_SIMILARITY_THRESHOLD: 相似度阈值（默认 0.85）
- DEDUP_MIN_PARAGRAPH_LENGTH: 最小段落长度（默认 50 字符）
"""
import logging
import os
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)


class CrossSectionDeduplicator:
    """跨章节语义去重器"""

    def __init__(self, llm_client=None, threshold: float = None,
                 min_paragraph_len: int = None):
        self.llm = llm_client
        self.threshold = threshold or float(
            os.environ.get('DEDUP_SIMILARITY_THRESHOLD', '0.85')
        )
        self.min_paragraph_len = min_paragraph_len or int(
            os.environ.get('DEDUP_MIN_PARAGRAPH_LENGTH', '50')
        )

    def _split_paragraphs(self, content: str) -> List[str]:
        """将内容按段落切分（跳过代码块和短段落）"""
        paragraphs = []
        in_code_block = False
        current = []

        for line in content.split('\n'):
            stripped = line.strip()
            if stripped.startswith('```'):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue
            if not stripped:
                if current:
                    text = '\n'.join(current).strip()
                    if len(text) >= self.min_paragraph_len:
                        paragraphs.append(text)
                    current = []
            else:
                # 跳过标题行
                if stripped.startswith('#'):
                    continue
                current.append(line)

        if current:
            text = '\n'.join(current).strip()
            if len(text) >= self.min_paragraph_len:
                paragraphs.append(text)

        return paragraphs

    def detect_duplicates(self, sections: List[Dict[str, Any]]) -> List[Dict]:
        """
        检测跨章节重复段落。

        Returns:
            重复对列表: [{'section_a': idx, 'para_a': str, 'section_b': idx,
                          'para_b': str, 'similarity': float}]
        """
        from .services.semantic_compressor import _cosine_similarity, EmbeddingProvider

        # 收集所有段落
        all_paragraphs: List[Tuple[int, str]] = []  # (section_idx, paragraph_text)
        for idx, section in enumerate(sections):
            content = section.get('content', '')
            for para in self._split_paragraphs(content):
                all_paragraphs.append((idx, para))

        if len(all_paragraphs) < 2:
            return []

        # 生成 embedding
        try:
            provider = EmbeddingProvider()
            texts = [p[1] for p in all_paragraphs]
            embeddings = provider.embed(texts)
        except Exception as e:
            logger.warning(f"[Dedup] Embedding 生成失败: {e}")
            return []

        # 两两比较（只比较不同章节的段落）
        duplicates = []
        for i in range(len(all_paragraphs)):
            for j in range(i + 1, len(all_paragraphs)):
                sec_i, _ = all_paragraphs[i]
                sec_j, _ = all_paragraphs[j]
                if sec_i == sec_j:
                    continue  # 同章节内不去重

                sim = _cosine_similarity(embeddings[i], embeddings[j])
                if sim >= self.threshold:
                    duplicates.append({
                        'section_a': sec_i,
                        'para_a': all_paragraphs[i][1],
                        'section_b': sec_j,
                        'para_b': all_paragraphs[j][1],
                        'similarity': round(sim, 4),
                    })

        logger.info(f"[Dedup] 检测到 {len(duplicates)} 对跨章节重复段落")
        return duplicates

    def deduplicate(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        执行去重：保留首次出现，后续重复段落删除或改写。

        Args:
            sections: 章节列表

        Returns:
            去重后的章节列表（原地修改）
        """
        duplicates = self.detect_duplicates(sections)
        if not duplicates:
            return sections

        # 收集需要从后续章节中删除的段落
        paragraphs_to_remove: Dict[int, List[str]] = {}  # section_idx -> [para_text]
        for dup in duplicates:
            # 保留 section_a（先出现的），删除 section_b 中的重复段落
            sec_b = dup['section_b']
            if sec_b not in paragraphs_to_remove:
                paragraphs_to_remove[sec_b] = []
            paragraphs_to_remove[sec_b].append(dup['para_b'])

        # 执行删除
        removed_count = 0
        for sec_idx, paras in paragraphs_to_remove.items():
            content = sections[sec_idx].get('content', '')
            for para in paras:
                if para in content:
                    content = content.replace(para, '')
                    removed_count += 1
            # 清理多余空行
            import re
            content = re.sub(r'\n{3,}', '\n\n', content)
            sections[sec_idx]['content'] = content.strip()

        logger.info(f"[Dedup] 去重完成: 删除 {removed_count} 个重复段落")
        return sections
