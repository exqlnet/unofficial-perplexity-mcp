from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from .config import AppConfig


class PerplexityCallError(Exception):
    """调用 Perplexity 失败。"""


_THINK_RE = re.compile(r"<think>[\\s\\S]*?<\\/think>", re.MULTILINE)


def strip_thinking_tokens(text: str) -> str:
    return _THINK_RE.sub("", text).strip()


def messages_to_query(messages: List[Mapping[str, Any]]) -> str:
    """
    将官方 MCP 形态的 messages[] 映射为非官方 SDK 需要的 query 字符串。
    """
    parts: List[str] = []
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content")
        if isinstance(role, str) and isinstance(content, str):
            parts.append(f"{role}: {content}")
    # 取最后一条 user 作为主要问题，前面作为上下文
    last_user = next((m.get("content") for m in reversed(messages) if m.get("role") == "user"), None)
    if isinstance(last_user, str) and last_user.strip():
        if parts:
            return "\n".join(parts[:-1] + [f"user: {last_user}"])
        return last_user.strip()
    if parts:
        return "\n".join(parts)
    raise PerplexityCallError("messages 为空或无法提取 content")


@dataclass(frozen=True)
class PerplexityResult:
    answer: str
    raw: Mapping[str, Any]
    chunks: Optional[List[Any]] = None
    backend_uuid: Optional[str] = None


def _extract_answer(payload: Mapping[str, Any]) -> Tuple[str, Optional[List[Any]]]:
    answer = payload.get("answer")
    if isinstance(answer, str) and answer.strip():
        chunks = payload.get("chunks")
        if isinstance(chunks, list):
            return answer, chunks
        return answer, None
    return "", None


def _extract_backend_uuid(payload: Mapping[str, Any]) -> Optional[str]:
    backend_uuid = payload.get("backend_uuid")
    if isinstance(backend_uuid, str) and backend_uuid.strip():
        return backend_uuid.strip()
    return None


def call_perplexity_search(
    config: AppConfig,
    *,
    query: str,
    mode: str,
    sources: Optional[List[str]] = None,
    model: Optional[str] = None,
    language: str = "en-US",
    incognito: bool = False,
    backend_uuid: Optional[str] = None,
) -> PerplexityResult:
    """
    调用非官方 SDK 的 search，返回 answer 与 raw payload。
    """
    try:
        perplexity = __import__("perplexity")
    except Exception as exc:  # noqa: BLE001
        raise PerplexityCallError(
            "无法导入 perplexity SDK。请先确保已安装 ../perplexity-ai 及其依赖。"
        ) from exc

    try:
        client = perplexity.Client(dict(config.cookies))
        follow_up = None
        if isinstance(backend_uuid, str) and backend_uuid.strip():
            follow_up = {"backend_uuid": backend_uuid.strip(), "attachments": []}
        payload = client.search(
            query,
            mode=mode,
            model=model,
            sources=sources or ["web"],
            files={},
            stream=False,
            language=language,
            follow_up=follow_up,
            incognito=incognito,
        )
    except Exception as exc:  # noqa: BLE001
        raise PerplexityCallError(f"Perplexity 调用失败：{exc}") from exc

    if not isinstance(payload, dict):
        raise PerplexityCallError("Perplexity 返回不是对象，无法解析")

    answer, chunks = _extract_answer(payload)
    extracted_backend_uuid = _extract_backend_uuid(payload)
    if not answer:
        # 兜底：某些情况下 SDK 可能只返回 text/其他字段
        fallback = payload.get("text")
        if isinstance(fallback, str) and fallback.strip():
            answer = fallback.strip()
        else:
            answer = "未从 Perplexity 响应中解析出 answer"

    return PerplexityResult(answer=answer, chunks=chunks, raw=payload, backend_uuid=extracted_backend_uuid)
