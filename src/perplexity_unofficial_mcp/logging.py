import json
import sys
import time
from typing import Any, Mapping


def log_event(event: Mapping[str, Any]) -> None:
    """
    输出最小结构化日志到 stderr。

    约束：
    - stdout 仅用于 MCP 协议消息
    - 不得输出明文 Cookies
    """
    payload = dict(event)
    payload.setdefault("ts", int(time.time() * 1000))
    sys.stderr.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stderr.flush()

