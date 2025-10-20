#!/usr/bin/env python3
from app import mcp

if __name__ == "__main__":
    # STDIO 기반으로 실행 (서브프로세스로 구동 시 권장)
    mcp.run()  # transport="stdio" 기본값


