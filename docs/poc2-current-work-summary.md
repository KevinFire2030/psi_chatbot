# GSCM PSI PoC2 현재 작업 정리

작성일: 2026-06-02  
대상 서비스: `GSCM PSI PoC2 — Hermes Webhook Chat UI`  
공개 URL: `https://psi.possible-connect.com/`  
로컬 URL: `http://127.0.0.1:8766/`

## 1. 목적

GSCM PSI Excel 데이터를 DuckDB long-form 데이터마트로 변환한 뒤, 사용자가 자연어로 지역/법인/모델/월/분기 별 PSI 지표를 조회하는 PoC 데모를 구축했다.

주요 조회 대상 지표는 다음과 같다.

- FP 매출
- DP
- RTF
- Short/숏
- Sell-Out/셀아웃
- WOS
- 유통재고
- 법인/지역/모델 단위 비교 및 전년비 분석

사용자 답변 포맷 기준:

- GSCM PSI 답변 시작 문구: `W23_Pre plan 기준`
- 금액 단위: 백만불
- 수량 단위: 천대

## 2. 현재 아키텍처

```text
Browser
  -> https://psi.possible-connect.com/
  -> Cloudflare
  -> Windows Caddy
  -> localhost:8766
  -> FastAPI PoC2 app
  -> Hermes webhook route: gscm-psi-chat
  -> Hermes Agent
  -> DuckDB data/psi.duckdb 조회
  -> 최종 답변을 PoC2 UI로 반환
```

핵심 파일:

```text
PoC2/app.py
PoC2/static/index.html
PoC2/static/style.css
PoC2/static/app.js
PoC2/README.md
```

데이터마트:

```text
data/psi.duckdb
psi_long table
```

PoC2 서버 실행 명령:

```bash
cd /mnt/e/ax/PRJs/psi_chatbot
uv run uvicorn PoC2.app:app --host 0.0.0.0 --port 8766
```

현재 서비스는 `8766` 포트에서 실행되며, Caddy가 `psi.possible-connect.com` 요청을 이 포트로 reverse proxy한다.

## 3. FastAPI / Hermes webhook 동작

`PoC2/app.py`는 브라우저 입력을 `/api/chat`에서 받아 Hermes webhook으로 전달한다.

주요 동작:

1. 브라우저가 `/api/chat`에 질문 전송
2. PoC2 backend가 `request_id` 생성
3. Hermes webhook route `gscm-psi-chat`으로 payload 전송
4. Hermes webhook은 비동기로 agent session 생성
5. PoC2 backend가 Hermes state DB를 polling
6. 해당 `request_id`가 포함된 최종 assistant 메시지를 찾아 UI에 반환

헬스체크:

```http
GET /health
```

정상 예시:

```json
{
  "status": "ok",
  "webhook_url": "http://127.0.0.1:8644/webhooks/gscm-psi-chat",
  "webhook_route": "gscm-psi-chat",
  "has_webhook_secret": true,
  "state_db_exists": true
}
```

## 4. Caddy / 도메인 연결

Windows Caddy 설정 파일:

```text
C:\caddy\Caddyfile
```

추가된 라우팅:

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

검증한 항목:

- Caddy 설정 문법 검증: `Valid configuration`
- Caddy reload/restart 완료
- `Host: psi.possible-connect.com` 로컬 라우팅 검증 성공
- `https://psi.possible-connect.com/` HTML/CSS 응답 검증 성공

주의:

- Caddyfile의 `header_up X-Forwarded-*`는 Caddy 경고상 기본 동작과 중복이라 추후 정리 가능하다.
- 현재 HTTPS는 Cloudflare가 담당하고, Caddy origin 쪽은 HTTP reverse proxy 구조다.

## 5. UI 변경 사항

상단 hero 영역을 기존 단순 텍스트에서 2단 카드 레이아웃으로 변경했다.

### 왼쪽 카드

표시 내용:

```text
● PSI Natural Language PoC
GSCM PSI Chatbot
GSCM PSI Excel 데이터를 DuckDB long-form 데이터마트로 변환한 뒤,
자연어 질문으로 지역/법인/모델/월/분기 別 FP 매출, DP, RTF, 숏,
셀아웃, WOS, 유통재고를 조회하는 PoC 데모
```

데이터마트 지표 카드:

```text
W23_pre    기준 플랜
2.2M+      long-form rows
937        source columns
```

### 오른쪽 카드

예시 질문 5개:

```text
3분기 Short가 가장 큰 지역 Top 5 보여줘
9월 WOS가 13 이상인 법인을 알려줘
3분기 FP 금액기준 전년비 감소가 가징 큰 법인 탑5 알려줘
SEG 3분기 PSI 입력 현황 분석해서 입력이 덜됐거나 추가로 확인이 필요한 부분이 있는지 점검해줘
2분기 SEROM s26F 셀아웃 WOS 알려줘
```

참고:

- `가징`은 사용자 요청 문구 그대로 반영했다.
- 로컬 8766 화면과 Caddy 경유 화면 모두 새 예시 질문 반영을 확인했다.

## 6. Cloudflare CSS 캐시 문제와 해결

증상:

- `http://127.0.0.1:8766/`에서는 최신 UI가 정상 표시됨
- `https://psi.possible-connect.com/`에서는 HTML은 최신인데 스타일이 깨져 보임

진단 결과:

- 공개 HTTPS HTML은 최신 `top-grid`, `hero-panel`, `example-list`를 포함하고 있었다.
- 하지만 `/static/style.css`는 Cloudflare 캐시에서 이전 CSS가 내려왔다.
- 응답 헤더에서 확인된 단서:

```text
cf-cache-status: HIT
cache-control: max-age=14400
content-length: 3199  # 이전 CSS
```

해결:

`index.html`의 CSS 링크에 cache-busting query를 추가했다.

```html
<link rel="stylesheet" href="/static/style.css?v=20260601-psi-ui" />
```

수정 후 HTTPS에서 새 CSS 수신을 확인했다.

```text
/static/style.css?v=20260601-psi-ui 포함: True
.top-grid 포함: True
.hero-panel 포함: True
.example-list 포함: True
.stat-card 포함: True
```

## 7. 검증한 대표 자연어 질의와 데이터 해석

### 7.1 3분기 사업부 FP 금액/수량 및 전년비

조회 기준:

```text
period = 3분기
business_unit = 사업부
region_entity = Total
psi_model_26 = Total
금액 = metric 매출 / sub_header FP (매출)
수량 = metric 물량 / sub_header RTF (FP)
전년 금액 = metric 매출전년 / sub_header 25년 (매출)
전년 수량 = metric 물량전년 / sub_header 25년 (셀인)
```

확인 결과:

- FP 매출: 23,349.3 백만불
- 전년 매출: 24,219.0 백만불
- 매출 차이: -869.7 백만불
- 매출 전년비: 96.4%
- RTF(FP) 수량: 56,739.5 천대
- 전년 셀인: 61,402.4 천대
- 수량 차이: -4,662.9 천대
- 수량 전년비: 92.4%

### 7.2 3분기 FP 금액 기준 전년비 감소 Top 5 법인

조회 기준:

```text
period = 3분기
metric = 매출 / sub_header FP (매출)
prior year = 매출전년 / sub_header 25년 (매출)
법인 row = region_entity != Total and psi_model_26 = Total
정렬 = FP 금액 - 전년 금액 ASC
```

Top 5:

1. SEA: -1,346.2 백만불, 전년비 72.0%
2. North America: -1,105.6 백만불, 전년비 78.9%
3. Korea: -340.3 백만불, 전년비 87.4%
4. SEUK: -155.8 백만불, 전년비 82.4%
5. Europe: -135.8 백만불, 전년비 97.5%

### 7.3 2분기 SEROM S26F Sell-Out / WOS

조회 기준:

```text
period = 2분기
region_entity = SEROM
model_code = S26F
metrics = Sell-Out, WOS(EDI+FOTA), T.WOS, WOS(F4)
```

확인 결과:

- Sell-Out: 64.1 천대
- WOS(EDI+FOTA): 7.5주
- T.WOS: 7.2주
- WOS(F4): 6.4주
- 전년 Sell-Out: 67.9 천대
- 전년 대비 수량 차이: -3.8 천대
- 전년비: 94.4%
- W12 Sell-Out: 71.5 천대
- W12 대비: -7.3 천대

## 8. 최근 주요 커밋

```text
57f96b1 fix: bust cached PSI chatbot stylesheet
61e98b2 feat: update PSI chatbot example prompts
58fac05 feat: refresh PSI chatbot landing UI
f9243a2 docs: sync GSCM PSI conversation transcript
fba5551 fix: wait for webhook agent answer
```

## 9. 운영 확인 명령

PoC2 서버 상태 확인:

```bash
ss -ltnp | grep ':8766'
curl -sS http://127.0.0.1:8766/health
```

로컬 HTML 확인:

```bash
curl -sS http://127.0.0.1:8766/ -o /tmp/poc2.html
```

공개 HTTPS HTML/CSS 확인:

```bash
curl -sS https://psi.possible-connect.com/ -o /tmp/psi_https.html
curl -sS 'https://psi.possible-connect.com/static/style.css?v=20260601-psi-ui' -o /tmp/psi_style.css
```

Caddy 설정 검증:

```powershell
cd C:\caddy
.\caddy.exe validate --config Caddyfile
.\caddy.exe reload --config Caddyfile
```

## 10. 남은 개선 아이디어 메모

사용자가 메모로 남긴 후속 고도화 후보:

- n8n 스타일 인증 페이지
- 담당자에게 메일 보내기 기능
- 앱 형태로 패키징
- UI 기능 안내 고도화
  - 기준 플랜
  - 조회 범위
  - 기능: 메일 보내기, 보고서, 인사이트 등
- 특정 폴더에 Excel을 넣으면 자동으로 DuckDB 업데이트
- cron job 기반 자동 갱신
- Codex CLI 활용

## 11. 현재 상태 요약

- PoC2 FastAPI 앱 구현 및 실행 확인 완료
- Hermes webhook 기반 브라우저 채팅 UI 구현 완료
- PSI DuckDB 실제 조회 기반 답변 패턴 검증 완료
- `psi.possible-connect.com` Caddy 라우팅 완료
- Cloudflare CSS 캐시 문제 해결 완료
- 최신 UI/예시 질문 반영 및 GitHub push 완료
