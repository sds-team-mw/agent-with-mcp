#!/usr/bin/env python3
import asyncio
import os
from pathlib import Path
import sys
from fastmcp import Client

# 스크립트 실행 시 상대 import 보완
sys.path.append(str(Path(__file__).parent))
from utils import run_demo

async def main() -> None:
    default_script = Path(__file__).parent.parent / "server" / "stdio_main.py"
    script_path = os.getenv("MCP_SERVER_SCRIPT", str(default_script))
    print(f"🖥️ STDIO 서버 실행: {script_path}")
    print()

    async with Client(script_path) as client:
        await run_demo(client)

if __name__ == "__main__":
    asyncio.run(main())


