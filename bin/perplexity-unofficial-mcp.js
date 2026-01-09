#!/usr/bin/env node

const { spawn } = require("node:child_process");
const path = require("node:path");

function main() {
  const projectRoot = path.resolve(__dirname, "..");

  // 注意：为避免污染 MCP STDIO 协议，启动器自身不得向 stdout 写任何内容
  // uv 的输出默认会走 stdout/stderr，这里使用 -q 尽量抑制 uv 自身输出
  const uvBin = process.env.UV_BIN || "uv";
  const args = ["-q", "run", "perplexity-unofficial-mcp"];

  const child = spawn(uvBin, args, {
    cwd: projectRoot,
    stdio: "inherit",
    env: {
      ...process.env,
      UV_NO_PROGRESS: process.env.UV_NO_PROGRESS || "1",
      UV_COLOR: process.env.UV_COLOR || "never",
    },
  });

  child.on("error", (err) => {
    if (err && err.code === "ENOENT") {
      console.error("未找到 uv。请先安装 uv：https://docs.astral.sh/uv/");
      console.error("你也可以设置环境变量 UV_BIN 指向 uv 可执行文件路径。");
    } else {
      console.error("启动失败：", err);
    }
    process.exit(1);
  });

  child.on("exit", (code, signal) => {
    if (signal) {
      process.exit(1);
    }
    process.exit(typeof code === "number" ? code : 1);
  });
}

main();
