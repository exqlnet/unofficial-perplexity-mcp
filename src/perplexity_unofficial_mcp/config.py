import json
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


def _load_cookies_from_json(value: str) -> Dict[str, str]:
    try:
        data = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ConfigError("PERPLEXITY_COOKIES_JSON 不是合法的 JSON") from exc
    if not isinstance(data, dict):
        raise ConfigError("PERPLEXITY_COOKIES_JSON 必须是对象（键值对）")

    cookies: Dict[str, str] = {}
    for key, cookie_value in data.items():
        if not isinstance(key, str) or not key.strip():
            raise ConfigError("PERPLEXITY_COOKIES_JSON 的键必须是非空字符串")
        if not isinstance(cookie_value, str) or not cookie_value.strip():
            raise ConfigError(f"PERPLEXITY_COOKIES_JSON 中 {key!r} 的值必须是非空字符串")
        cookies[key] = cookie_value
    if not cookies:
        raise ConfigError("PERPLEXITY_COOKIES_JSON 不能为空对象")
    return cookies


def _load_cookies_from_path(path: str) -> Dict[str, str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError as exc:
        raise ConfigError("PERPLEXITY_COOKIES_PATH 指向的文件无法读取") from exc
    return _load_cookies_from_json(content)


def load_config(env: Optional[Mapping[str, str]] = None) -> AppConfig:
    """
    从环境变量加载配置。

    已确认约定：
    - PERPLEXITY_COOKIES_JSON：必选
    - PERPLEXITY_TIMEOUT_MS：可选

    可选兼容：
    - PERPLEXITY_COOKIES_PATH：用于不便传长 JSON 的环境
    """
    e = dict(env) if env is not None else os.environ

    cookies_json = e.get("PERPLEXITY_COOKIES_JSON")
    cookies_path = e.get("PERPLEXITY_COOKIES_PATH")

    if cookies_json:
        cookies = _load_cookies_from_json(cookies_json)
    elif cookies_path:
        cookies = _load_cookies_from_path(cookies_path)
    else:
        raise ConfigError("必须提供 PERPLEXITY_COOKIES_JSON（或可选的 PERPLEXITY_COOKIES_PATH）")

    timeout_ms = _parse_timeout_ms(e.get("PERPLEXITY_TIMEOUT_MS"))
    return AppConfig(cookies=cookies, timeout_ms=timeout_ms)


def redact_env(env: Mapping[str, str]) -> Dict[str, Any]:
    """
    用于日志输出的环境变量脱敏。
    """
    result: Dict[str, Any] = {}
    for k, v in env.items():
        if k in {"PERPLEXITY_COOKIES_JSON"}:
            result[k] = "***REDACTED***"
        else:
            result[k] = v
    return result

