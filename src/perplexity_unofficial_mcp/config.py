import os
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


def _load_cookies_from_env(e: Mapping[str, str]) -> Dict[str, str]:
    csrf = (e.get("PERPLEXITY_CSRF_TOKEN") or "").strip()
    session = (e.get("PERPLEXITY_SESSION_TOKEN") or "").strip()

    if csrf and session:
        return {
            "next-auth.csrf-token": csrf,
            "next-auth.session-token": session,
        }

    # 破坏性变更：旧入口已移除，但为了可诊断性，若检测到旧变量仍存在则给出迁移提示
    if e.get("PERPLEXITY_COOKIES_JSON") or e.get("PERPLEXITY_COOKIES_PATH"):
        raise ConfigError(
            "已移除 PERPLEXITY_COOKIES_JSON / PERPLEXITY_COOKIES_PATH；请改用 "
            "PERPLEXITY_CSRF_TOKEN 与 PERPLEXITY_SESSION_TOKEN"
        )

    if not csrf and not session:
        raise ConfigError("必须提供 PERPLEXITY_CSRF_TOKEN 与 PERPLEXITY_SESSION_TOKEN")
    if not csrf:
        raise ConfigError("缺少 PERPLEXITY_CSRF_TOKEN")
    raise ConfigError("缺少 PERPLEXITY_SESSION_TOKEN")


def load_config(env: Optional[Mapping[str, str]] = None) -> AppConfig:
    """
    从环境变量加载配置。

    已确认约定：
    - PERPLEXITY_CSRF_TOKEN：必选
    - PERPLEXITY_SESSION_TOKEN：必选
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
