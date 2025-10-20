#!/usr/bin/env python3
import asyncio
import json
import os
from pathlib import Path
from fastmcp import Client
from typing import Any, Dict
from pydantic import create_model
from langchain.tools import StructuredTool
from langchain_openai import ChatOpenAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# utils 재사용을 위해 경로 추가
import sys
sys.path.append(str(Path(__file__).parent))
from utils import print_available_tools

# OPENAI 키는 환경변수 OPENAI_API_KEY로 제공하세요 (예: PowerShell → $env:OPENAI_API_KEY = 'YOUR_API_KEY')

async def main() -> None:
    # openai_llm.py와 동일한 방식: 별도의 .env 로드/프록시 조작 없이 사용
    config_path = os.getenv("MCP_SERVERS_CONFIG", str(Path(__file__).parent.parent / "mcp_servers.json"))
    print(f"🗂️ 멀티 서버 설정: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    servers = list(config.get("mcpServers", {}).keys())
    print(f"🔗 대상 서버들: {', '.join(servers) if servers else '(없음)'}")
    print()

    async with Client(config) as client:
        # 전체 서버 툴 조회(선택적 출력)
        await print_available_tools(client)

        # MCP 툴 → LangChain StructuredTool 변환 유틸
        def pyd_model_from_json_schema(name: str, schema: Dict[str, Any]):
            schema = schema or {"type": "object", "properties": {}}
            props = schema.get("properties", {})
            req = set(schema.get("required", []))
            def pytype(t: str):
                return {
                    "integer": int,
                    "number": float,
                    "boolean": bool,
                    "object": dict,
                    "array": list,
                }.get(t, str)
            fields = {k: (pytype(v.get("type", "string")), ... if k in req else None) for k, v in props.items()}
            return create_model(name, **fields) if fields else create_model(name)

        def make_langchain_tool(t: Any) -> StructuredTool:
            name = getattr(t, "name", None) or (t.get("name") if isinstance(t, dict) else None)
            desc = getattr(t, "description", "") or (t.get("description") if isinstance(t, dict) else "")
            params = getattr(t, "inputSchema", None) or (t.get("inputSchema") if isinstance(t, dict) else None)
            ArgsModel = pyd_model_from_json_schema(f"{name}_Args", params)

            async def _acall(**kwargs):
                res = await client.call_tool(name, kwargs)
                if hasattr(res, "content") and res.content:
                    texts = [c.text for c in res.content if hasattr(c, "text")]
                    return "\n".join(texts) if texts else str(res)
                return str(res)

            return StructuredTool.from_function(
                name=name,
                description=desc,
                args_schema=ArgsModel,
                coroutine=_acall,
            )

        # MCP에서 툴 메타데이터 수집 후 LangChain 도구로 변환
        mcp_tools = await client.list_tools()
        lc_tools = [make_langchain_tool(t) for t in mcp_tools]

        # LangChain 에이전트 구성: 모델이 자연어로 툴 선택/호출
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        prompt = ChatPromptTemplate.from_messages([
            ("system", "너는 제공된 MCP 툴 중 적절한 것을 선택해 호출한다. 필요 없으면 직접 답하라."),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        agent = create_tool_calling_agent(llm, lc_tools, prompt)
        executor = AgentExecutor(agent=agent, tools=lc_tools, verbose=True, handle_parsing_errors=True)

        # 모델이 직접 말하도록 입력 제공
        user_query = "돈 12345 지불해"
        result = await executor.ainvoke({"input": user_query})
        print(result.get("output", "(출력 없음)"))

        print()
        print("✨ 멀티 서버 테스트 완료!")

if __name__ == "__main__":
    asyncio.run(main())


