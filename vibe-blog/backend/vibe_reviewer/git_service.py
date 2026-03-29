"""
Git 服务 - 仓库克隆与拉取

支持 HTTP 协议公共仓库
"""
import os
import subprocess
import logging
from pathlib import Path
from typing import Optional, Tuple
import hashlib

logger = logging.getLogger(__name__)


class GitService:
    """Git 仓库管理服务"""
    
    def __init__(self, repos_dir: str):
        """
        初始化 Git 服务
        
        Args:
            repos_dir: 仓库存储目录
        """
        self.repos_dir = repos_dir
        Path(repos_dir).mkdir(parents=True, exist_ok=True)
    
    def _get_repo_dir(self, git_url: str) -> str:
        """根据 Git URL 生成本地目录名"""
        # 使用 URL 的 hash 作为目录名，避免特殊字符问题
        url_hash = hashlib.md5(git_url.encode()).hexdigest()[:12]
        repo_name = git_url.rstrip('/').split('/')[-1]
        if repo_name.endswith('.git'):
            repo_name = repo_name[:-4]
        return os.path.join(self.repos_dir, f"{repo_name}_{url_hash}")
    
    def clone_or_pull(self, git_url: str, branch: str = "main") -> Tuple[str, bool]:
        """
        克隆或拉取仓库
        
        Args:
            git_url: Git 仓库 URL
            branch: 分支名
            
        Returns:
            (本地路径, 是否有更新)
        """
        local_path = self._get_repo_dir(git_url)
        
        if os.path.exists(local_path):
            # 已存在，执行 pull
            return self._pull(local_path, branch)
        else:
            # 不存在，执行 clone
            return self._clone(git_url, local_path, branch)
    
    def _clone(self, git_url: str, local_path: str, branch: str) -> Tuple[str, bool]:
        """克隆仓库"""
        logger.info(f"克隆仓库: {git_url} -> {local_path}")
        
        try:
            result = subprocess.run(
                ["git", "clone", "--depth", "1", "-b", branch, git_url, local_path],
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            if result.returncode != 0:
                # 尝试不指定分支
                result = subprocess.run(
                    ["git", "clone", "--depth", "1", git_url, local_path],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                
                if result.returncode != 0:
                    raise RuntimeError(f"Git clone 失败: {result.stderr}")
            
            logger.info(f"克隆成功: {local_path}")
            return local_path, True
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("Git clone 超时")
        except Exception as e:
            logger.error(f"克隆失败: {e}")
            raise
    
    def _pull(self, local_path: str, branch: str) -> Tuple[str, bool]:
        """拉取更新"""
        logger.info(f"拉取更新: {local_path}")
        
        try:
            # 获取当前 commit hash
            old_hash = self._get_commit_hash(local_path)
            
            # 执行 pull
            result = subprocess.run(
                ["git", "pull", "origin", branch],
                cwd=local_path,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                # 尝试不指定分支
                result = subprocess.run(
                    ["git", "pull"],
                    cwd=local_path,
                    capture_output=True,
                    text=True,
                    timeout=120
                )
            
            # 获取新的 commit hash
            new_hash = self._get_commit_hash(local_path)
            
            has_update = old_hash != new_hash
            if has_update:
                logger.info(f"有更新: {old_hash[:8]} -> {new_hash[:8]}")
            else:
                logger.info("无更新")
            
            return local_path, has_update
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("Git pull 超时")
        except Exception as e:
            logger.error(f"拉取失败: {e}")
            raise
    
    def _get_commit_hash(self, local_path: str) -> str:
        """获取当前 commit hash"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=local_path,
                capture_output=True,
                text=True
            )
            return result.stdout.strip()
        except Exception:
            return ""
    
    def get_local_path(self, git_url: str) -> Optional[str]:
        """获取仓库的本地路径"""
        local_path = self._get_repo_dir(git_url)
        if os.path.exists(local_path):
            return local_path
        return None
