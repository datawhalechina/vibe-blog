"""
文件解析服务 - 使用 MinerU 解析 PDF/文档
复用自 AI绘本 项目
"""
import os
import re
import time
import uuid
import logging
import zipfile
import io
from pathlib import Path
from typing import Optional, List, Tuple, Callable

import requests

logger = logging.getLogger(__name__)


class FileParserService:
    """文件解析服务，支持 MinerU OCR 解析 PDF"""
    
    def __init__(
        self,
        mineru_token: str,
        mineru_api_base: str = "https://mineru.net",
        upload_folder: str = ""
    ):
        """
        初始化文件解析服务
        
        Args:
            mineru_token: MinerU API Token
            mineru_api_base: MinerU API 基础 URL
            upload_folder: 上传文件存储目录
        """
        self.mineru_token = mineru_token
        self.mineru_api_base = mineru_api_base
        self.upload_url_api = f"{mineru_api_base}/api/v4/file-urls/batch"
        self.result_api_template = f"{mineru_api_base}/api/v4/extract-results/batch/{{}}"
        
        self.upload_folder = upload_folder or str(Path(__file__).parent.parent / 'uploads')
        
        logger.info(f"FileParserService 初始化完成, upload_folder={self.upload_folder}")
    
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
            response = requests.post(
                self.upload_url_api,
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("code") != 0:
                return None, None, f"获取上传 URL 失败: {result.get('msg')}"
            
            batch_id = result["data"]["batch_id"]
            upload_url = result["data"]["file_urls"][0]
            return batch_id, upload_url, None
            
        except requests.RequestException as e:
            return None, None, f"网络请求失败: {e}"
    
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
            
            if not markdown_content:
                return None, None, None, "未找到 Markdown 文件"
            
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


# 全局单例
_file_parser: Optional[FileParserService] = None


def get_file_parser() -> Optional[FileParserService]:
    """获取文件解析服务单例"""
    return _file_parser


def init_file_parser(
    mineru_token: str,
    mineru_api_base: str = "https://mineru.net",
    upload_folder: str = ""
) -> FileParserService:
    """初始化文件解析服务"""
    global _file_parser
    _file_parser = FileParserService(
        mineru_token=mineru_token,
        mineru_api_base=mineru_api_base,
        upload_folder=upload_folder
    )
    return _file_parser


def create_file_parser_from_config(config) -> FileParserService:
    """从 Flask config 创建 FileParserService 实例"""
    return FileParserService(
        mineru_token=getattr(config, 'MINERU_TOKEN', ''),
        mineru_api_base=getattr(config, 'MINERU_API_BASE', 'https://mineru.net'),
        upload_folder=getattr(config, 'UPLOAD_FOLDER', '')
    )
