from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Tuple, Union


JsonValue = Union[None, bool, int, float, str, Dict[str, Any], list]
JsonObject = Dict[str, JsonValue]
JsonRpcId = Union[str, int, None]


class JsonRpcError(Exception):
    """JSON-RPC 协议错误。"""

    def __init__(self, code: int, message: str, *, data: Optional[JsonValue] = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


def make_result(id_: JsonRpcId, result: JsonValue) -> JsonObject:
    return {"jsonrpc": "2.0", "id": id_, "result": result}


def make_error(id_: JsonRpcId, code: int, message: str, data: Optional[JsonValue] = None) -> JsonObject:
    err: JsonObject = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": id_, "error": err}


@dataclass(frozen=True)
class ParsedRequest:
    id: JsonRpcId
    method: str
    params: Mapping[str, Any]
    is_notification: bool


def parse_request(obj: Any) -> ParsedRequest:
    if not isinstance(obj, dict):
        raise JsonRpcError(-32600, "Invalid Request: 必须是 JSON 对象")
    if obj.get("jsonrpc") != "2.0":
        raise JsonRpcError(-32600, "Invalid Request: jsonrpc 必须为 '2.0'")

    method = obj.get("method")
    if not isinstance(method, str) or not method:
        raise JsonRpcError(-32600, "Invalid Request: method 必须是非空字符串")

    id_: JsonRpcId = obj.get("id") if "id" in obj else None
    is_notification = "id" not in obj

    params = obj.get("params", {})
    if params is None:
        params = {}
    if not isinstance(params, dict):
        raise JsonRpcError(-32602, "Invalid params: params 必须是对象")

    return ParsedRequest(id=id_, method=method, params=params, is_notification=is_notification)


def safe_parse_json_line(line: str) -> Tuple[Optional[ParsedRequest], Optional[JsonObject]]:
    """
    解析一行 JSON，并返回（ParsedRequest, errorResponse）。
    """
    import json

    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return None, make_error(None, -32700, "Parse error: 无法解析 JSON")

    try:
        req = parse_request(obj)
    except JsonRpcError as e:
        return None, make_error(obj.get("id") if isinstance(obj, dict) else None, e.code, e.message, e.data)

    return req, None

