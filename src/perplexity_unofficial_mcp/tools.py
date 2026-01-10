from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Tuple

from .config import AppConfig
from .perplexity_adapter import (
    PerplexityCallError,
    call_perplexity_search,
    messages_to_query,
    strip_thinking_tokens,
)


JsonObject = Dict[str, Any]


@dataclass(frozen=True)
class ToolDef:
    name: str
    description: str
    input_schema: JsonObject
    title: Optional[str] = None
    annotations: Optional[JsonObject] = None


def list_tools() -> List[JsonObject]:
    tools: List[ToolDef] = [
        ToolDef(
            name="perplexity_ask",
            title="Ask Perplexity",
            description="对齐官方 Perplexity MCP：基于 messages[] 提问并返回回答文本。",
            input_schema={
                "type": "object",
                "properties": {
                    "messages": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "role": {"type": "string"},
                                "content": {"type": "string"},
                            },
                            "required": ["role", "content"],
                            "additionalProperties": True,
                        },
                        "minItems": 1,
                    }
                    ,
                    "mode": {"type": "string"},
                    "model": {"type": "string"},
                },
                "required": ["messages"],
                "additionalProperties": True,
            },
            annotations={"readOnlyHint": True, "openWorldHint": True},
        ),
        ToolDef(
            name="perplexity_research",
            title="Deep Research",
            description="对齐官方 Perplexity MCP：深度研究（内部映射为非官方 SDK 的 deep research 模式）。",
            input_schema={
                "type": "object",
                "properties": {
                    "messages": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "role": {"type": "string"},
                                "content": {"type": "string"},
                            },
                            "required": ["role", "content"],
                            "additionalProperties": True,
                        },
                        "minItems": 1,
                    },
                    "strip_thinking": {"type": "boolean"},
                    "mode": {"type": "string"},
                    "model": {"type": "string"},
                },
                "required": ["messages"],
                "additionalProperties": True,
            },
            annotations={"readOnlyHint": True, "openWorldHint": True},
        ),
        ToolDef(
            name="perplexity_reason",
            title="Advanced Reasoning",
            description="对齐官方 Perplexity MCP：推理（内部映射为非官方 SDK 的 reasoning 模式）。",
            input_schema={
                "type": "object",
                "properties": {
                    "messages": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "role": {"type": "string"},
                                "content": {"type": "string"},
                            },
                            "required": ["role", "content"],
                            "additionalProperties": True,
                        },
                        "minItems": 1,
                    },
                    "strip_thinking": {"type": "boolean"},
                    "mode": {"type": "string"},
                    "model": {"type": "string"},
                },
                "required": ["messages"],
                "additionalProperties": True,
            },
            annotations={"readOnlyHint": True, "openWorldHint": True},
        ),
        ToolDef(
            name="perplexity_search",
            title="Search the Web",
            description="对齐官方 Perplexity MCP：搜索（当前实现返回回答文本，结构化字段尽量附带）。",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "max_results": {"type": "number"},
                    "max_tokens_per_page": {"type": "number"},
                    "country": {"type": "string"},
                    "mode": {"type": "string"},
                    "model": {"type": "string"},
                },
                "required": ["query"],
                "additionalProperties": True,
            },
            annotations={"readOnlyHint": True, "openWorldHint": True},
        ),
    ]

    # MCP tools/list 期望字段为 inputSchema（驼峰），这里做一次格式化输出
    result: List[JsonObject] = []
    for t in tools:
        item: JsonObject = {
            "name": t.name,
            "description": t.description,
            "inputSchema": t.input_schema,
        }
        if t.title:
            item["title"] = t.title
        if t.annotations:
            item["annotations"] = t.annotations
        result.append(item)
    return result


def _tool_result_text(text: str, *, structured: Optional[JsonObject] = None, is_error: bool = False) -> JsonObject:
    result: JsonObject = {"content": [{"type": "text", "text": text}]}
    if structured is not None:
        result["structuredContent"] = structured
    if is_error:
        result["isError"] = True
    return result


def _read_optional_str(arguments: Mapping[str, Any], key: str) -> Tuple[Optional[str], Optional[str]]:
    """
    读取可选字符串参数。

    返回 (value, error_message)。
    """
    value = arguments.get(key)
    if value is None:
        return None, None
    if not isinstance(value, str):
        return None, f"参数错误：{key} 必须是字符串"
    v = value.strip()
    if not v:
        return None, f"参数错误：{key} 不能为空字符串"
    return v, None


def _cookies_provided(config: AppConfig) -> bool:
    cookies = getattr(config, "cookies", {})
    if not isinstance(cookies, Mapping):
        return False
    csrf = cookies.get("next-auth.csrf-token")
    session = cookies.get("next-auth.session-token")
    return isinstance(csrf, str) and bool(csrf.strip()) and isinstance(session, str) and bool(session.strip())


def _default_mode_for_tool(name: str, *, has_cookies: bool) -> str:
    if name in {"perplexity_ask", "perplexity_search"}:
        return "pro" if has_cookies else "auto"
    if name == "perplexity_research":
        return "deep research"
    if name == "perplexity_reason":
        return "reasoning"
    return "auto"


def _resolve_mode_model(config: AppConfig, tool_name: str, arguments: Mapping[str, Any]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    解析并推导本次调用的 mode/model。

    返回 (mode, model, error_message)。
    """
    mode, mode_err = _read_optional_str(arguments, "mode")
    if mode_err:
        return None, None, mode_err

    model, model_err = _read_optional_str(arguments, "model")
    if model_err:
        return None, None, model_err

    has_cookies = _cookies_provided(config)

    effective_mode = mode if mode is not None else _default_mode_for_tool(tool_name, has_cookies=has_cookies)

    effective_model = model
    if effective_model is None and has_cookies and effective_mode == "pro":
        effective_model = "gpt-5.2"

    return effective_mode, effective_model, None


def call_tool(config: AppConfig, name: str, arguments: Mapping[str, Any]) -> JsonObject:
    try:
        effective_mode, effective_model, mode_model_err = _resolve_mode_model(config, name, arguments)
        if mode_model_err:
            return _tool_result_text(mode_model_err, is_error=True)

        if name == "perplexity_ask":
            messages = arguments.get("messages")
            if not isinstance(messages, list):
                return _tool_result_text("参数错误：messages 必须是数组", is_error=True)
            query = messages_to_query(messages)
            resp = call_perplexity_search(
                config,
                query=query,
                mode=effective_mode or "auto",
                model=effective_model,
                sources=["web"],
            )
            structured: JsonObject = {"response": resp.answer}
            if resp.chunks is not None:
                structured["chunks"] = resp.chunks
            return _tool_result_text(resp.answer, structured=structured)

        if name == "perplexity_research":
            messages = arguments.get("messages")
            if not isinstance(messages, list):
                return _tool_result_text("参数错误：messages 必须是数组", is_error=True)
            strip = bool(arguments.get("strip_thinking", False))
            query = messages_to_query(messages)
            resp = call_perplexity_search(
                config,
                query=query,
                mode=effective_mode or "deep research",
                model=effective_model,
                sources=["web"],
            )
            text = strip_thinking_tokens(resp.answer) if strip else resp.answer
            structured: JsonObject = {"response": text}
            if resp.chunks is not None:
                structured["chunks"] = resp.chunks
            return _tool_result_text(text, structured=structured)

        if name == "perplexity_reason":
            messages = arguments.get("messages")
            if not isinstance(messages, list):
                return _tool_result_text("参数错误：messages 必须是数组", is_error=True)
            strip = bool(arguments.get("strip_thinking", False))
            query = messages_to_query(messages)
            resp = call_perplexity_search(
                config,
                query=query,
                mode=effective_mode or "reasoning",
                model=effective_model,
                sources=["web"],
            )
            text = strip_thinking_tokens(resp.answer) if strip else resp.answer
            structured = {"response": text}
            if resp.chunks is not None:
                structured["chunks"] = resp.chunks
            return _tool_result_text(text, structured=structured)

        if name == "perplexity_search":
            query = arguments.get("query")
            if not isinstance(query, str) or not query.strip():
                return _tool_result_text("参数错误：query 必须是非空字符串", is_error=True)
            resp = call_perplexity_search(
                config,
                query=query.strip(),
                mode=effective_mode or "auto",
                model=effective_model,
                sources=["web"],
            )
            structured = {"results": resp.answer}
            if resp.chunks is not None:
                structured["chunks"] = resp.chunks
            return _tool_result_text(resp.answer, structured=structured)

        return _tool_result_text(f"工具不存在：{name}", is_error=True)
    except PerplexityCallError as exc:
        return _tool_result_text(str(exc), is_error=True)
