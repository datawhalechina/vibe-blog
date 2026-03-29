"""
文档处理器 - 解析 Markdown 文件

功能:
- 扫描 .md 文件
- 提取标题层级
- 计算 MD5 (增量更新检测)
- 过滤非内容文件
"""
import os
import re
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# 需要过滤的文件名模式
IGNORE_PATTERNS = [
    r'^README\.md$',
    r'^CHANGELOG\.md$',
    r'^CONTRIBUTING\.md$',
    r'^LICENSE.*',
    r'^CODE_OF_CONDUCT\.md$',
    r'^SECURITY\.md$',
    r'^\..*',  # 隐藏文件
]

# 需要过滤的目录
IGNORE_DIRS = [
    '.git',
    'node_modules',
    '__pycache__',
    '.venv',
    'venv',
    '.idea',
    '.vscode',
]


@dataclass
class MarkdownFile:
    """Markdown 文件信息"""
    file_path: str          # 相对路径
    file_name: str          # 文件名
    title: Optional[str]    # 从 H1 提取的标题
    content: str            # 文件内容
    content_hash: str       # MD5 哈希
    word_count: int         # 字数
    order: int              # 排序顺序


class DocumentProcessor:
    """文档处理器"""
    
    def __init__(self, include_readme: bool = False):
        """
        初始化文档处理器
        
        Args:
            include_readme: 是否包含 README.md
        """
        self.include_readme = include_readme
        self.ignore_patterns = IGNORE_PATTERNS.copy()
        if include_readme:
            self.ignore_patterns = [p for p in self.ignore_patterns if 'README' not in p]
    
    def scan_directory(self, repo_path: str) -> List[MarkdownFile]:
        """
        扫描目录中的所有 Markdown 文件
        
        Args:
            repo_path: 仓库根目录
            
        Returns:
            Markdown 文件列表，按路径排序
        """
        md_files = []
        repo_path = Path(repo_path)
        
        for root, dirs, files in os.walk(repo_path):
            # 过滤忽略的目录
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            
            for file in files:
                if not file.endswith('.md'):
                    continue
                
                # 检查是否需要忽略
                if self._should_ignore(file):
                    continue
                
                full_path = Path(root) / file
                rel_path = str(full_path.relative_to(repo_path))
                
                try:
                    md_file = self._parse_file(str(full_path), rel_path, file)
                    if md_file:
                        md_files.append(md_file)
                except Exception as e:
                    logger.warning(f"解析文件失败: {rel_path}, 错误: {e}")
        
        # 按路径排序
        md_files.sort(key=lambda f: f.file_path)
        
        # 设置顺序
        for i, md_file in enumerate(md_files):
            md_file.order = i
        
        logger.info(f"扫描完成: 找到 {len(md_files)} 个 Markdown 文件")
        return md_files
    
    def _should_ignore(self, filename: str) -> bool:
        """检查文件是否应该被忽略"""
        for pattern in self.ignore_patterns:
            if re.match(pattern, filename, re.IGNORECASE):
                return True
        return False
    
    def _parse_file(self, full_path: str, rel_path: str, file_name: str) -> Optional[MarkdownFile]:
        """解析单个 Markdown 文件"""
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 空文件跳过
        if not content.strip():
            return None
        
        # 提取标题 (第一个 H1)
        title = self._extract_title(content)
        
        # 计算 MD5
        content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
        
        # 计算字数 (中文按字符，英文按单词)
        word_count = self._count_words(content)
        
        return MarkdownFile(
            file_path=rel_path,
            file_name=file_name,
            title=title,
            content=content,
            content_hash=content_hash,
            word_count=word_count,
            order=0,
        )
    
    def _extract_title(self, content: str) -> Optional[str]:
        """从 Markdown 内容中提取标题"""
        # 匹配 # 开头的 H1
        match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        
        # 匹配 === 下划线形式的 H1
        match = re.search(r'^(.+)\n=+\s*$', content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        
        return None
    
    def _count_words(self, content: str) -> int:
        """计算字数"""
        # 移除代码块
        content = re.sub(r'```[\s\S]*?```', '', content)
        content = re.sub(r'`[^`]+`', '', content)
        
        # 移除 Markdown 语法
        content = re.sub(r'[#*_\[\]()>]', '', content)
        
        # 计算中文字符
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
        
        # 计算英文单词
        english_words = len(re.findall(r'[a-zA-Z]+', content))
        
        return chinese_chars + english_words
    
    def extract_structure(self, content: str) -> Dict[str, Any]:
        """
        提取文档结构
        
        Args:
            content: Markdown 内容
            
        Returns:
            结构信息
        """
        structure = {
            'headings': [],
            'code_blocks': [],
            'images': [],
            'links': [],
            'lists': 0,
            'tables': 0,
        }
        
        # 提取标题
        for match in re.finditer(r'^(#{1,6})\s+(.+)$', content, re.MULTILINE):
            level = len(match.group(1))
            text = match.group(2).strip()
            structure['headings'].append({'level': level, 'text': text})
        
        # 提取代码块
        for match in re.finditer(r'```(\w*)\n([\s\S]*?)```', content):
            lang = match.group(1) or 'text'
            code = match.group(2)
            structure['code_blocks'].append({'language': lang, 'lines': code.count('\n') + 1})
        
        # 提取图片
        for match in re.finditer(r'!\[([^\]]*)\]\(([^)]+)\)', content):
            alt = match.group(1)
            src = match.group(2)
            structure['images'].append({'alt': alt, 'src': src})
        
        # 提取链接
        for match in re.finditer(r'\[([^\]]+)\]\(([^)]+)\)', content):
            text = match.group(1)
            href = match.group(2)
            if not href.startswith('#'):  # 排除锚点链接
                structure['links'].append({'text': text, 'href': href})
        
        # 统计列表
        structure['lists'] = len(re.findall(r'^[\s]*[-*+]\s', content, re.MULTILINE))
        structure['lists'] += len(re.findall(r'^[\s]*\d+\.\s', content, re.MULTILINE))
        
        # 统计表格
        structure['tables'] = len(re.findall(r'^\|.+\|$', content, re.MULTILINE)) // 2
        
        return structure
