from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional

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


def call_tool(config: AppConfig, name: str, arguments: Mapping[str, Any]) -> JsonObject:
    try:
        if name == "perplexity_ask":
            messages = arguments.get("messages")
            if not isinstance(messages, list):
                return _tool_result_text("参数错误：messages 必须是数组", is_error=True)
            query = messages_to_query(messages)
            # 对齐官方 perplexity_ask（sonar-pro）的语义：这里默认映射为非官方 SDK 的 pro 模式
            resp = call_perplexity_search(config, query=query, mode="pro", sources=["web"])
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
            resp = call_perplexity_search(config, query=query, mode="deep research", sources=["web"])
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
            resp = call_perplexity_search(config, query=query, mode="reasoning", sources=["web"])
            text = strip_thinking_tokens(resp.answer) if strip else resp.answer
            structured = {"response": text}
            if resp.chunks is not None:
                structured["chunks"] = resp.chunks
            return _tool_result_text(text, structured=structured)

        if name == "perplexity_search":
            query = arguments.get("query")
            if not isinstance(query, str) or not query.strip():
                return _tool_result_text("参数错误：query 必须是非空字符串", is_error=True)
            resp = call_perplexity_search(config, query=query.strip(), mode="auto", sources=["web"])
            structured = {"results": resp.answer}
            if resp.chunks is not None:
                structured["chunks"] = resp.chunks
            return _tool_result_text(resp.answer, structured=structured)

        return _tool_result_text(f"工具不存在：{name}", is_error=True)
    except PerplexityCallError as exc:
        return _tool_result_text(str(exc), is_error=True)
