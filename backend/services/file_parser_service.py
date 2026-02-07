"""
文件解析服务 - 使用 MinerU 解析 PDF/文档

二期新增：
- 知识分块功能
- 图片摘要生成（多模态模型）
"""
import os
import re
import time
import uuid
import base64
import logging
import zipfile
import io
from pathlib import Path
from typing import Optional, List, Tuple, Callable, Dict, Any

import requests
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

# 初始化 Jinja2 模板环境
_templates_dir = Path(__file__).parent.parent / 'infrastructure' / 'prompts' / 'shared'
_jinja_env = Environment(loader=FileSystemLoader(str(_templates_dir)))


class FileParserService:
    """文件解析服务，支持 MinerU OCR 解析 PDF"""
    
    def __init__(
        self,
        mineru_token: str,
        mineru_api_base: str = "https://mineru.net",
        upload_folder: str = "",
        pdf_max_pages: int = 15
    ):
        """
        初始化文件解析服务
        
        Args:
            mineru_token: MinerU API Token
            mineru_api_base: MinerU API 基础 URL
            upload_folder: 上传文件存储目录
            pdf_max_pages: PDF 最大页数限制
        """
        self.mineru_token = mineru_token
        self.mineru_api_base = mineru_api_base
        self.upload_url_api = f"{mineru_api_base}/api/v4/file-urls/batch"
        self.result_api_template = f"{mineru_api_base}/api/v4/extract-results/batch/{{}}"
        
        self.upload_folder = upload_folder or str(Path(__file__).parent.parent / 'uploads')
        self.pdf_max_pages = pdf_max_pages
        
        logger.info(f"FileParserService 初始化完成, upload_folder={self.upload_folder}, pdf_max_pages={self.pdf_max_pages}")
    
    def parse_file(
        self, 
        file_path: str, 
        filename: str, 
        on_progress: Callable[[int, int, str, str], None] = None
    ) -> dict:
        """
        解析文件
        
        Args:
            file_path: 文件路径
            filename: 原始文件名
            on_progress: 进度回调函数 (step: int, total: int, message: str, detail: str)
            
        Returns:
            dict: {
                'success': bool,
                'batch_id': str | None,
                'markdown': str | None,
                'images': list[dict] | None,  # [{path, url, page_num}]
                'mineru_folder': str | None,  # MinerU 解析结果目录
                'error': str | None
            }
        """
        try:
            file_ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
            
            # 纯文本文件直接读取
            if file_ext in ['txt', 'md', 'markdown']:
                logger.info(f"直接读取文本文件: {filename}")
                if on_progress:
                    on_progress(1, 1, "读取文本文件", filename)
                return self._parse_text_file(file_path)
            
            # PDF 文件检查页数限制
            if file_ext == 'pdf':
                page_count = self._get_pdf_page_count(file_path)
                if page_count > self.pdf_max_pages:
                    logger.warning(f"PDF 页数超限: {page_count} 页 (最大 {self.pdf_max_pages} 页)")
                    return {
                        'success': False,
                        'batch_id': None,
                        'markdown': None,
                        'images': None,
                        'mineru_folder': None,
                        'error': f'PDF 页数超过限制：{page_count} 页（最大支持 {self.pdf_max_pages} 页）'
                    }
                logger.info(f"PDF 页数检查通过: {page_count} 页")
            
            # 其他文件使用 MinerU 解析
            logger.info(f"使用 MinerU 解析文件: {filename}")
            return self._parse_with_mineru(file_path, filename, on_progress)
            
        except Exception as e:
            logger.error(f"文件解析异常: {e}", exc_info=True)
            return {
                'success': False,
                'batch_id': None,
                'markdown': None,
                'images': None,
                'mineru_folder': None,
                'error': str(e)
            }
    
    def _get_pdf_page_count(self, file_path: str) -> int:
        """获取 PDF 页数"""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                # 简单方法：统计 /Type /Page 出现次数（不包括 /Pages）
                # 更准确的方法需要用 PyPDF2，但这里用简单方法避免额外依赖
                # 匹配 /Type /Page 但不匹配 /Type /Pages
                pages = re.findall(rb'/Type\s*/Page[^s]', content)
                count = len(pages)
                if count == 0:
                    # 备用方法：查找 /Count 字段
                    count_match = re.search(rb'/Count\s+(\d+)', content)
                    if count_match:
                        count = int(count_match.group(1))
                logger.info(f"PDF 页数检测: {count} 页")
                return count if count > 0 else 1
        except Exception as e:
            logger.warning(f"无法获取 PDF 页数: {e}")
            return 0
    
    def _parse_text_file(self, file_path: str) -> dict:
        """解析纯文本文件"""
        try:
            # 尝试 UTF-8 编码
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                # 尝试 GBK 编码
                with open(file_path, 'r', encoding='gbk') as f:
                    content = f.read()
            
            logger.info(f"文本文件读取成功: {len(content)} 字符")
            
            return {
                'success': True,
                'batch_id': None,
                'markdown': content,
                'images': [],
                'mineru_folder': None,
                'error': None
            }
        except Exception as e:
            return {
                'success': False,
                'batch_id': None,
                'markdown': None,
                'images': None,
                'mineru_folder': None,
                'error': f"读取文本文件失败: {e}"
            }
    
    def _parse_with_mineru(
        self, 
        file_path: str, 
        filename: str, 
        on_progress: Callable = None
    ) -> dict:
        """使用 MinerU 解析文件"""
        # Step 1: 获取上传 URL
        logger.info("Step 1/3: 获取上传 URL...")
        if on_progress:
            on_progress(1, 3, "准备上传", f"正在获取上传地址...")
        batch_id, upload_url, error = self._get_upload_url(filename)
        if error:
            return {
                'success': False,
                'batch_id': None,
                'markdown': None,
                'images': None,
                'mineru_folder': None,
                'error': error
            }
        
        # Step 2: 上传文件
        logger.info(f"Step 2/3: 上传文件... batch_id={batch_id}")
        if on_progress:
            on_progress(2, 3, "上传文件", f"正在上传 {filename}...")
        error = self._upload_file(file_path, upload_url)
        if error:
            return {
                'success': False,
                'batch_id': batch_id,
                'markdown': None,
                'images': None,
                'mineru_folder': None,
                'error': error
            }
        
        # Step 3: 轮询解析结果
        logger.info("Step 3/3: 等待解析完成...")
        if on_progress:
            on_progress(3, 3, "解析文档", "MinerU 正在解析文档内容...")
        extract_id = str(uuid.uuid4())[:8]
        markdown, images, mineru_folder, error = self._poll_and_download(
            batch_id, extract_id, on_progress
        )
        if error:
            return {
                'success': False,
                'batch_id': batch_id,
                'markdown': None,
                'images': None,
                'mineru_folder': None,
                'error': error
            }
        
        return {
            'success': True,
            'batch_id': batch_id,
            'markdown': markdown,
            'images': images,
            'mineru_folder': mineru_folder,
            'error': None
        }
    
    def _get_upload_url(self, filename: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """从 MinerU 获取上传 URL"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.mineru_token}"
        }
        
        payload = {
            "files": [{"name": filename}],
            "model_version": "vlm"
        }
        
        try:
            logger.info(f"请求 MinerU 上传 URL: {self.upload_url_api}")
            response = requests.post(
                self.upload_url_api,
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"MinerU 响应: code={result.get('code')}, msg={result.get('msg')}")
            
            if result.get("code") != 0:
                error_msg = f"获取上传 URL 失败: {result.get('msg')}"
                logger.error(error_msg)
                return None, None, error_msg
            
            batch_id = result["data"]["batch_id"]
            upload_url = result["data"]["file_urls"][0]
            logger.info(f"成功获取上传 URL: batch_id={batch_id}")
            return batch_id, upload_url, None
            
        except requests.RequestException as e:
            error_msg = f"网络请求失败: {e}"
            logger.error(error_msg, exc_info=True)
            return None, None, error_msg
        except Exception as e:
            error_msg = f"解析响应失败: {e}"
            logger.error(error_msg, exc_info=True)
            return None, None, error_msg
    
    def _upload_file(self, file_path: str, upload_url: str) -> Optional[str]:
        """上传文件到 MinerU"""
        try:
            with open(file_path, 'rb') as f:
                response = requests.put(
                    upload_url,
                    data=f,
                    timeout=300
                )
                response.raise_for_status()
            return None
        except requests.RequestException as e:
            return f"文件上传失败: {e}"
        except IOError as e:
            return f"文件读取失败: {e}"
    
    def _poll_and_download(
        self, 
        batch_id: str, 
        extract_id: str,
        on_progress: Callable = None,
        max_wait: int = 600
    ) -> Tuple[Optional[str], Optional[List[dict]], Optional[str], Optional[str]]:
        """轮询解析结果并下载"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.mineru_token}"
        }
        
        result_url = self.result_api_template.format(batch_id)
        start_time = time.time()
        poll_count = 0
        
        while True:
            if time.time() - start_time > max_wait:
                return None, None, None, f"解析超时 ({max_wait}s)"
            
            try:
                response = requests.get(result_url, headers=headers, timeout=30)
                response.raise_for_status()
                task_info = response.json()
                
                if task_info.get("code") != 0:
                    return None, None, None, f"查询状态失败: {task_info.get('msg')}"
                
                state = task_info["data"]["extract_result"][0]["state"]
                
                if state == "done":
                    logger.info("解析完成，开始下载结果...")
                    if on_progress:
                        on_progress(3, 3, "下载结果", "解析完成，正在下载结果...")
                    zip_url = task_info["data"]["extract_result"][0]["full_zip_url"]
                    return self._download_and_extract(zip_url, extract_id)
                elif state == "failed":
                    err_msg = task_info["data"]["extract_result"][0].get("err_msg", "未知错误")
                    return None, None, None, f"解析失败: {err_msg}"
                else:
                    poll_count += 1
                    elapsed = int(time.time() - start_time)
                    logger.info(f"当前状态: {state}, 继续等待...")
                    if on_progress and poll_count % 3 == 0:  # 每 6 秒更新一次
                        on_progress(3, 3, "解析文档", f"MinerU 正在解析... 已等待 {elapsed} 秒")
                    time.sleep(2)
                    
            except requests.RequestException as e:
                logger.warning(f"轮询请求失败: {e}, 重试中...")
                time.sleep(2)
    
    def _download_and_extract(
        self, 
        zip_url: str, 
        extract_id: str
    ) -> Tuple[Optional[str], Optional[List[dict]], Optional[str], Optional[str]]:
        """下载并解压结果"""
        try:
            response = requests.get(zip_url, timeout=120)
            response.raise_for_status()
            
            # 创建存储目录
            storage_dir = Path(self.upload_folder) / 'mineru_files' / extract_id
            storage_dir.mkdir(parents=True, exist_ok=True)
            
            markdown_content = None
            images = []
            
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                z.extractall(storage_dir)
                logger.info(f"解压 {len(z.namelist())} 个文件到 {storage_dir}")
                
                # 查找 Markdown 文件
                for name in z.namelist():
                    if name.lower().endswith('.md'):
                        md_path = storage_dir / name
                        with open(md_path, 'r', encoding='utf-8') as f:
                            markdown_content = f.read()
                        logger.info(f"找到 Markdown 文件: {name}")
                        break
                
                # 收集图片文件
                for name in z.namelist():
                    if name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                        img_path = storage_dir / name
                        # 生成访问 URL
                        url = f"/files/mineru/{extract_id}/{name}"
                        
                        # 尝试从文件名中提取页码
                        page_num = self._extract_page_num_from_filename(name)
                        
                        images.append({
                            'path': str(img_path),
                            'url': url,
                            'filename': os.path.basename(name),
                            'page_num': page_num
                        })
            
            if markdown_content is None:
                return None, None, None, "未找到 Markdown 文件"
            
            if not markdown_content.strip():
                return None, None, None, "PDF 解析结果为空，可能是扫描版 PDF 或内容无法识别"
            
            # 替换 Markdown 中的图片路径
            markdown_content = self._replace_image_paths(markdown_content, extract_id)
            
            return markdown_content, images, str(storage_dir), None
            
        except requests.RequestException as e:
            return None, None, None, f"下载结果失败: {e}"
        except zipfile.BadZipFile:
            return None, None, None, "下载的文件不是有效的 ZIP 文件"
        except Exception as e:
            return None, None, None, f"处理结果失败: {e}"
    
    def _extract_page_num_from_filename(self, filename: str) -> int:
        """
        从文件名中提取页码
        
        支持的格式:
        - page_1_xxx.png -> 1
        - 1_xxx.png -> 1
        - xxx_p1.png -> 1
        - xxx_page1.png -> 1
        - images/1/xxx.png -> 1 (从路径中提取)
        
        Returns:
            页码 (从 1 开始)，如果无法提取则返回 0
        """
        # 获取文件名（不含路径）
        basename = os.path.basename(filename)
        
        # 尝试多种模式
        patterns = [
            r'page[_-]?(\d+)',      # page_1, page-1, page1
            r'^(\d+)[_-]',          # 1_xxx, 1-xxx
            r'[_-]p(\d+)\.',        # xxx_p1.png
            r'[_-](\d+)\.',         # xxx_1.png
        ]
        
        for pattern in patterns:
            match = re.search(pattern, basename, re.IGNORECASE)
            if match:
                return int(match.group(1))
        
        # 尝试从路径中提取 (如 images/1/xxx.png)
        path_parts = filename.replace('\\', '/').split('/')
        for part in path_parts:
            if part.isdigit():
                return int(part)
        
        return 0  # 无法提取页码
    
    def _replace_image_paths(self, markdown: str, extract_id: str) -> str:
        """替换 Markdown 中的图片路径为本地服务 URL"""
        def replace_match(match):
            alt_text = match.group(1)
            img_path = match.group(2)
            
            # 跳过已经是 HTTP URL 的图片
            if img_path.startswith(('http://', 'https://')):
                return match.group(0)
            
            # 处理相对路径
            if img_path.startswith('/'):
                rel_path = img_path.lstrip('/')
            else:
                rel_path = img_path
            
            # 移除可能的 file/ 或 files/ 前缀
            for prefix in ['file/', 'files/']:
                if rel_path.startswith(prefix):
                    rel_path = rel_path[len(prefix):]
                    break
            
            new_url = f"/files/mineru/{extract_id}/{rel_path}"
            return f"![{alt_text}]({new_url})"
        
        pattern = r'!\[(.*?)\]\(([^\)]+)\)'
        return re.sub(pattern, replace_match, markdown)
    
    # ========== 二期新增：知识分块 ==========
    
    def chunk_markdown(
        self, 
        markdown: str, 
        chunk_size: int = 2000, 
        chunk_overlap: int = 200
    ) -> List[Dict[str, Any]]:
        """
        将 Markdown 内容分块
        
        策略：
        1. 优先按标题分块（## 或 ###）
        2. 如果单个章节过长，再按段落分块
        3. 保留分块位置信息
        
        Args:
            markdown: Markdown 内容
            chunk_size: 目标分块大小（字符）
            chunk_overlap: 分块重叠大小
        
        Returns:
            分块列表，每个分块包含 {chunk_type, title, content, start_pos, end_pos}
        """
        chunks = []
        
        # 按标题分割（## 或 ###）
        sections = self._split_by_headers(markdown)
        
        for section in sections:
            title = section.get('title', '')
            content = section.get('content', '')
            start_pos = section.get('start_pos', 0)
            
            if len(content) <= chunk_size:
                # 内容不超过限制，直接作为一个分块
                chunks.append({
                    'chunk_type': 'section',
                    'title': title,
                    'content': content,
                    'start_pos': start_pos,
                    'end_pos': start_pos + len(content)
                })
            else:
                # 内容过长，按段落再分块
                sub_chunks = self._split_by_paragraphs(
                    content, chunk_size, chunk_overlap, start_pos, title
                )
                chunks.extend(sub_chunks)
        
        logger.info(f"Markdown 分块完成: {len(chunks)} 块")
        return chunks
    
    def _split_by_headers(self, markdown: str) -> List[Dict[str, Any]]:
        """按标题分割 Markdown"""
        sections = []
        
        # 匹配 ## 或 ### 标题
        header_pattern = r'^(#{2,3})\s+(.+)$'
        lines = markdown.split('\n')
        
        current_section = {'title': '', 'content': '', 'start_pos': 0}
        current_pos = 0
        
        for line in lines:
            match = re.match(header_pattern, line)
            if match:
                # 保存之前的 section
                if current_section['content'].strip():
                    sections.append(current_section)
                
                # 开始新 section
                current_section = {
                    'title': match.group(2).strip(),
                    'content': line + '\n',
                    'start_pos': current_pos
                }
            else:
                current_section['content'] += line + '\n'
            
            current_pos += len(line) + 1  # +1 for newline
        
        # 保存最后一个 section
        if current_section['content'].strip():
            sections.append(current_section)
        
        # 如果没有找到任何标题，整个文档作为一个 section
        if not sections:
            sections.append({
                'title': '',
                'content': markdown,
                'start_pos': 0
            })
        
        return sections
    
    def _split_by_paragraphs(
        self, 
        content: str, 
        chunk_size: int, 
        chunk_overlap: int,
        base_pos: int,
        parent_title: str
    ) -> List[Dict[str, Any]]:
        """按段落分块长内容"""
        chunks = []
        
        # 按空行分割段落
        paragraphs = re.split(r'\n\s*\n', content)
        
        current_chunk = ''
        current_start = base_pos
        chunk_index = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            if len(current_chunk) + len(para) + 2 <= chunk_size:
                current_chunk += para + '\n\n'
            else:
                # 保存当前分块
                if current_chunk.strip():
                    chunks.append({
                        'chunk_type': 'paragraph',
                        'title': f"{parent_title} (Part {chunk_index + 1})" if parent_title else f"Part {chunk_index + 1}",
                        'content': current_chunk.strip(),
                        'start_pos': current_start,
                        'end_pos': current_start + len(current_chunk)
                    })
                    chunk_index += 1
                
                # 开始新分块（带重叠）
                overlap_text = current_chunk[-chunk_overlap:] if len(current_chunk) > chunk_overlap else ''
                current_start = current_start + len(current_chunk) - len(overlap_text)
                current_chunk = overlap_text + para + '\n\n'
        
        # 保存最后一个分块
        if current_chunk.strip():
            chunks.append({
                'chunk_type': 'paragraph',
                'title': f"{parent_title} (Part {chunk_index + 1})" if parent_title else f"Part {chunk_index + 1}",
                'content': current_chunk.strip(),
                'start_pos': current_start,
                'end_pos': current_start + len(current_chunk)
            })
        
        return chunks
    
    # ========== 二期新增：图片摘要 ==========
    
    def generate_image_captions(
        self, 
        images: List[Dict[str, Any]], 
        llm_service=None,
        max_images: int = 10
    ) -> List[Dict[str, Any]]:
        """
        为图片生成摘要描述
        
        Args:
            images: 图片列表，每个包含 {path, url, filename, page_num}
            llm_service: LLM 服务实例（需支持 vision 模型）
            max_images: 最多处理的图片数量
        
        Returns:
            带有 caption 的图片列表
        """
        if not llm_service:
            logger.warning("未提供 LLM 服务，跳过图片摘要生成")
            return images
        
        result = []
        processed = 0
        
        for img in images:
            if processed >= max_images:
                # 超过限制的图片不生成摘要
                result.append(img)
                continue
            
            img_path = img.get('path', '')
            if not img_path or not os.path.exists(img_path):
                result.append(img)
                continue
            
            try:
                # 读取图片并转为 base64
                with open(img_path, 'rb') as f:
                    img_data = f.read()
                img_base64 = base64.b64encode(img_data).decode('utf-8')
                
                # 确定 MIME 类型
                ext = os.path.splitext(img_path)[1].lower()
                mime_map = {
                    '.png': 'image/png',
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.gif': 'image/gif',
                    '.webp': 'image/webp'
                }
                mime_type = mime_map.get(ext, 'image/jpeg')
                
                # 调用多模态模型生成描述
                template = _jinja_env.get_template('image_caption.j2')
                prompt = template.render(max_length=200)
                caption = llm_service.chat_with_image(prompt, img_base64, mime_type)
                
                if caption:
                    img['caption'] = caption
                    logger.info(f"图片摘要生成成功: {img.get('filename', '')}")
                    processed += 1
                
            except Exception as e:
                logger.warning(f"图片摘要生成失败: {img_path}, 错误: {e}")
            
            result.append(img)
        
        logger.info(f"图片摘要生成完成: {processed}/{len(images)} 张")
        return result
    
    def generate_document_summary(
        self, 
        markdown: str, 
        llm_service=None,
        max_length: int = 500
    ) -> Optional[str]:
        """
        生成文档摘要（二期新增）
        
        Args:
            markdown: 文档 Markdown 内容
            llm_service: LLM 服务实例
            max_length: 摘要最大长度
        
        Returns:
            文档摘要
        """
        if not llm_service:
            logger.warning("未提供 LLM 服务，跳过文档摘要生成")
            return None
        
        try:
            # 截取前 4000 字符用于生成摘要
            content_preview = markdown[:4000] if len(markdown) > 4000 else markdown
            
            template = _jinja_env.get_template('document_summary.j2')
            prompt = template.render(max_length=max_length, content_preview=content_preview)
            
            summary = llm_service.chat([{"role": "user", "content": prompt}])
            
            if summary:
                # 确保不超过最大长度
                if len(summary) > max_length:
                    summary = summary[:max_length-3] + "..."
                logger.info(f"文档摘要生成成功: {len(summary)} 字")
                return summary
            
        except Exception as e:
            logger.error(f"文档摘要生成失败: {e}")
        
        return None


# 全局单例
_file_parser: Optional[FileParserService] = None


def get_file_parser() -> Optional[FileParserService]:
    """获取文件解析服务单例"""
    return _file_parser


def init_file_parser(
    mineru_token: str,
    mineru_api_base: str = "https://mineru.net",
    upload_folder: str = "",
    pdf_max_pages: int = 15
) -> FileParserService:
    """初始化文件解析服务"""
    global _file_parser
    _file_parser = FileParserService(
        mineru_token=mineru_token,
        mineru_api_base=mineru_api_base,
        upload_folder=upload_folder,
        pdf_max_pages=pdf_max_pages
    )
    return _file_parser


def create_file_parser_from_config(config) -> FileParserService:
    """从 Flask config 创建 FileParserService 实例"""
    return FileParserService(
        mineru_token=getattr(config, 'MINERU_TOKEN', ''),
        mineru_api_base=getattr(config, 'MINERU_API_BASE', 'https://mineru.net'),
        upload_folder=getattr(config, 'UPLOAD_FOLDER', '')
    )
