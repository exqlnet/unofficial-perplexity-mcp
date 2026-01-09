import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


class TestStdioIntegration(unittest.TestCase):
    def test_initialize_and_tools_list(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        env = os.environ.copy()
        env["PERPLEXITY_CSRF_TOKEN"] = "csrf"
        env["PERPLEXITY_SESSION_TOKEN"] = "session"
        env["PYTHONPATH"] = str(repo_root / "src")

        proc = subprocess.Popen(
            [sys.executable, "-m", "perplexity_unofficial_mcp.cli"],
            cwd=str(repo_root),
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        input_lines = "\n".join(
            [
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {"protocolVersion": "2024-11-05", "capabilities": {}},
                    }
                ),
                json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}),
                "",
            ]
        )

        stdout, stderr = proc.communicate(input=input_lines, timeout=5)

        # stdout 必须只有 MCP 消息（每行都是 JSON-RPC）
        stdout_lines = [line for line in stdout.splitlines() if line.strip()]
        self.assertGreaterEqual(len(stdout_lines), 2)
        parsed = [json.loads(line) for line in stdout_lines]

        self.assertEqual(parsed[0]["jsonrpc"], "2.0")
        self.assertEqual(parsed[0]["id"], 1)
        self.assertIn("result", parsed[0])

        self.assertEqual(parsed[1]["jsonrpc"], "2.0")
        self.assertEqual(parsed[1]["id"], 2)
        self.assertIn("tools", parsed[1]["result"])

        # stderr 允许有日志，但不应包含明文 cookies（这里只做最小断言）
        self.assertNotIn("csrf", stderr)
        self.assertNotIn("session", stderr)

    def test_unknown_tool_is_tool_error(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        env = os.environ.copy()
        env["PERPLEXITY_CSRF_TOKEN"] = "csrf"
        env["PERPLEXITY_SESSION_TOKEN"] = "session"
        env["PYTHONPATH"] = str(repo_root / "src")

        proc = subprocess.Popen(
            [sys.executable, "-m", "perplexity_unofficial_mcp.cli"],
            cwd=str(repo_root),
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        input_lines = "\n".join(
            [
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {"protocolVersion": "2024-11-05", "capabilities": {}},
                    }
                ),
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {"name": "nonexistent_tool", "arguments": {}},
                    }
                ),
                "",
            ]
        )

        stdout, _stderr = proc.communicate(input=input_lines, timeout=5)
        stdout_lines = [line for line in stdout.splitlines() if line.strip()]
        self.assertGreaterEqual(len(stdout_lines), 2)
        res = json.loads(stdout_lines[1])
        self.assertEqual(res["id"], 2)
        self.assertIn("result", res)
        self.assertTrue(res["result"].get("isError"))


if __name__ == "__main__":
    unittest.main()
