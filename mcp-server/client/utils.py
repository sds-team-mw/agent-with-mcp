#!/usr/bin/env python3
from typing import Any

async def print_available_tools(client: Any) -> None:
    print("📋 사용 가능한 툴:")
    tools = await client.list_tools()
    for tool in tools:
        name = getattr(tool, "name", None) or (tool.get("name") if isinstance(tool, dict) else str(tool))
        desc = getattr(tool, "description", None) or (tool.get("description") if isinstance(tool, dict) else "")
        print(f"   - {name}: {desc}")
    print()

async def run_demo(client: Any) -> None:
    await print_available_tools(client)

    tools = await client.list_tools()
    tool_names = [
        getattr(t, "name", None) or (t.get("name") if isinstance(t, dict) else str(t))
        for t in tools
    ]

    # pay_amount 우선, 접두사 포함 변형도 지원
    chosen_name = None
    for name in tool_names:
        if name.endswith("pay_amount") or name == "pay_amount":
            chosen_name = name
            break
    if chosen_name:
        amount = 12345
        print(f"💰 테스트: {chosen_name}(amount={amount}) 호출")
        result = await client.call_tool(chosen_name, {"amount": amount})
    else:
        # 레거시 pay(command) 대응
        test_command = "돈 12345 지불해"
        fallback_name = None
        for name in tool_names:
            if name.endswith("pay") or name == "pay":
                fallback_name = name
                break
        print(f"💰 테스트: {fallback_name or 'pay'}(command='{test_command}') 호출")
        result = await client.call_tool(fallback_name or "pay", {"command": test_command})

    print()
    print("📤 서버 응답:")
    if hasattr(result, 'content') and result.content:
        for content in result.content:
            if hasattr(content, 'text'):
                print(content.text)
            else:
                print(content)
    else:
        print(result)

    print()
    print("✨ 테스트 완료!")


