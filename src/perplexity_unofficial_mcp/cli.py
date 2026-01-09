import sys

from .mcp_stdio import run_stdio_server


def main() -> None:
    """
    CLI 入口：启动 MCP STDIO Server。
    """
    try:
        run_stdio_server()
    except Exception:
        # 任何未捕获异常都必须走 stderr，避免污染 stdout
        raise


if __name__ == "__main__":
    main()

