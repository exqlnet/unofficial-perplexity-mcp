import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import unittest

from perplexity_unofficial_mcp.config import AppConfig
from perplexity_unofficial_mcp.perplexity_adapter import call_perplexity_search


class TestFollowUpBackendUuid(unittest.TestCase):
    def test_adapter_passes_follow_up_when_backend_uuid_provided(self) -> None:
        fake_mod = types.SimpleNamespace()
        calls = []

        class FakeClient:
            def __init__(self, cookies):  # type: ignore[no-untyped-def]
                self.cookies = cookies

            def search(  # type: ignore[no-untyped-def]
                self,
                query,
                mode="auto",
                model=None,
                sources=None,
                files=None,
                stream=False,
                language="en-US",
                follow_up=None,
                incognito=False,
            ):
                calls.append({"follow_up": follow_up, "query": query, "mode": mode})
                return {"answer": "ok", "backend_uuid": "new-backend-uuid"}

        fake_mod.Client = FakeClient

        original = sys.modules.get("perplexity")
        sys.modules["perplexity"] = fake_mod  # type: ignore[assignment]
        try:
            cfg = AppConfig(
                cookies={
                    "next-auth.csrf-token": "csrf",
                    "next-auth.session-token": "session",
                },
                timeout_ms=300_000,
            )
            res = call_perplexity_search(
                cfg,
                query="hi",
                mode="auto",
                sources=["web"],
                backend_uuid="prev-backend-uuid",
            )
            self.assertEqual(calls[0]["follow_up"], {"backend_uuid": "prev-backend-uuid", "attachments": []})
            self.assertEqual(res.backend_uuid, "new-backend-uuid")
        finally:
            if original is None:
                del sys.modules["perplexity"]
            else:
                sys.modules["perplexity"] = original

    def test_adapter_omits_follow_up_when_backend_uuid_missing(self) -> None:
        fake_mod = types.SimpleNamespace()
        calls = []

        class FakeClient:
            def __init__(self, cookies):  # type: ignore[no-untyped-def]
                self.cookies = cookies

            def search(  # type: ignore[no-untyped-def]
                self,
                query,
                mode="auto",
                model=None,
                sources=None,
                files=None,
                stream=False,
                language="en-US",
                follow_up=None,
                incognito=False,
            ):
                calls.append({"follow_up": follow_up})
                return {"answer": "ok"}

        fake_mod.Client = FakeClient

        original = sys.modules.get("perplexity")
        sys.modules["perplexity"] = fake_mod  # type: ignore[assignment]
        try:
            cfg = AppConfig(
                cookies={
                    "next-auth.csrf-token": "csrf",
                    "next-auth.session-token": "session",
                },
                timeout_ms=300_000,
            )
            _res = call_perplexity_search(
                cfg,
                query="hi",
                mode="auto",
                sources=["web"],
                backend_uuid=None,
            )
            self.assertIsNone(calls[0]["follow_up"])
        finally:
            if original is None:
                del sys.modules["perplexity"]
            else:
                sys.modules["perplexity"] = original


if __name__ == "__main__":
    unittest.main()

