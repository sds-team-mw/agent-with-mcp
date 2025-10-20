#!/usr/bin/env python3
from app import mcp

if __name__ == "__main__":
    # SSE 기반 독립 서버로 실행. 기본 접속 URL: http://127.0.0.1:8765/sse
    mcp.run(transport="sse", host="127.0.0.1", port=8765)


