from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Tuple

from .config import AppConfig
from .perplexity_adapter import (
    PerplexityCallError,
    call_perplexity_search,
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
    usage_hint = "请避免频繁调用；尽量将多个子问题合并到一次 query / 一次 perplexity_search 中查清楚。"
    backend_uuid_desc = (
        "续问用的会话标识。通常应直接使用上一轮工具返回的 structuredContent.backend_uuid；"
        "若不提供则视为新对话。"
    )
    tools: List[ToolDef] = [
        ToolDef(
            name="perplexity_ask",
            title="Ask Perplexity",
            description=f"对齐官方 Perplexity MCP：输入 query 字符串并返回回答文本。{usage_hint}",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "backend_uuid": {"type": "string", "description": backend_uuid_desc},
                },
                "required": ["query"],
                "additionalProperties": True,
            },
            annotations={"readOnlyHint": True, "openWorldHint": True},
        ),
        ToolDef(
            name="perplexity_research",
            title="Deep Research（重型）",
            description=f"对齐官方 Perplexity MCP：深度研究（重型调用，耗时更长；仅在必要时使用，优先 ask/search）。{usage_hint}",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "backend_uuid": {"type": "string", "description": backend_uuid_desc},
                    "strip_thinking": {"type": "boolean"},
                },
                "required": ["query"],
                "additionalProperties": True,
            },
            annotations={"readOnlyHint": True, "openWorldHint": True},
        ),
        ToolDef(
            name="perplexity_reason",
            title="Advanced Reasoning",
            description=f"对齐官方 Perplexity MCP：推理（默认 reasoning）。{usage_hint}",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "backend_uuid": {"type": "string", "description": backend_uuid_desc},
                    "strip_thinking": {"type": "boolean"},
                },
                "required": ["query"],
                "additionalProperties": True,
            },
            annotations={"readOnlyHint": True, "openWorldHint": True},
        ),
        ToolDef(
            name="perplexity_search",
            title="Search the Web",
            description=f"对齐官方 Perplexity MCP：搜索（当前实现返回回答文本，结构化字段尽量附带）。{usage_hint}",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "backend_uuid": {"type": "string", "description": backend_uuid_desc},
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


def _read_required_query(arguments: Mapping[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    query = arguments.get("query")
    if not isinstance(query, str) or not query.strip():
        return None, "参数错误：query 必须是非空字符串"
    return query.strip(), None


def _read_optional_backend_uuid(arguments: Mapping[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    if "backend_uuid" not in arguments:
        return None, None
    backend_uuid = arguments.get("backend_uuid")
    if not isinstance(backend_uuid, str):
        return None, "参数错误：backend_uuid 必须是字符串（可选）"
    if not backend_uuid.strip():
        return None, "参数错误：backend_uuid 不能为空字符串"
    return backend_uuid.strip(), None


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


def _resolve_effective_mode_model(config: AppConfig, tool_name: str) -> Tuple[str, Optional[str]]:
    """
    推导本次调用的内部 mode/model。

    说明：已禁用外部传入 mode/model，避免调用方误传导致行为不可预测。
    """
    has_cookies = _cookies_provided(config)
    mode = _default_mode_for_tool(tool_name, has_cookies=has_cookies)
    model: Optional[str] = None
    if has_cookies and mode == "pro":
        model = "gpt-5.2"
    return mode, model


def call_tool(config: AppConfig, name: str, arguments: Mapping[str, Any]) -> JsonObject:
    try:
        if "messages" in arguments:
            return _tool_result_text("参数错误：已不再支持 messages，请改用 query 字符串入参", is_error=True)
        if "mode" in arguments:
            return _tool_result_text("参数错误：已禁用 mode 入参，请移除该字段并使用默认策略", is_error=True)
        if "model" in arguments:
            return _tool_result_text("参数错误：已禁用 model 入参，请移除该字段并使用默认策略", is_error=True)

        effective_mode, effective_model = _resolve_effective_mode_model(config, name)
        backend_uuid, backend_uuid_err = _read_optional_backend_uuid(arguments)
        if backend_uuid_err:
            return _tool_result_text(backend_uuid_err, is_error=True)

        if name == "perplexity_ask":
            query, query_err = _read_required_query(arguments)
            if query_err:
                return _tool_result_text(query_err, is_error=True)
            resp = call_perplexity_search(
                config,
                query=query or "",
                mode=effective_mode or "auto",
                model=effective_model,
                sources=["web"],
                backend_uuid=backend_uuid,
            )
            structured: JsonObject = {"response": resp.answer}
            if resp.chunks is not None:
                structured["chunks"] = resp.chunks
            if resp.backend_uuid:
                structured["backend_uuid"] = resp.backend_uuid
            return _tool_result_text(resp.answer, structured=structured)

        if name == "perplexity_research":
            strip = bool(arguments.get("strip_thinking", False))
            query, query_err = _read_required_query(arguments)
            if query_err:
                return _tool_result_text(query_err, is_error=True)
            resp = call_perplexity_search(
                config,
                query=query or "",
                mode=effective_mode or "deep research",
                model=effective_model,
                sources=["web"],
                backend_uuid=backend_uuid,
            )
            text = strip_thinking_tokens(resp.answer) if strip else resp.answer
            structured: JsonObject = {"response": text}
            if resp.chunks is not None:
                structured["chunks"] = resp.chunks
            if resp.backend_uuid:
                structured["backend_uuid"] = resp.backend_uuid
            return _tool_result_text(text, structured=structured)

        if name == "perplexity_reason":
            strip = bool(arguments.get("strip_thinking", False))
            query, query_err = _read_required_query(arguments)
            if query_err:
                return _tool_result_text(query_err, is_error=True)
            resp = call_perplexity_search(
                config,
                query=query or "",
                mode=effective_mode or "reasoning",
                model=effective_model,
                sources=["web"],
                backend_uuid=backend_uuid,
            )
            text = strip_thinking_tokens(resp.answer) if strip else resp.answer
            structured = {"response": text}
            if resp.chunks is not None:
                structured["chunks"] = resp.chunks
            if resp.backend_uuid:
                structured["backend_uuid"] = resp.backend_uuid
            return _tool_result_text(text, structured=structured)

        if name == "perplexity_search":
            query, query_err = _read_required_query(arguments)
            if query_err:
                return _tool_result_text(query_err, is_error=True)
            resp = call_perplexity_search(
                config,
                query=query or "",
                mode=effective_mode or "auto",
                model=effective_model,
                sources=["web"],
                backend_uuid=backend_uuid,
            )
            structured = {"results": resp.answer}
            if resp.chunks is not None:
                structured["chunks"] = resp.chunks
            if resp.backend_uuid:
                structured["backend_uuid"] = resp.backend_uuid
            return _tool_result_text(resp.answer, structured=structured)

        return _tool_result_text(f"工具不存在：{name}", is_error=True)
    except PerplexityCallError as exc:
        return _tool_result_text(str(exc), is_error=True)
