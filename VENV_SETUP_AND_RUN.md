## Windows CMD(명령 프롬프트) 로컬 실행 가이드 (Python 3.12)

이 문서는 Windows CMD(명령 프롬프트) 환경에서 이 프로젝트를 "최소 설정"으로 빠르게 실행하기 위한 가이드입니다.

### 전제 조건
- Python 3.12.1 설치 완료
- 저장소는 이미 클론된 상태 (`agent-with-mcp` 디렉터리)

---

### 1) 가상환경 생성 및 활성화

```bat
REM 프로젝트 루트로 이동 (예: Desktop\github\agent-with-mcp)
cd C:\Users\yho.roh\Desktop\github\agent-with-mcp

REM 가상환경 생성 (프로젝트 내부 .venv 사용 권장)
python -m venv .venv

REM CMD에서 활성화
.\.venv\Scripts\activate.bat
```

비활성화는 다음 명령으로 가능합니다:
```bat
deactivate
```

---

### 2) 의존성 설치

필요 패키지는 모두 루트 `requirements.txt`에 포함되어 있습니다.

```bat
python -m pip install --upgrade pip
pip install -r requirements.txt
```

앱은 Streamlit UI + LangGraph + MCP(STDIO)로 동작하며, 별도의 MCP 서버를 수동으로 실행할 필요가 없습니다.

---

### 3) 환경 변수(.env) 설정

필수:
```bat
set OPENAI_API_KEY=sk-...your-key...
```

선택:
```bat
REM LangGraph가 사용할 OpenAI 모델 (기본: gpt-4o-mini)
set LANGGRAPH_MODEL=gpt-4o-mini

REM MCP 설정 파일 경로를 바꾸고 싶을 때
set MCP_SERVERS_CONFIG=mcp-server\mcp_servers.json
```

`.env` 파일을 사용할 경우, 루트에 `.env`를 만들고 동일한 키를 넣으면 됩니다.

---

### 4) 실행

Streamlit로 UI를 기동합니다.

```bat
streamlit run main.py
```

브라우저에서 다음 주소로 접속합니다:
```
http://localhost:8501
```

포트가 이미 사용 중이라면 다른 포트를 지정할 수 있습니다:
```bat
streamlit run main.py --server.port 8502
```

---

### 5) 문제 해결

OpenAI 사용 시 키 설정을 다시 확인하세요:
```bat
echo %OPENAI_API_KEY%
```

---

### 6) 자주 발생하는 이슈

- 활성화 경로 오류: `.\.venv\Scripts\activate.bat` 경로 확인
- 패키지 충돌/부족: `pip install --upgrade pip` 후 `pip install -r requirements.txt` 재실행
- Streamlit 포트 충돌: `--server.port` 옵션으로 다른 포트 사용

---

### 요약
1. `.venv` 생성 및 활성화 → `python -m venv .venv` → `.\.venv\Scripts\activate.bat`
2. 의존성 설치 → `pip install -r requirements.txt`
3. `OPENAI_API_KEY` 설정 (+ 선택: `LANGGRAPH_MODEL`)
4. 실행 → `streamlit run main.py` → `http://localhost:8501`


