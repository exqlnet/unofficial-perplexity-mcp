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

    def test_tools_use_query_only(self) -> None:
        tools = list_tools()
        tools_by_name = {t["name"]: t for t in tools}

        for name in ["perplexity_ask", "perplexity_research", "perplexity_reason", "perplexity_search"]:
            schema = tools_by_name[name]["inputSchema"]
            props = schema.get("properties", {})
            self.assertIn("query", props)
            self.assertIn("backend_uuid", props)
            self.assertNotIn("messages", props)
            self.assertNotIn("mode", props)
            self.assertNotIn("model", props)

        search_props = tools_by_name["perplexity_search"]["inputSchema"].get("properties", {})
        self.assertNotIn("max_results", search_props)
        self.assertNotIn("max_tokens_per_page", search_props)
        self.assertNotIn("country", search_props)

    def test_research_is_marked_heavy(self) -> None:
        tools = list_tools()
        t = next(x for x in tools if x["name"] == "perplexity_research")
        self.assertIn("重型", t.get("title", "") + t.get("description", ""))

    def test_tools_warn_about_frequency(self) -> None:
        tools = list_tools()
        for t in tools:
            text = (t.get("title", "") or "") + (t.get("description", "") or "")
            self.assertIn("避免频繁调用", text)


if __name__ == "__main__":
    unittest.main()
