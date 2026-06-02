# GSCM PSI Chatbot PoC2

GSCM PSI Excel 데이터를 DuckDB long-form 데이터마트로 변환하고, 사용자가 웹 채팅 UI에서 자연어로 질문하면 Hermes Agent가 실제 PSI 데이터를 조회해 답변하는 PoC입니다.

현재 기준 서비스는 **PoC2 — FastAPI → Hermes Webhook Chat UI**입니다.

- 공개 URL: `https://psi.possible-connect.com/`
- 로컬 URL: `http://127.0.0.1:8766/`
- Android WebView APK: `artifacts/android/gscm-psi-chatbot-webview-debug.apk`

## 현재 구현 범위

1. `PoC1/sample_psi/sample_psi.xlsx` 분석 및 문서화
2. Excel 리포트형 wide data → long-form DuckDB 데이터마트 변환
3. PSI 조회용 DuckDB `psi_long` 테이블 생성
4. PoC2 웹 채팅 UI 제공
5. `/api/chat`에서 Hermes webhook route `gscm-psi-chat` 호출
6. Hermes Agent 최종 응답을 state DB polling으로 UI에 반환
7. Android WebView APK wrapper 제공

기존 `PoC1.app.main`의 deterministic FastAPI `/query` API와 관련 스크립트/문서는 `PoC1/` 아래로 이동했습니다. 현재 데모/운영 기준은 `PoC2.app:app`입니다.

## 아키텍처

```text
Browser 또는 Android WebView
  -> https://psi.possible-connect.com/
  -> Cloudflare
  -> Windows Caddy
  -> localhost:8766
  -> FastAPI PoC2 app
  -> POST /api/chat
  -> Hermes webhook route: gscm-psi-chat
  -> Hermes Agent
  -> DuckDB data/psi.duckdb / psi_long 실제 조회
  -> Hermes 최종 답변을 PoC2 UI로 반환
```

핵심 파일:

```text
PoC2/app.py                    # FastAPI backend, Hermes webhook 호출, state DB polling
PoC2/static/index.html         # PoC2 채팅 UI
PoC2/static/app.js             # /api/chat 호출 및 응답 렌더링
PoC2/static/style.css          # UI styling
PoC2/README.md                 # PoC2 세부 실행/웹훅 메모
PoC1/scripts/preprocess_psi.py # PoC1 Excel -> DuckDB 전처리
PoC1/scripts/query_psi.py      # PoC1 DuckDB 직접 질의용 CLI
PoC1/app/                      # PoC1 deterministic API/Query planner 코드
PoC1/docs/                     # PoC1 분석/전처리 문서
PoC1/tests/                    # PoC1 테스트
PoC1/sample_psi/               # PoC1 샘플 Excel
android/psi-webview/           # Android WebView wrapper 프로젝트
artifacts/android/             # 생성된 APK 산출물
```

## 데이터마트 생성

```bash
uv run python3 PoC1/scripts/preprocess_psi.py \
  --input PoC1/sample_psi/sample_psi.xlsx \
  --output PoC1/data/psi.duckdb
```

생성 결과 예시:

```text
Created PoC1/data/psi.duckdb
sheet_name=4)법인·모델별 현황 (분기_월)
source_rows=3051
source_columns=937
metric_columns=854
long_rows=2217562
```

`PoC1/data/psi.duckdb`는 용량이 커서 GitHub에는 커밋하지 않습니다. 필요 시 위 명령으로 재생성합니다. 현재 PoC2 webhook 데모는 운영 편의를 위해 기존 runtime DB인 `data/psi.duckdb`를 참조합니다.

## PoC2 서버 실행

프로젝트 루트에서 실행합니다.

```bash
cd /mnt/e/ax/PRJs/psi_chatbot
uv run uvicorn PoC2.app:app --host 0.0.0.0 --port 8766
```

브라우저:

```text
http://127.0.0.1:8766/
```

Health check:

```bash
curl http://127.0.0.1:8766/health
```

정상 응답 예시:

```json
{
  "status": "ok",
  "webhook_url": "http://127.0.0.1:8644/webhooks/gscm-psi-chat",
  "webhook_route": "gscm-psi-chat",
  "has_webhook_secret": true,
  "state_db_exists": true
}
```

## Hermes Webhook 연동

PoC2 backend는 기본적으로 다음 Hermes webhook으로 질문을 전달합니다.

```text
http://127.0.0.1:8644/webhooks/gscm-psi-chat
```

로컬 데모에서는 `~/.hermes/webhook_subscriptions.json`에서 route secret을 자동 탐색합니다. 운영/분리 환경에서는 아래 환경변수를 명시합니다.

```bash
export HERMES_WEBHOOK_URL=http://127.0.0.1:8644/webhooks/gscm-psi-chat
export HERMES_WEBHOOK_SECRET=... # Git에 커밋 금지
export HERMES_STATE_DB=$HOME/.hermes/state.db
```

웹훅 구독이 없으면 한 번 생성합니다.

```bash
hermes webhook subscribe gscm-psi-chat \
  --description "GSCM PSI 자연어 질문을 Hermes Agent가 처리해 답변하는 PoC2 웹훅" \
  --deliver log \
  --prompt "[gscm-psi-chat] request_id={request_id}\n\n당신은 GSCM PSI 데이터 자연어 조회 Agent입니다.\n사용자 질문: {question}\n\n반드시 /mnt/e/ax/PRJs/psi_chatbot 프로젝트의 data/psi.duckdb DuckDB와 psi_long 테이블을 실제 조회해서 답하세요.\n최종 답변은 한국어로, 데모 화면에 바로 보여줄 수 있게 간결하게 작성하세요.\n답변 첫 줄에는 W23_Pre plan 기준을 포함하세요.\n금액은 백만불, 수량은 천대 기준으로 표시하세요.\n툴 실행 로그나 내부 설명은 최종 답변에 포함하지 마세요."
```

## API

### `POST /api/chat`

Request:

```json
{
  "message": "3분기 FP 금액기준 전년비 감소가 가장 큰 법인 탑5 알려줘",
  "timeout_seconds": 1800
}
```

Response:

```json
{
  "request_id": "poc2-...",
  "delivery_id": "poc2-...",
  "webhook_status": {"status": "accepted"},
  "answer": "W23_Pre plan 기준 ...",
  "elapsed_seconds": 12.3,
  "session_id": "20260602_...",
  "answer_source": "hermes_webhook"
}
```

PoC2는 로컬 deterministic DuckDB fallback을 사용하지 않습니다. 브라우저는 Hermes webhook agent의 최종 응답을 기다립니다.

## 예시 질문

UI에 포함된 예시 질문:

- `3분기 Short가 가장 큰 지역 Top 5 보여줘`
- `9월 WOS가 13 이상인 법인을 알려줘`
- `3분기 FP 금액기준 전년비 감소가 가징 큰 법인 탑5 알려줘`
- `SEG 3분기 PSI 입력 현황 분석해서 입력이 덜됐거나 추가로 확인이 필요한 부분이 있는지 점검해줘`
- `2분기 SEROM s26F 셀아웃 WOS 알려줘`

답변 포맷 기준:

- 기준 문구: `W23_Pre plan 기준`
- 금액 단위: 백만불
- 수량 단위: 천대

## 공개 도메인 / Caddy

Windows Caddy 설정 파일:

```text
C:\caddy\Caddyfile
```

현재 라우팅:

```caddy
# ===== PSI chatbot PoC2 web =====
http://psi.possible-connect.com {
    reverse_proxy localhost:8766 {
        header_up X-Forwarded-Proto {scheme}
        header_up X-Forwarded-Host {host}
        header_up X-Forwarded-For {remote}
    }
}
```

서비스가 502를 반환하면 대부분 PoC2 uvicorn server가 `8766`에서 떠 있지 않은 상태입니다. 아래 순서로 확인합니다.

```bash
ss -ltnp | grep ':8766'
curl http://127.0.0.1:8766/health
curl https://psi.possible-connect.com/
```

## Android WebView APK

Android wrapper는 `https://psi.possible-connect.com/`를 WebView로 여는 앱입니다.

프로젝트:

```text
android/psi-webview/
```

빌드:

```bash
cd android/psi-webview
./gradlew assembleDebug
```

APK 산출물:

```text
android/psi-webview/app/build/outputs/apk/debug/app-debug.apk
artifacts/android/gscm-psi-chatbot-webview-debug.apk
```

현재 APK는 debug signing APK입니다. 실제 배포용은 release keystore로 별도 서명해야 합니다.

## 초기 PoC CLI / deterministic API

초기 DuckDB 직접 질의 CLI는 계속 사용할 수 있습니다.

```bash
uv run python3 PoC1/scripts/query_psi.py \
  '3분기 Short가 가장 큰 지역 Top 5 보여줘' \
  --db PoC1/data/psi.duckdb
```

초기 FastAPI deterministic API를 실행하려면:

```bash
uv run uvicorn PoC1.app.main:app --host 127.0.0.1 --port 8765
```

단, 현재 웹 데모와 Android APK는 `PoC2.app:app` / port `8766` 기준입니다.

## 테스트

```bash
uv run --extra test python3 -m unittest discover -s PoC1/tests -v
uv run --extra test python3 -m unittest discover -s tests -v
```

현재 테스트 범위:

- Excel column address 변환
- PSI metric header parsing
- 중복 metric key disambiguation
- 한국어 자연어 query intent parsing
- DuckDB query service
- 초기 FastAPI `/query` endpoint
- 초기 FastAPI 루트(`/`) 앱 UI HTML 서빙
- Query planner의 SQL/params/explanation 생성
- 기간 비교형 모델별 delta 조회
- PoC2 webhook signature 생성
- PoC2 Hermes state DB polling
- PoC2에서 local deterministic fallback이 제거되어 있는지 검증

## 문서

- `PoC1/docs/sample_psi_analysis.md`: 샘플 PSI Excel 분석 결과
- `PoC1/docs/preprocessing_pipeline.md`: 전처리 파이프라인 및 DuckDB schema 설명
- `docs/poc2-current-work-summary.md`: PoC2 현재 아키텍처/운영/검증 정리
- `PoC2/README.md`: PoC2 backend/webhook 상세 메모
- `android/psi-webview/README.md`: Android WebView APK 빌드 메모

## 다음 단계 후보

1. PoC2 uvicorn을 Windows/WSL persistent service로 등록해 재부팅/세션 종료 후에도 자동 기동
2. Hermes webhook 응답 상태/실패 원인을 UI에 더 명확히 표시
3. Cloudflare/Caddy 캐시 정책 정리
4. Android release signing 및 설치 링크 배포 방식 정리
5. Query planner를 완전한 LLM+tool 기반 질의 라우팅으로 고도화
6. UI에 chart/table rendering, 다운로드, 질의 히스토리 추가
