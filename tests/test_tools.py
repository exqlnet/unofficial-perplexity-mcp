import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import unittest

from perplexity_unofficial_mcp.tools import list_tools


class TestTools(unittest.TestCase):
    def test_tools_list_contains_official_names(self) -> None:
        tools = list_tools()
        names = {t["name"] for t in tools}
        self.assertIn("perplexity_ask", names)
        self.assertIn("perplexity_research", names)
        self.assertIn("perplexity_reason", names)
        self.assertIn("perplexity_search", names)

    def test_tools_have_input_schema(self) -> None:
        tools = list_tools()
        for t in tools:
            self.assertIn("inputSchema", t)
            self.assertIsInstance(t["inputSchema"], dict)


if __name__ == "__main__":
    unittest.main()
