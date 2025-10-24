## RHEL 9.4 Docker Compose 배포 가이드 (Nginx 포함)

이 문서는 `agent-with-mcp` 프로젝트를 RHEL 9.4 서버에서 Docker Compose와 Nginx 리버스 프록시로 배포하는 방법을 설명합니다.

### 사전 준비
- RHEL 9.4 서버(퍼블릭 IP)
- sudo 권한
- 도메인: `chatbot.leebalso.org` (A 레코드를 서버 공인 IP로 지정)
- 방화벽에서 80 포트 오픈

```bash
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --reload
```

### 1) Docker 및 Compose 설치
```bash
sudo dnf -y install dnf-plugins-core
sudo dnf config-manager --add-repo https://download.docker.com/linux/rhel/docker-ce.repo
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

sudo systemctl enable --now docker
sudo usermod -aG docker $USER
newgrp docker

docker version
docker compose version
```

### 2) 프로젝트 준비 및 환경설정
```bash
cd /opt
sudo git clone https://github.com/sds-team-mw/agent-with-mcp.git
cd agent-with-mcp

# .env 준비 (필수: OPENAI_API_KEY, 선택: LANGGRAPH_MODEL)
cat > .env <<'EOF'
OPENAI_API_KEY=sk-...your-openai-key...
# LANGGRAPH_MODEL=gpt-4o-mini
EOF
```

> 본 가이드는 OpenAI API 키 기반으로 동작합니다.

### 3) Nginx 설정(HTTP)
- 이미 `nginx/nginx.conf`가 포함되어 있으며 `app:8501`으로 프록시합니다.
- WebSocket 업그레이드 헤더 포함(Streamlit 호환).
- `server_name`은 `chatbot.leebalso.org`로 설정되어 있습니다.

### 4) 빌드 및 실행
```bash
docker compose up -d --build
docker compose ps
docker compose logs -f nginx
# 필요 시
docker compose logs -f app
```

접속: 브라우저에서 `http://chatbot.leebalso.org`로 접속합니다.

### 5) 참고(SELinux)
SELinux 활성화 환경에서 로컬 파일 마운트 권한 문제가 있으면 `:Z` 또는 `:z` 마운트 옵션을 고려하세요.

### 7) 운영 명령어
```bash
docker compose up -d
docker compose stop
docker compose restart
docker compose logs -f nginx
docker compose logs -f app
docker compose build --no-cache
docker compose up -d --build
```

### 8) 트러블슈팅
- 502/504: `docker compose logs -f app`로 앱 상태 확인
- 404: Nginx 설정 마운트 경로 확인(`nginx/nginx.conf`)
- 포트 충돌: 호스트 80 점유 확인 후 조정
- OpenAI 오류: `OPENAI_API_KEY` 및 과금 상태 확인
- Streamlit 포트: 프록시 뒤에서는 내부 8501 고정 유지

### 구성 요약
- `Dockerfile`: Streamlit 앱 이미지
- `docker-compose.yml`: `app` + `nginx`
- `nginx/nginx.conf`: 리버스 프록시 설정(WebSocket 포함)
- `.env`: LLM 및 비밀키 설정
