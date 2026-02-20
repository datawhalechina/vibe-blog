"""原子文件写入 — temp file → os.replace 模式"""
import os
import tempfile


def atomic_write(filepath: str, content: str, encoding: str = 'utf-8'):
    """原子文件写入：先写临时文件，再 rename 替换。"""
    dir_name = os.path.dirname(filepath)
    os.makedirs(dir_name, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding=encoding) as f:
            f.write(content)
        os.replace(tmp_path, filepath)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
