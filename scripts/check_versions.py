import json
import os
import re
from pathlib import Path


def read_package_version(repo_root: Path) -> str:
    package_json = repo_root / "package.json"
    data = json.loads(package_json.read_text(encoding="utf-8"))
    version = data.get("version")
    if not isinstance(version, str) or not version:
        raise SystemExit("package.json 缺少 version")
    return version


def read_python_version(repo_root: Path) -> str:
    version_py = repo_root / "src" / "perplexity_unofficial_mcp" / "version.py"
    content = version_py.read_text(encoding="utf-8")
    m = re.search(r'__version__\s*=\s*"([^"]+)"', content)
    if not m:
        raise SystemExit("version.py 缺少 __version__")
    return m.group(1)


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    tag = os.environ.get("GITHUB_REF_NAME", "")
    if not tag:
        raise SystemExit("缺少 GITHUB_REF_NAME")
    if not tag.startswith("v"):
        raise SystemExit(f"tag 必须以 v 开头，当前为：{tag}")

    tag_version = tag[1:]
    pkg_version = read_package_version(repo_root)
    py_version = read_python_version(repo_root)

    if pkg_version != tag_version:
        raise SystemExit(f"版本不一致：tag={tag_version} package.json={pkg_version}")
    if py_version != tag_version:
        raise SystemExit(f"版本不一致：tag={tag_version} version.py={py_version}")

    print(f"版本校验通过：{tag_version}")


if __name__ == "__main__":
    main()

