"""
Streamlit UI 모듈 (LangGraph + MCP 기반)

SOLID 원칙:
- 단일 책임 원칙(SRP): UI 렌더링과 대화 흐름 호출을 분리
- 의존성 역전 원칙(DIP): 구체 구현 대신 함수 인터페이스(run_purchase_flow_once_sync)에 의존
"""
import os
import sys
import streamlit as st
from pathlib import Path

# 하이픈(-)이 포함된 디렉터리(`mcp-server`)로 인해 패키지 임포트가 불가하므로 런타임에 경로 추가
_CLIENT_DIR = Path(__file__).parents[1] / "mcp-server" / "client"
sys.path.append(str(_CLIENT_DIR))
from purchase_flow import run_purchase_flow_once_sync


def run():
    # 표시 정보
    model_name = os.getenv("LANGGRAPH_MODEL", "gpt-4o-mini")
    st.title("🤖 LangGraph + MCP 챗봇")
    st.caption(f"LangGraph 모델: {model_name}")

    # MCP 설정 경로 표시(선택)
    default_cfg = str(Path(__file__).parents[1] / "mcp-server" / "mcp_servers.json")
    mcp_config_path = os.getenv("MCP_SERVERS_CONFIG", default_cfg)
    with st.expander("MCP 설정 정보", expanded=False):
        st.code(mcp_config_path)

    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_input = st.chat_input("메시지를 입력하세요...")
    if user_input:
        st.session_state["messages"].append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        try:
            bot_response = run_purchase_flow_once_sync(user_input, mcp_config_path=mcp_config_path)
        except Exception as e:
            bot_response = f"❌ 처리 중 오류가 발생했습니다: {e}"

        st.session_state["messages"].append({"role": "assistant", "content": bot_response})
        with st.chat_message("assistant"):
            st.markdown(bot_response)