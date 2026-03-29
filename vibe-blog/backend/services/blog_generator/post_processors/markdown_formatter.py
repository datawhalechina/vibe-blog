"""
Markdown 后处理器：修复分割线前后的换行符问题

用于处理生成的 Markdown 文件中分割线（---）前后缺少换行符的问题，
确保 Markdown 格式规范且渲染正确。
"""

import re
from pathlib import Path
from typing import Optional


class MarkdownFormatter:
    """
    Markdown 格式化器：处理常见的格式问题
    """
    
    def __init__(self):
        """初始化格式化器"""
        # 分割线模式：匹配 --- 前后没有正确换行的情况
        self.separator_pattern = re.compile(
            r'([^\n])(-{3,})([^\n])',  # 匹配 X---Y 的模式
            re.MULTILINE
        )
        
        # 标题前分割线模式：匹配 ---## 这样的情况
        self.separator_heading_pattern = re.compile(
            r'(-{3,})([#])',  # 匹配 ---# 的模式
            re.MULTILINE
        )
    
    def fix_separator_spacing(self, content: str) -> str:
        """
        修复分割线前后的换行符
        
        注意：只处理独立的分割线（行首的 ---），不处理表格分隔符（|---|）
        
        Args:
            content (str): 原始 Markdown 内容
        
        Returns:
            str: 修复后的内容
        """
        # 行首是 --- 的，拆分并前后加空行
        # 先把 ---## 拆成 ---\n##
        content = re.sub(r'^(---+)([^-\s\n])', r'\1\n\n\2', content, flags=re.MULTILINE)
        # 再确保独立的 --- 前后有空行
        content = re.sub(r'^(---+)$', r'\n\1\n', content, flags=re.MULTILINE)
        return content
    
    def fix_multiple_blank_lines(self, content: str, max_blanks: int = 2) -> str:
        """
        修复过多的空行（保留最多 max_blanks 个连续空行）
        
        Args:
            content (str): Markdown 内容
            max_blanks (int): 最多保留的连续空行数，默认 2
        
        Returns:
            str: 修复后的内容
        """
        # Step 1: 构建正则表达式匹配多于 max_blanks 的空行
        # \n{n,} 匹配 n 个或更多换行符
        pattern = r'\n' * (max_blanks + 2) + r'+'
        replacement = '\n' * (max_blanks + 1)
        
        # Step 2: 替换多余空行
        content = re.sub(pattern, replacement, content)
        
        return content
    
    def fix_heading_spacing(self, content: str) -> str:
        """
        修复标题前后的空行（标题前应有空行，标题后应有空行）
        
        Args:
            content (str): Markdown 内容
        
        Returns:
            str: 修复后的内容
        """
        # Step 1: 处理标题前缺少空行的情况
        # 匹配 \n## 这样标题前没有空行的情况
        content = re.sub(
            r'([^\n])\n(#{1,6}\s)',  # 匹配 X\n## 的模式
            r'\1\n\n\2',
            content
        )
        
        # Step 2: 处理标题后缺少空行的情况
        # 匹配 ##标题\n非空行 这样标题后没有空行的情况
        content = re.sub(
            r'(#{1,6}\s[^\n]+)\n([^\n\s])',  # 匹配 ##标题\nX 的模式
            r'\1\n\n\2',
            content
        )
        
        return content
    
    def format_content(self, content: str) -> str:
        """
        执行完整的 Markdown 格式化流程
        
        Args:
            content (str): 原始 Markdown 内容
        
        Returns:
            str: 格式化后的内容
        """
        # Step 1: 修复分割线间距
        content = self.fix_separator_spacing(content)
        
        # Step 2: 修复多余空行
        content = self.fix_multiple_blank_lines(content, max_blanks=2)
        
        # Step 3: 修复标题间距
        content = self.fix_heading_spacing(content)
        
        # Step 4: 移除文件末尾多余空行（保留单个换行符）
        content = content.rstrip() + '\n'
        
        return content
    
    def process_file(self, file_path: str) -> bool:
        """
        处理单个 Markdown 文件
        
        Args:
            file_path (str): 文件路径
        
        Returns:
            bool: 处理是否成功
        """
        try:
            # Step 1: 读取文件
            path = Path(file_path)
            if not path.exists():
                print(f"[ERROR] 文件不存在: {file_path}")
                return False
            
            # Step 2: 读取内容
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Step 3: 格式化内容
            formatted_content = self.format_content(content)
            
            # Step 4: 如果内容有变化，写回文件
            if content != formatted_content:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(formatted_content)
                print(f"[SUCCESS] 已修复文件: {file_path}")
                return True
            else:
                print(f"[INFO] 文件无需修改: {file_path}")
                return True
        
        except Exception as e:
            print(f"[ERROR] 处理文件失败 {file_path}: {str(e)}")
            return False
    
    def process_directory(self, directory_path: str, pattern: str = "*.md") -> int:
        """
        批量处理目录下的 Markdown 文件
        
        Args:
            directory_path (str): 目录路径
            pattern (str): 文件匹配模式，默认 *.md
        
        Returns:
            int: 成功处理的文件数量
        """
        try:
            # Step 1: 获取目录路径对象
            dir_path = Path(directory_path)
            if not dir_path.is_dir():
                print(f"[ERROR] 目录不存在: {directory_path}")
                return 0
            
            # Step 2: 查找所有匹配的 Markdown 文件
            md_files = list(dir_path.glob(pattern))
            if not md_files:
                print(f"[INFO] 目录中未找到匹配的文件: {directory_path}")
                return 0
            
            # Step 3: 逐个处理文件
            success_count = 0
            for md_file in md_files:
                if self.process_file(str(md_file)):
                    success_count += 1
            
            # Step 4: 输出处理统计
            print(f"[INFO] 处理完成: {success_count}/{len(md_files)} 个文件")
            return success_count
        
        except Exception as e:
            print(f"[ERROR] 处理目录失败 {directory_path}: {str(e)}")
            return 0


# --- 使用示例 ---
if __name__ == "__main__":
    import sys
    
    # Step 1: 创建格式化器实例
    formatter = MarkdownFormatter()
    
    # Step 2: 检查命令行参数
    if len(sys.argv) > 1:
        # 如果提供了文件或目录路径，处理它
        target_path = sys.argv[1]
        path_obj = Path(target_path)
        
        if path_obj.is_file():
            # 处理单个文件
            formatter.process_file(target_path)
        elif path_obj.is_dir():
            # 处理目录
            formatter.process_directory(target_path)
        else:
            print(f"[ERROR] 无效的路径: {target_path}")
    else:
        # 默认处理当前目录的 outputs 文件夹
        outputs_dir = Path(__file__).parent.parent.parent.parent.parent / "outputs"
        if outputs_dir.exists():
            print(f"[INFO] 处理输出目录: {outputs_dir}")
            formatter.process_directory(str(outputs_dir))
        else:
            print("[ERROR] 未找到 outputs 目录")
