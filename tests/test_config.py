import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import os
import unittest

from perplexity_unofficial_mcp.config import ConfigError, load_config, redact_env


class TestConfig(unittest.TestCase):
    def test_missing_tokens_generate_placeholders(self) -> None:
        cfg = load_config(env={})
        self.assertIn("next-auth.csrf-token", cfg.cookies)
        self.assertIn("next-auth.session-token", cfg.cookies)
        self.assertIsInstance(cfg.cookies["next-auth.csrf-token"], str)
        self.assertIsInstance(cfg.cookies["next-auth.session-token"], str)
        self.assertTrue(cfg.cookies["next-auth.csrf-token"].strip())
        self.assertTrue(cfg.cookies["next-auth.session-token"].strip())

    def test_load_cookies_env_ok(self) -> None:
        cfg = load_config(
            env={
                "PERPLEXITY_CSRF_TOKEN": "csrf",
                "PERPLEXITY_SESSION_TOKEN": "session",
            }
        )
        self.assertIn("next-auth.session-token", cfg.cookies)
        self.assertEqual(cfg.timeout_ms, 300_000)

    def test_partial_tokens_generate_placeholder_for_missing(self) -> None:
        cfg = load_config(env={"PERPLEXITY_CSRF_TOKEN": "csrf"})
        self.assertEqual(cfg.cookies["next-auth.csrf-token"], "csrf")
        self.assertTrue(cfg.cookies["next-auth.session-token"].strip())

        cfg2 = load_config(env={"PERPLEXITY_SESSION_TOKEN": "session"})
        self.assertTrue(cfg2.cookies["next-auth.csrf-token"].strip())
        self.assertEqual(cfg2.cookies["next-auth.session-token"], "session")

    def test_old_cookie_vars_raise_migration_hint(self) -> None:
        with self.assertRaises(ConfigError) as ctx:
            load_config(env={"PERPLEXITY_COOKIES_JSON": '{"x":"y"}'})
        self.assertIn("已移除", str(ctx.exception))

    def test_redact_env(self) -> None:
        env = {
            "PERPLEXITY_CSRF_TOKEN": "csrf",
            "PERPLEXITY_SESSION_TOKEN": "session",
            "OTHER": "x",
        }
        redacted = redact_env(env)
        self.assertEqual(redacted["PERPLEXITY_CSRF_TOKEN"], "***REDACTED***")
        self.assertEqual(redacted["PERPLEXITY_SESSION_TOKEN"], "***REDACTED***")
        self.assertEqual(redacted["OTHER"], "x")


if __name__ == "__main__":
    unittest.main()
