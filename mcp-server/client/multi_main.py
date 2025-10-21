#!/usr/bin/env python3
import asyncio
import json
import os
from pathlib import Path
from fastmcp import Client
from typing import Any, Dict, List, TypedDict
from pydantic import create_model
from langchain.tools import StructuredTool
from langchain_openai import ChatOpenAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END

# utils 재사용을 위해 경로 추가
import sys
sys.path.append(str(Path(__file__).parent))
from utils import print_available_tools

# .env를 로드하여 OPENAI_API_KEY / LANGSMITH 관련 환경변수를 그대로 사용합니다.
load_dotenv()

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

        # 예의(존대말) 및 금액 지불 의사 분기용 LangGraph 구성
        class GraphState(TypedDict):
            input: str
            is_honorific: bool
            intent_pay_amount: bool
            tool_eligible: bool
            output: str

        async def llm_is_honorific(user_input: str) -> bool:
            instruction = (
                "사용자 발화가 한국어 존대말(높임말)인지 판별하라. 반말이거나 애매하면 NO, 존대말이면 YES.\n"
                "반드시 YES 또는 NO만 출력하라. 다른 말 금지."
            )
            prompt_text = f"[Instruction]\n{instruction}\n\n[User Input]\n{user_input}"
            resp = await llm.ainvoke(prompt_text)
            content = getattr(resp, "content", "").strip().upper()
            return content.startswith("Y")

        async def llm_has_pay_amount_intent(user_input: str) -> bool:
            instruction = (
                "다음 사용자 발화에 '금액을 지불(결제)하겠다는 의사'가 분명히 포함되어 있으면 YES,\n"
                "(숫자나 금액 표현 포함 등) 그렇지 않거나 정보가 부족하면 NO만 출력하라. 다른 말 금지."
            )
            prompt_text = f"[Instruction]\n{instruction}\n\n[User Input]\n{user_input}"
            resp = await llm.ainvoke(prompt_text)
            content = getattr(resp, "content", "").strip().upper()
            return content.startswith("Y")

        async def llm_is_purchase_tool_available(user_input: str, tools: List[StructuredTool]) -> bool:
            # LLM에게 도구 목록을 주고, 구매/주문/결제를 수행할 수 있는 적절한 도구 존재 여부를 YES/NO로 판단하게 함
            tool_lines = []
            for tool in tools:
                name = getattr(tool, "name", "")
                desc = getattr(tool, "description", "")
                tool_lines.append(f"- {name}: {desc}")
            tools_text = "\n".join(tool_lines) if tool_lines else "(no tools)"

            instruction = (
                "너는 제공된 MCP 도구 목록을 보고, 사용자 요청이 '특정 상품 구매/주문/결제'를 실제 수행할 수 있는 도구가 있는지 판단한다.\n"
                "도구의 이름/설명 상 해당 액션을 수행할 수 있다고 합리적으로 볼 수 있을 때만 YES, 아니면 NO.\n"
                "반드시 대문자 YES 또는 NO만 출력하라. 추가 설명 금지."
            )
            prompt_text = (
                f"[Instruction]\n{instruction}\n\n"
                f"[User Input]\n{user_input}\n\n"
                f"[Tools]\n{tools_text}\n"
            )
            resp = await llm.ainvoke(prompt_text)
            content = getattr(resp, "content", "").strip().upper()
            return content.startswith("Y")

        async def node_politeness(state: GraphState) -> GraphState:
            text = state["input"]
            is_h = await llm_is_honorific(text)
            return {**state, "is_honorific": is_h}

        def node_polite_warning(state: GraphState) -> GraphState:
            return {**state, "output": "존대말을 써주세요"}

        async def node_classify_pay_amount(state: GraphState) -> GraphState:
            text = state["input"]
            intent = await llm_has_pay_amount_intent(text)
            return {**state, "intent_pay_amount": intent}

        def node_ask_product(state: GraphState) -> GraphState:
            return {
                **state,
                "output": "어떤 상품을 구매하시나요? 구체적으로 알려주세요.",
            }

        async def node_check_tool(state: GraphState) -> GraphState:
            try:
                eligible = await llm_is_purchase_tool_available(state["input"], lc_tools)
            except Exception:
                # 실패 시 보수적으로 False 처리
                eligible = False
            return {**state, "tool_eligible": eligible}

        async def node_agent(state: GraphState) -> GraphState:
            res = await executor.ainvoke({"input": state["input"]})
            out = res.get("output", "(출력 없음)")
            return {**state, "output": out}

        def node_no_tool(state: GraphState) -> GraphState:
            return {**state, "output": "적절한 tool 이 존재하지 않습니다."}

        workflow = StateGraph(GraphState)
        workflow.add_node("politeness", node_politeness)
        workflow.add_node("polite_warning", node_polite_warning)
        workflow.add_node("classify_pay_amount", node_classify_pay_amount)
        workflow.add_node("ask_product", node_ask_product)
        workflow.add_node("check_tool", node_check_tool)
        workflow.add_node("agent", node_agent)
        workflow.add_node("no_tool", node_no_tool)

        workflow.add_edge(START, "politeness")
        # 분기 1: 존대말 여부
        def cond_polite(state: GraphState) -> bool:
            return state.get("is_honorific", False)
        workflow.add_conditional_edges(
            "politeness",
            cond_polite,
            {
                True: "classify_pay_amount",
                False: "polite_warning",
            },
        )
        # 분기 2: 금액 지불 의사 여부
        def cond_pay_amount(state: GraphState) -> bool:
            return state.get("intent_pay_amount", False)
        workflow.add_conditional_edges(
            "classify_pay_amount",
            cond_pay_amount,
            {
                True: "check_tool",
                False: "ask_product",
            },
        )
        # 분기 3: 적절한 구매 관련 툴 존재 여부
        def cond_tool(state: GraphState) -> bool:
            return state.get("tool_eligible", False)
        workflow.add_conditional_edges(
            "check_tool",
            cond_tool,
            {
                True: "agent",
                False: "no_tool",
            },
        )
        workflow.add_edge("ask_product", END)
        workflow.add_edge("polite_warning", END)
        workflow.add_edge("agent", END)
        workflow.add_edge("no_tool", END)

        graph = workflow.compile()
        # LangGraph 그래프 시각화 저장
        try:
            g = graph.get_graph(xray=True)
            g.draw_png("purchase_flow.png")
            g.draw_svg("purchase_flow.svg")
            print("그래프 저장: purchase_flow.png / purchase_flow.svg")
        except Exception as e:
            print(f"그래프 시각화 실패: {e}")

        # 입력 예시 (필요 시 교체)
        user_query = "돈 12345 지불해주세요."
        final_state = await graph.ainvoke({"input": user_query, "is_honorific": False, "intent_pay_amount": False, "tool_eligible": False, "output": ""})
        print(final_state.get("output", "(출력 없음)"))

        print()
        print("✨ 멀티 서버 테스트 완료!")

if __name__ == "__main__":
    asyncio.run(main())


