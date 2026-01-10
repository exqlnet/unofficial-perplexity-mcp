import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import unittest

from perplexity_unofficial_mcp.config import AppConfig
from perplexity_unofficial_mcp.perplexity_adapter import PerplexityResult
from perplexity_unofficial_mcp import tools as tools_mod


class TestModeModel(unittest.TestCase):
    def test_ask_defaults_to_pro_gpt52_when_has_cookies(self) -> None:
        calls = []

        def fake_call(config, *, query, mode, sources=None, model=None, **kwargs):  # type: ignore[no-untyped-def]
            calls.append({"mode": mode, "model": model, "query": query})
            return PerplexityResult(answer="ok", raw={})

        original = tools_mod.call_perplexity_search
        tools_mod.call_perplexity_search = fake_call  # type: ignore[assignment]
        try:
            cfg = AppConfig(
                cookies={
                    "next-auth.csrf-token": "csrf",
                    "next-auth.session-token": "session",
                },
                timeout_ms=300_000,
            )
            res = tools_mod.call_tool(
                cfg,
                "perplexity_ask",
                {"messages": [{"role": "user", "content": "hi"}]},
            )
            self.assertFalse(res.get("isError"))
            self.assertEqual(calls[0]["mode"], "pro")
            self.assertEqual(calls[0]["model"], "gpt-5.2")
        finally:
            tools_mod.call_perplexity_search = original  # type: ignore[assignment]

    def test_search_defaults_to_pro_gpt52_when_has_cookies(self) -> None:
        calls = []

        def fake_call(config, *, query, mode, sources=None, model=None, **kwargs):  # type: ignore[no-untyped-def]
            calls.append({"mode": mode, "model": model, "query": query})
            return PerplexityResult(answer="ok", raw={})

        original = tools_mod.call_perplexity_search
        tools_mod.call_perplexity_search = fake_call  # type: ignore[assignment]
        try:
            cfg = AppConfig(
                cookies={
                    "next-auth.csrf-token": "csrf",
                    "next-auth.session-token": "session",
                },
                timeout_ms=300_000,
            )
            res = tools_mod.call_tool(cfg, "perplexity_search", {"query": "hello"})
            self.assertFalse(res.get("isError"))
            self.assertEqual(calls[0]["mode"], "pro")
            self.assertEqual(calls[0]["model"], "gpt-5.2")
        finally:
            tools_mod.call_perplexity_search = original  # type: ignore[assignment]

    def test_research_keeps_default_mode(self) -> None:
        calls = []

        def fake_call(config, *, query, mode, sources=None, model=None, **kwargs):  # type: ignore[no-untyped-def]
            calls.append({"mode": mode, "model": model, "query": query})
            return PerplexityResult(answer="ok", raw={})

        original = tools_mod.call_perplexity_search
        tools_mod.call_perplexity_search = fake_call  # type: ignore[assignment]
        try:
            cfg = AppConfig(
                cookies={
                    "next-auth.csrf-token": "csrf",
                    "next-auth.session-token": "session",
                },
                timeout_ms=300_000,
            )
            res = tools_mod.call_tool(
                cfg,
                "perplexity_research",
                {"messages": [{"role": "user", "content": "topic"}]},
            )
            self.assertFalse(res.get("isError"))
            self.assertEqual(calls[0]["mode"], "deep research")
            self.assertIsNone(calls[0]["model"])
        finally:
            tools_mod.call_perplexity_search = original  # type: ignore[assignment]

    def test_override_mode_sets_default_model_when_pro(self) -> None:
        calls = []

        def fake_call(config, *, query, mode, sources=None, model=None, **kwargs):  # type: ignore[no-untyped-def]
            calls.append({"mode": mode, "model": model, "query": query})
            return PerplexityResult(answer="ok", raw={})

        original = tools_mod.call_perplexity_search
        tools_mod.call_perplexity_search = fake_call  # type: ignore[assignment]
        try:
            cfg = AppConfig(
                cookies={
                    "next-auth.csrf-token": "csrf",
                    "next-auth.session-token": "session",
                },
                timeout_ms=300_000,
            )
            res = tools_mod.call_tool(
                cfg,
                "perplexity_reason",
                {"messages": [{"role": "user", "content": "why"}], "mode": "pro"},
            )
            self.assertFalse(res.get("isError"))
            self.assertEqual(calls[0]["mode"], "pro")
            self.assertEqual(calls[0]["model"], "gpt-5.2")
        finally:
            tools_mod.call_perplexity_search = original  # type: ignore[assignment]

    def test_invalid_mode_type_is_tool_error(self) -> None:
        cfg = AppConfig(
            cookies={
                "next-auth.csrf-token": "csrf",
                "next-auth.session-token": "session",
            },
            timeout_ms=300_000,
        )
        res = tools_mod.call_tool(
            cfg,
            "perplexity_ask",
            {"messages": [{"role": "user", "content": "hi"}], "mode": 123},
        )
        self.assertTrue(res.get("isError"))


if __name__ == "__main__":
    unittest.main()

