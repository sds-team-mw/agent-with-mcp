# check_key_langchain_env.py
import os
import sys
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# .env 파일 로드
load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    print("ERROR: .env 파일에 OPENAI_API_KEY 가 없습니다 ❌")
    sys.exit(2)

try:
    # 간단하고 빠른 모델 선택
    llm = ChatOpenAI(
        api_key=API_KEY,
        model="gpt-4o-mini",
        temperature=0,
    )

    # 실제 호출 (1토큰 수준)
    result = llm.invoke("ping")

    print("✅ OPENAI_API_KEY is VALID")
    print("Response:", result.content)

except Exception as e:
    if "401" in str(e) or "invalid_api_key" in str(e).lower():
        print("❌ OPENAI_API_KEY is INVALID (401 Unauthorized)")
    else:
        print(f"⚠️  Request failed: {type(e).__name__} - {e}")
