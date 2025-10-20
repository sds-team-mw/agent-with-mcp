#!/usr/bin/env python3
import re
from datetime import datetime
from fastmcp import FastMCP

# FastMCP 서버 인스턴스 (단일 책임: MCP 서버와 도구 정의)
mcp = FastMCP("pay-server")

@mcp.tool
def pay_amount(amount: int) -> str:
    """정수 금액(원)을 입력받아 지불 처리 후 확인 메시지를 반환합니다.

    Args:
        amount: 지불 금액(원). 0 이상 정수. 예: 12345

    Returns:
        지불 결과 메시지 문자열
    """
    if amount < 0:
        return "❌ 금액은 0 이상이어야 합니다."

    paid_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"✅ 지불 완료!\n금액: {amount:,}원\n시각: {paid_at}"


