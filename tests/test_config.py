import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import os
import unittest

from perplexity_unofficial_mcp.config import ConfigError, load_config, redact_env


class TestConfig(unittest.TestCase):
    def test_missing_cookies_raises(self) -> None:
        with self.assertRaises(ConfigError):
            load_config(env={})

    def test_load_cookies_env_ok(self) -> None:
        cfg = load_config(
            env={
                "PERPLEXITY_CSRF_TOKEN": "csrf",
                "PERPLEXITY_SESSION_TOKEN": "session",
            }
        )
        self.assertIn("next-auth.session-token", cfg.cookies)
        self.assertEqual(cfg.timeout_ms, 300_000)

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
