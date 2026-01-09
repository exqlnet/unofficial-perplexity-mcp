import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import unittest

from perplexity_unofficial_mcp.jsonrpc import safe_parse_json_line


class TestJsonRpc(unittest.TestCase):
    def test_parse_error(self) -> None:
        req, err = safe_parse_json_line("{not-json")
        self.assertIsNone(req)
        self.assertIsNotNone(err)
        self.assertEqual(err["error"]["code"], -32700)

    def test_invalid_request_missing_method(self) -> None:
        req, err = safe_parse_json_line('{"jsonrpc":"2.0","id":1}')
        self.assertIsNone(req)
        self.assertIsNotNone(err)
        self.assertEqual(err["error"]["code"], -32600)

    def test_valid_request(self) -> None:
        req, err = safe_parse_json_line('{"jsonrpc":"2.0","id":1,"method":"ping","params":{}}')
        self.assertIsNone(err)
        self.assertIsNotNone(req)
        assert req is not None
        self.assertEqual(req.method, "ping")
        self.assertEqual(req.id, 1)


if __name__ == "__main__":
    unittest.main()
