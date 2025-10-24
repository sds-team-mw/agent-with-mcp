#!/usr/bin/env python3
import os
import json
from pathlib import Path
from typing import Any, Dict, List, TypedDict

import asyncio
from dotenv import load_dotenv
from fastmcp import Client
from pydantic import create_model
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END


class GraphState(TypedDict):
    input: str
    is_honorific: bool
    intent_pay_amount: bool
    tool_eligible: bool
    output: str


def _pyd_model_from_json_schema(name: str, schema: Dict[str, Any]):
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


def _make_langchain_tool(client: Client, t: Any) -> StructuredTool:
    name = getattr(t, "name", None) or (t.get("name") if isinstance(t, dict) else None)
    desc = getattr(t, "description", "") or (t.get("description") if isinstance(t, dict) else "")
    params = getattr(t, "inputSchema", None) or (t.get("inputSchema") if isinstance(t, dict) else None)
    ArgsModel = _pyd_model_from_json_schema(f"{name}_Args", params)

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



async def _llm_is_honorific(llm: ChatOpenAI, user_input: str) -> bool:
    instruction = (
        "사용자 발화가 한국어 존대말(높임말)인지 판별하라. 반말이거나 애매하면 NO, 존대말이면 YES.\n"
        "반드시 YES 또는 NO만 출력하라. 다른 말 금지."
    )
    prompt_text = f"[Instruction]\n{instruction}\n\n[User Input]\n{user_input}"
    resp = await llm.ainvoke(prompt_text)
    content = getattr(resp, "content", "").strip().upper()
    return content.startswith("Y")


async def _llm_has_pay_amount_intent(llm: ChatOpenAI, user_input: str) -> bool:
    instruction = (
        "다음 사용자 발화에 '금액을 지불(결제)하겠다는 의사'가 분명히 포함되어 있으면 YES,\n"
        "(숫자나 금액 표현 포함 등) 그렇지 않거나 정보가 부족하면 NO만 출력하라. 다른 말 금지."
    )
    prompt_text = f"[Instruction]\n{instruction}\n\n[User Input]\n{user_input}"
    resp = await llm.ainvoke(prompt_text)
    content = getattr(resp, "content", "").strip().upper()
    return content.startswith("Y")


async def _llm_is_purchase_tool_available(llm: ChatOpenAI, user_input: str, tools: List[StructuredTool]) -> bool:
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


async def run_purchase_flow_once(user_input: str, *, mcp_config_path: str | None = None) -> str:
    """사용자 입력 1건을 LangGraph 분기 + MCP 도구 호출로 처리하여 응답 텍스트를 반환.

    - 환경변수 `MCP_SERVERS_CONFIG`가 있으면 해당 경로 사용, 없으면 기본값(`mcp-server/mcp_servers.json`).
    - LLM 모델은 `LANGGRAPH_MODEL` 환경변수로 지정(기본: gpt-4o-mini).
    """
    load_dotenv()

    config_path = (
        mcp_config_path
        or os.getenv("MCP_SERVERS_CONFIG")
        or str(Path(__file__).parent.parent / "mcp_servers.json")
    )
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    # 컨테이너/배포 환경에서 SSE 서버가 없을 수 있으므로 기본적으로 STDIO 항목만 사용
    # ENABLE_SSE=true 일 때만 url 기반 서버를 유지
    if isinstance(config, dict) and "mcpServers" in config:
        enable_sse = os.getenv("ENABLE_SSE", "false").lower() in {"1", "true", "yes"}
        if not enable_sse:
            pruned = {}
            for name, entry in config["mcpServers"].items():
                if isinstance(entry, dict) and "command" in entry:
                    pruned[name] = entry
            config["mcpServers"] = pruned

    # Client 수명은 그래프 실행 동안 유지되어야 함
    async with Client(config) as client:
        mcp_tools = await client.list_tools()
        lc_tools = [_make_langchain_tool(client, t) for t in mcp_tools]

        model_name = os.getenv("LANGGRAPH_MODEL", "gpt-4o-mini")
        llm = ChatOpenAI(model=model_name, temperature=0)

        async def node_politeness(state: GraphState) -> GraphState:
            text = state["input"]
            is_h = await _llm_is_honorific(llm, text)
            return {**state, "is_honorific": is_h}

        def node_polite_warning(state: GraphState) -> GraphState:
            return {**state, "output": "존대말을 써주세요"}

        async def node_classify_pay_amount(state: GraphState) -> GraphState:
            text = state["input"]
            intent = await _llm_has_pay_amount_intent(llm, text)
            return {**state, "intent_pay_amount": intent}

        def node_ask_product(state: GraphState) -> GraphState:
            return {**state, "output": "어떤 상품을 구매하시나요? 구체적으로 알려주세요."}

        async def node_check_tool(state: GraphState) -> GraphState:
            try:
                eligible = await _llm_is_purchase_tool_available(llm, state["input"], lc_tools)
            except Exception:
                eligible = False
            return {**state, "tool_eligible": eligible}

        async def node_agent(state: GraphState) -> GraphState:
            llm_with_tools = llm.bind_tools(lc_tools)
            res = await llm_with_tools.ainvoke(state["input"])
            # tool 호출이 있다면 첫 번째 툴만 실행하여 결과를 반환
            tool_calls = getattr(res, "tool_calls", []) or []
            if tool_calls:
                call = tool_calls[0]
                tool_name = call.get("name") or call.get("tool")
                tool_args = call.get("args") or {}
                tool_map = {t.name: t for t in lc_tools}
                tool = tool_map.get(tool_name)
                if tool is not None:
                    try:
                        tool_res = await tool.ainvoke(tool_args)
                        return {**state, "output": str(tool_res)}
                    except Exception as e:
                        return {**state, "output": f"툴 실행 중 오류: {e}"}
            # 툴 호출이 없으면 모델 응답 텍스트 사용
            content = getattr(res, "content", None)
            return {**state, "output": content if isinstance(content, str) else str(res)}

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

        def cond_polite(state: GraphState) -> bool:
            return state.get("is_honorific", False)

        workflow.add_conditional_edges(
            "politeness",
            cond_polite,
            {True: "classify_pay_amount", False: "polite_warning"},
        )

        def cond_pay_amount(state: GraphState) -> bool:
            return state.get("intent_pay_amount", False)

        workflow.add_conditional_edges(
            "classify_pay_amount",
            cond_pay_amount,
            {True: "check_tool", False: "ask_product"},
        )

        def cond_tool(state: GraphState) -> bool:
            return state.get("tool_eligible", False)

        workflow.add_conditional_edges(
            "check_tool",
            cond_tool,
            {True: "agent", False: "no_tool"},
        )

        workflow.add_edge("ask_product", END)
        workflow.add_edge("polite_warning", END)
        workflow.add_edge("agent", END)
        workflow.add_edge("no_tool", END)

        graph = workflow.compile()

        final_state = await graph.ainvoke(
            {"input": user_input, "is_honorific": False, "intent_pay_amount": False, "tool_eligible": False, "output": ""}
        )

    # Client는 async context로 관리되므로 여기서 명시적으로 close는 필요 없음
    # (fastmcp.Client는 내부에서 연결을 관리 하며, 도구 호출 후 종료됨)

    return final_state.get("output", "(출력 없음)")


def run_purchase_flow_once_sync(user_input: str, *, mcp_config_path: str | None = None) -> str:
    """Streamlit 등 동기 환경에서 호출할 수 있는 동기 헬퍼."""
    return asyncio.run(run_purchase_flow_once(user_input, mcp_config_path=mcp_config_path))


