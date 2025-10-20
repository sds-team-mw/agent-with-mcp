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
    server_url = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8765/sse")
    print(f"🔗 MCP 서버(SSE) URL: {server_url}")
    print()

    async with Client(server_url) as client:
        await run_demo(client)

if __name__ == "__main__":
    asyncio.run(main())


