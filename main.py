"""
메인 애플리케이션 진입점 (Streamlit UI 실행)

LangGraph + MCP 기반의 챗봇 UI를 실행합니다.
"""
from dotenv import load_dotenv
from ui.streamlit_ui import run

load_dotenv()  # .env 파일에서 환경 변수 로드

if __name__ == "__main__":
    run() 