## Windows CMD(명령 프롬프트) 최소 설정 가상환경 실행 가이드 (Python 3.12.1)

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

### 2) 의존성 설치 (최소)

프로젝트 루트의 `requirements.txt`만 설치하면 UI 실행에 필요한 최소 패키지가 준비됩니다.

```bat
python -m pip install --upgrade pip
pip install -r requirements.txt
```

참고: `mcp-server/requirements.txt`는 MCP 서버 실습 시에만 필요합니다. 본 가이드의 최소 실행에는 불필요하므로 생략합니다.

---

### 3) 환경 변수(.env) 설정 (OpenAI + LangSmith)

기본값은 `LLM_PROVIDER=ollama`, `LLM_MODEL=gemma3n:e4b` 이지만, OpenAI와 LangSmith 트레이싱을 사용할 경우 아래 템플릿 사용을 권장합니다.

#### Option A) 템플릿 사용 (권장)
```bat
copy openai_langsmith.env .env
REM 편집기로 .env 열어 다음 값을 채우세요:
REM   - OPENAI_API_KEY=<<입력필요>>
REM   - LANGCHAIN_API_KEY=<<입력필요>>
REM   - LANGCHAIN_PROJECT=<<입력필요>>
```

템플릿에는 다음이 포함됩니다:
- LLM 설정: `LLM_PROVIDER=openai`, `LLM_MODEL=gpt-4`
- OpenAI: `OPENAI_API_KEY`
- LangSmith 트레이싱: `LANGSMITH_TRACING=true`, `LANGCHAIN_ENDPOINT=https://api.smith.langchain.com`, `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT`

LangSmith는 `.env`를 통해 자동으로 활성화되며(`main.py`에서 `load_dotenv()` 호출), 별도 코드 수정이 필요 없습니다.

#### Option B) 기존 샘플 복사
```bat
copy example.env .env
REM 필요 시 OpenAI/LangSmith 관련 값을 직접 수정
```

#### (대안) 환경변수 직접 설정 (세션 한정)
```bat
set OPENAI_API_KEY=sk-...your-key...
set LLM_PROVIDER=openai
set LLM_MODEL=gpt-4

REM LangSmith (선택)
set LANGSMITH_TRACING=true
set LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
set LANGCHAIN_API_KEY=sk-langsmith-...  
set LANGCHAIN_PROJECT=my-project-name
```

#### 빠른 확인
```bat
echo %OPENAI_API_KEY%
echo %LANGCHAIN_API_KEY%
echo %LANGCHAIN_PROJECT%
```

#### Ollama(기본) 사용 시 (참고)
```bat
REM Ollama 설치: https://ollama.ai/download
REM 모델 다운로드 예시
ollama pull gemma3n:e4b
REM 또는
ollama pull llama2
```

---

### 4) 실행 방법

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

### 5) (옵션) 설치 확인 및 기본 점검

LLM 호출 없이 구조만 확인하려면 아래 스크립트를 실행해 볼 수 있습니다.
```bat
python test_llm.py
```

Ollama 사용 시 연결 문제가 있으면 다음을 점검하세요:
```bat
REM 서버 실행 확인
ollama serve
REM 모델 설치 여부 확인
ollama list
ollama pull gemma3n:e4b
```

OpenAI 사용 시에는 키 설정을 다시 확인하세요:
```bat
echo %OPENAI_API_KEY%
```

---

### 6) 자주 발생하는 이슈 빠른 해결

- 활성화 경로 오류: `.\.venv\Scripts\activate.bat` 경로 확인
- 패키지 충돌/부족: `pip install --upgrade pip` 후 `pip install -r requirements.txt` 재실행
- Streamlit 포트 충돌: `--server.port` 옵션으로 다른 포트 사용

---

### 요약
1. `.venv` 생성 및 활성화 → `python -m venv .venv` → `.\.venv\Scripts\activate.bat`
2. 의존성 설치 → `pip install -r requirements.txt`
3. (선택) `.env` 또는 환경변수로 LLM 제공자 설정
4. 실행 → `streamlit run main.py` → 브라우저에서 `http://localhost:8501`


