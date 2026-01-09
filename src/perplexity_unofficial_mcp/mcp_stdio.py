from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .config import ConfigError, load_config, redact_env
from .jsonrpc import JsonRpcError, make_error, make_result, safe_parse_json_line
from .logging import log_event
from .tools import call_tool, list_tools


JsonObject = Dict[str, Any]


@dataclass
class ServerState:
    initialized: bool = False
    protocol_version: str = "2024-11-05"


def _write_message(obj: JsonObject) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def run_stdio_server() -> None:
    """
    以 STDIO 方式运行 MCP Server。

    注意：
    - stdout 仅输出 MCP JSON-RPC
    - stderr 输出结构化日志
    """
    try:
        config = load_config()
    except ConfigError as exc:
        log_event(
            {
                "level": "error",
                "msg": "配置加载失败",
                "error": str(exc),
                "env": redact_env(dict(os.environ)),
            }
        )
        # 启动阶段失败只能写 stderr；stdout 不能输出非 MCP 消息
        raise

    state = ServerState()
    log_event({"level": "info", "msg": "MCP Server 启动", "protocolVersion": state.protocol_version})

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        req, parse_err = safe_parse_json_line(line)
        if parse_err is not None:
            _write_message(parse_err)
            continue
        assert req is not None

        start = time.time()
        tool_name: Optional[str] = None
        ok = True
        try:
            if req.method == "initialize":
                if state.initialized:
                    raise JsonRpcError(-32600, "Invalid Request: 已初始化")
                client_proto = req.params.get("protocolVersion")
                if isinstance(client_proto, str) and client_proto:
                    state.protocol_version = client_proto
                state.initialized = True
                result = {
                    "protocolVersion": state.protocol_version,
                    "serverInfo": {
                        "name": "perplexity-unofficial-mcp",
                        "version": "0.1.0",
                    },
                    "capabilities": {
                        "tools": {},
                    },
                }
                if not req.is_notification:
                    _write_message(make_result(req.id, result))

            elif req.method in {"notifications/initialized", "initialized"}:
                # 兼容不同客户端命名；通知无响应
                pass

            elif req.method == "ping":
                if not req.is_notification:
                    _write_message(make_result(req.id, {}))

            elif req.method == "tools/list":
                if not state.initialized:
                    raise JsonRpcError(-32002, "Server not initialized")
                if not req.is_notification:
                    _write_message(make_result(req.id, {"tools": list_tools()}))

            elif req.method == "tools/call":
                if not state.initialized:
                    raise JsonRpcError(-32002, "Server not initialized")
                name = req.params.get("name")
                arguments = req.params.get("arguments", {})
                if not isinstance(name, str) or not name:
                    raise JsonRpcError(-32602, "Invalid params: name 必须是非空字符串")
                if arguments is None:
                    arguments = {}
                if not isinstance(arguments, dict):
                    raise JsonRpcError(-32602, "Invalid params: arguments 必须是对象")
                tool_name = name
                result = call_tool(config, name, arguments)
                if not req.is_notification:
                    _write_message(make_result(req.id, result))

            elif req.method == "resources/list":
                if not state.initialized:
                    raise JsonRpcError(-32002, "Server not initialized")
                if not req.is_notification:
                    _write_message(make_result(req.id, {"resources": []}))

            elif req.method == "prompts/list":
                if not state.initialized:
                    raise JsonRpcError(-32002, "Server not initialized")
                if not req.is_notification:
                    _write_message(make_result(req.id, {"prompts": []}))

            else:
                raise JsonRpcError(-32601, f"Method not found: {req.method}")

        except JsonRpcError as exc:
            ok = False
            if not req.is_notification:
                _write_message(make_error(req.id, exc.code, exc.message, exc.data))
        except Exception as exc:  # noqa: BLE001
            ok = False
            if not req.is_notification:
                _write_message(make_error(req.id, -32603, f"Internal error: {exc}"))
        finally:
            duration_ms = int((time.time() - start) * 1000)
            log_event(
                {
                    "level": "info" if ok else "error",
                    "requestId": req.id,
                    "method": req.method,
                    "toolName": tool_name,
                    "durationMs": duration_ms,
                    "ok": ok,
                }
            )
