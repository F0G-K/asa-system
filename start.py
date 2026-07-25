#!/usr/bin/env python3
"""ASA System 快速启动入口。

从项目根目录一键启动::

    python start.py              # 启动全部（API + Worker）
    python start.py --api        # 仅启动 API 服务器
    python start.py --check      # 仅检查环境
    python start.py --migrate    # 仅数据库迁移
    python start.py --help       # 查看所有选项
"""

import sys
from pathlib import Path

# 将 backend/src 加入 sys.path，使 `from backend.launcher import ...` 可用
_BACKEND_SRC = Path(__file__).resolve().parent / "backend" / "src"
if str(_BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(_BACKEND_SRC))

from backend.launcher import main

if __name__ == "__main__":
    main()
