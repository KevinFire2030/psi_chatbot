# GSCM PSI PoC2 — FastAPI → Hermes Webhook Chat UI

PoC2는 간단한 웹 채팅 UI에서 입력한 PSI 자연어 질문을 FastAPI가 Hermes Webhook으로 전달하고, Hermes Agent가 처리한 최종 답변을 다시 UI에 출력하는 데모입니다.

```text
Browser chat UI
  -> FastAPI /api/chat
  -> Hermes Webhook /webhooks/gscm-psi-chat
  -> Hermes Agent tool execution
  -> Hermes state DB polling
  -> Browser chat UI
```

## 실행

프로젝트 루트에서:

```bash
cd /mnt/e/ax/PRJs/psi_chatbot
uv run uvicorn PoC2.app:app --host 0.0.0.0 --port 8766
```

브라우저:

```text
http://localhost:8766/
```

## Hermes Webhook 구독 생성

한 번만 실행하면 됩니다.

```bash
hermes webhook subscribe gscm-psi-chat \
  --description "GSCM PSI 자연어 질문을 Hermes Agent가 처리해 답변하는 PoC2 웹훅" \
  --deliver log \
  --prompt "[gscm-psi-chat] request_id={request_id}\n\n당신은 GSCM PSI 데이터 자연어 조회 Agent입니다.\n사용자 질문: {question}\n\n반드시 /mnt/e/ax/PRJs/psi_chatbot 프로젝트의 data/psi.duckdb DuckDB와 psi_long 테이블을 실제 조회해서 답하세요.\n필요하면 terminal에서 uv run python + duckdb를 사용하세요.\n최종 답변은 한국어로, 데모 화면에 바로 보여줄 수 있게 간결하게 작성하세요.\n툴 실행 로그나 내부 설명은 최종 답변에 포함하지 마세요."
```

PoC2 backend는 로컬 데모 편의를 위해 `~/.hermes/webhook_subscriptions.json`에서 해당 route의 secret을 자동 탐색합니다. 운영/배포 환경에서는 아래처럼 명시적으로 환경변수를 설정하세요.

```bash
export HERMES_WEBHOOK_URL=http://127.0.0.1:8644/webhooks/gscm-psi-chat
export HERMES_WEBHOOK_SECRET=... # Git에 커밋 금지
```

## 데모 질문

- `유럽 2분기 플래그십 숏현황 알려줘`
- `북미 2분기 숏이 몇대야?`
- `유럽 법인별 2분기 숏 현황 알려줘`
- `2분기 사업부 FP(매출) 알려줘`

## API

### `POST /api/chat`

Request:

```json
{
  "message": "유럽 2분기 플래그십 숏현황 알려줘",
  "timeout_seconds": 180
}
```

Response:

```json
{
  "request_id": "poc2-...",
  "delivery_id": "poc2-...",
  "webhook_status": {"status": "accepted"},
  "answer": "유럽 2분기 플래그십 Short 현황입니다...",
  "elapsed_seconds": 12.3,
  "session_id": "20260601_..."
}
```

## 구현 메모

Hermes Webhook은 비동기로 `202 accepted`를 반환합니다. 따라서 PoC2 FastAPI는 payload에 `request_id`를 넣고, Hermes state DB에서 해당 `request_id`가 포함된 webhook session을 찾아 최종 assistant 메시지를 polling합니다.

LLM provider rate limit 등으로 Hermes 최종 응답이 시간 내 저장되지 않으면, 데모가 멈추지 않도록 기본적으로 알려진 PSI 질문군은 DuckDB를 직접 조회하는 deterministic fallback을 사용합니다. 이 경우 API 응답의 `answer_source`가 `local_deterministic_fallback_after_webhook`으로 표시됩니다. 끄려면:

```bash
export POC2_ENABLE_LOCAL_FALLBACK=false
```
