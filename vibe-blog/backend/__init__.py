"""
兼容包入口。

允许测试从仓库根目录使用 `import backend...`，同时继续支持代码里大量存在的
`from services ...` / `from routes ...` 这类以 backend 目录为 import root 的旧写法。
"""

import os
import sys

_BACKEND_DIR = os.path.dirname(__file__)

if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)