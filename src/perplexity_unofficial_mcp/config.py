import os
import secrets
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional


class ConfigError(Exception):
    """配置错误（例如 Cookies 缺失或 JSON 无法解析）。"""


@dataclass(frozen=True)
class AppConfig:
    cookies: Mapping[str, str]
    timeout_ms: int


def _parse_timeout_ms(value: Optional[str]) -> int:
    if not value:
        return 300_000
    try:
        timeout_ms = int(value)
    except ValueError as exc:
        raise ConfigError("PERPLEXITY_TIMEOUT_MS 必须是整数毫秒") from exc
    if timeout_ms <= 0:
        raise ConfigError("PERPLEXITY_TIMEOUT_MS 必须大于 0")
    return timeout_ms


def _random_placeholder_token() -> str:
    """
    生成随机占位 token。

    说明：用于在未配置 Cookies token 时满足上游 SDK 对 cookies 形态的要求；
    占位值不代表真实登录态，且不得写入 stdout/stderr。
    """
    return secrets.token_urlsafe(32)


def _load_cookies_from_env(e: Mapping[str, str]) -> Dict[str, str]:
    csrf = (e.get("PERPLEXITY_CSRF_TOKEN") or "").strip()
    session = (e.get("PERPLEXITY_SESSION_TOKEN") or "").strip()

    # 破坏性变更：旧入口已移除，但为了可诊断性，若检测到旧变量仍存在则给出迁移提示
    # 兼容：若用户已开始迁移并提供了任意一个新变量，则不阻断启动（缺失项会由占位值补齐）。
    if (e.get("PERPLEXITY_COOKIES_JSON") or e.get("PERPLEXITY_COOKIES_PATH")) and not (csrf or session):
        raise ConfigError(
            "已移除 PERPLEXITY_COOKIES_JSON / PERPLEXITY_COOKIES_PATH；请改用 "
            "PERPLEXITY_CSRF_TOKEN 与 PERPLEXITY_SESSION_TOKEN"
        )

    if not csrf:
        csrf = _random_placeholder_token()
    if not session:
        session = _random_placeholder_token()

    return {
        "next-auth.csrf-token": csrf,
        "next-auth.session-token": session,
    }


def load_config(env: Optional[Mapping[str, str]] = None) -> AppConfig:
    """
    从环境变量加载配置。

    已确认约定：
    - PERPLEXITY_CSRF_TOKEN：可选（缺失/为空会自动生成占位值）
    - PERPLEXITY_SESSION_TOKEN：可选（缺失/为空会自动生成占位值）
    - PERPLEXITY_TIMEOUT_MS：可选
    """
    e = dict(env) if env is not None else os.environ

    cookies = _load_cookies_from_env(e)

    timeout_ms = _parse_timeout_ms(e.get("PERPLEXITY_TIMEOUT_MS"))
    return AppConfig(cookies=cookies, timeout_ms=timeout_ms)


def redact_env(env: Mapping[str, str]) -> Dict[str, Any]:
    """
    用于日志输出的环境变量脱敏。
    """
    result: Dict[str, Any] = {}
    for k, v in env.items():
        if k in {"PERPLEXITY_CSRF_TOKEN", "PERPLEXITY_SESSION_TOKEN"}:
            result[k] = "***REDACTED***"
        elif k in {"PERPLEXITY_COOKIES_JSON", "PERPLEXITY_COOKIES_PATH"}:
            result[k] = "***REDACTED***"
        else:
            result[k] = v
    return result
