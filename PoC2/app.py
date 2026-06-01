"""PoC2 chat UI backend: browser chat -> FastAPI -> Hermes webhook -> UI.

This backend intentionally calls the Hermes webhook adapter instead of querying
PSI data directly. Hermes executes the actual agent run asynchronously, so the
backend polls the Hermes session DB for the final assistant message matching the
request id.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import sqlite3
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

import duckdb
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent
STATIC_DIR = APP_DIR / "static"

DEFAULT_HERMES_HOME = Path.home() / ".hermes"
DEFAULT_WEBHOOK_URL = "http://127.0.0.1:8644/webhooks/gscm-psi-chat"
DEFAULT_ROUTE = "gscm-psi-chat"
DEFAULT_TIMEOUT_SECONDS = 180
POLL_INTERVAL_SECONDS = 1.5


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    timeout_seconds: int = Field(default=DEFAULT_TIMEOUT_SECONDS, ge=10, le=300)


class ChatResponse(BaseModel):
    request_id: str
    delivery_id: str
    webhook_status: dict[str, Any]
    answer: str
    elapsed_seconds: float
    session_id: str | None = None
    answer_source: str = "hermes_webhook"


app = FastAPI(title="GSCM PSI PoC2 Hermes Webhook Chat", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def hermes_home() -> Path:
    return Path(os.getenv("HERMES_HOME", str(DEFAULT_HERMES_HOME))).expanduser()


def state_db_path() -> Path:
    return Path(os.getenv("HERMES_STATE_DB", str(hermes_home() / "state.db"))).expanduser()


def webhook_url() -> str:
    return os.getenv("HERMES_WEBHOOK_URL", DEFAULT_WEBHOOK_URL)


def webhook_route_from_url(url: str) -> str:
    return url.rstrip("/").split("/")[-1] or DEFAULT_ROUTE


def discover_webhook_secret(route: str) -> str | None:
    """Discover the local Hermes dynamic subscription secret for dev/demo use.

    This avoids committing secrets. In production, set HERMES_WEBHOOK_SECRET.
    """

    env_secret = os.getenv("HERMES_WEBHOOK_SECRET")
    if env_secret:
        return env_secret

    subs_path = Path(os.getenv("HERMES_WEBHOOK_SUBSCRIPTIONS", str(hermes_home() / "webhook_subscriptions.json"))).expanduser()
    if not subs_path.exists():
        return None
    try:
        data = json.loads(subs_path.read_text(encoding="utf-8"))
        route_config = data.get(route, {}) if isinstance(data, dict) else {}
        secret = route_config.get("secret")
        if isinstance(secret, str) and secret:
            return secret
    except Exception:
        return None
    return None


def sign_body(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def post_to_hermes_webhook(message: str, request_id: str, delivery_id: str) -> dict[str, Any]:
    url = webhook_url()
    route = webhook_route_from_url(url)
    secret = discover_webhook_secret(route)
    if not secret:
        raise HTTPException(
            status_code=500,
            detail=(
                "Hermes webhook secret not configured. Set HERMES_WEBHOOK_SECRET "
                f"or create local route '{route}' with hermes webhook subscribe."
            ),
        )

    payload = {
        "event_type": "psi_chat_query",
        "request_id": request_id,
        "question": message,
        "source": "PoC2 FastAPI chat UI",
    }
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "X-Request-ID": delivery_id,
        "X-Webhook-Signature": sign_body(body, secret),
    }
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            text = res.read().decode("utf-8")
            return json.loads(text) if text else {"status": res.status}
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(status_code=502, detail=f"Hermes webhook HTTP {exc.code}: {error_body}") from exc
    except urllib.error.URLError as exc:
        raise HTTPException(status_code=502, detail=f"Cannot reach Hermes webhook at {url}: {exc}") from exc


def find_session_for_request(conn: sqlite3.Connection, request_id: str) -> str | None:
    row = conn.execute(
        """
        SELECT m.session_id
        FROM messages m
        JOIN sessions s ON s.id = m.session_id
        WHERE s.source = 'webhook'
          AND m.role = 'user'
          AND m.content LIKE ?
        ORDER BY m.timestamp DESC
        LIMIT 1
        """,
        (f"%{request_id}%",),
    ).fetchone()
    return str(row[0]) if row else None


def latest_final_assistant_message(conn: sqlite3.Connection, session_id: str) -> str | None:
    rows = conn.execute(
        """
        SELECT role, content, tool_calls
        FROM messages
        WHERE session_id = ?
        ORDER BY id ASC
        """,
        (session_id,),
    ).fetchall()
    final: str | None = None
    for role, content, tool_calls in rows:
        # Tool-calling assistant placeholders have empty content and non-empty tool calls.
        if role == "assistant" and content and not tool_calls:
            final = str(content)
    return final


async def wait_for_hermes_answer(request_id: str, timeout_seconds: int) -> tuple[str, str | None, str]:
    db_path = state_db_path()
    deadline = time.monotonic() + timeout_seconds
    last_session_id: str | None = None

    while time.monotonic() < deadline:
        if db_path.exists():
            try:
                conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=5)
                try:
                    session_id = find_session_for_request(conn, request_id)
                    if session_id:
                        last_session_id = session_id
                        answer = latest_final_assistant_message(conn, session_id)
                        if answer:
                            return answer, session_id, "hermes_webhook"
                finally:
                    conn.close()
            except sqlite3.Error:
                # Gateway may be writing; retry shortly.
                pass
        await asyncio.sleep(POLL_INTERVAL_SECONDS)

    raise TimeoutError(
        "Hermes accepted the webhook but no final assistant response was found "
        f"within {timeout_seconds}s. request_id={request_id}, session_id={last_session_id}"
    )


def local_fallback_enabled() -> bool:
    return os.getenv("POC2_ENABLE_LOCAL_FALLBACK", "true").strip().lower() in {"1", "true", "yes", "on"}


def fallback_after_seconds(timeout_seconds: int) -> int:
    configured = int(os.getenv("POC2_FALLBACK_AFTER_SECONDS", "45"))
    return max(5, min(timeout_seconds, configured))


def psi_db_path() -> Path:
    return Path(os.getenv("PSI_DUCKDB_PATH", str(PROJECT_ROOT / "data" / "psi.duckdb"))).expanduser()


def fmt_num(value: float | int) -> str:
    return f"{int(value):,}"


def deterministic_local_answer(question: str) -> str | None:
    """Small deterministic fallback for demo questions when Hermes is rate-limited.

    The primary path remains Hermes webhook. This fallback keeps the visual demo
    usable if the LLM provider returns 429 during a customer-facing rehearsal.
    """

    db = psi_db_path()
    if not db.exists():
        return None

    q = question.replace(" ", "").lower()
    con = duckdb.connect(str(db), read_only=True)
    try:
        if "유럽" in q and "플래그십" in q and ("숏" in q or "short" in q):
            total = con.execute(
                """
                SELECT value
                FROM psi_long
                WHERE period='2분기' AND metric='Short' AND comparison=''
                  AND region_entity='Europe' AND psi_model_26='Flagship'
                """
            ).fetchone()[0]
            subs = con.execute(
                """
                SELECT region_entity, CAST(value AS BIGINT) AS short_value
                FROM psi_long
                WHERE period='2분기' AND metric='Short' AND comparison=''
                  AND psi_model_26='Flagship'
                  AND excel_row_number BETWEEN 245 AND 937
                ORDER BY value DESC
                """
            ).fetchall()
            model_rows = con.execute(
                """
                SELECT psi_model_26, model_code, CAST(value AS BIGINT) AS short_value
                FROM psi_long
                WHERE period='2분기' AND metric='Short' AND comparison=''
                  AND region_entity='Europe'
                  AND excel_row_number BETWEEN 202 AND 225
                  AND value <> 0
                ORDER BY excel_row_number
                """
            ).fetchall()
            lines = [
                "유럽 2분기 플래그십 Short 현황입니다.",
                "",
                "유럽 전체",
                f"- Europe / Flagship Short: {fmt_num(total)}대",
                "",
                "법인별 현황 — Short 높은 순",
            ]
            lines.extend(f"{i}. {entity}: {fmt_num(value)}대" for i, (entity, value) in enumerate(subs, 1))
            lines.extend(["", f"법인별 합계도 {fmt_num(sum(v for _, v in subs))}대로 Europe Flagship Total과 일치합니다."])
            lines.extend(["", "유럽 전체 기준 주요 플래그십 모델군"])
            for model, code, value in model_rows:
                label = f"{model}" + (f" / {code}" if code else "")
                lines.append(f"- {label}: {fmt_num(value)}대")
            return "\n".join(lines)

        if "북미" in q and ("숏" in q or "short" in q):
            value = con.execute(
                """
                SELECT value FROM psi_long
                WHERE period='2분기' AND metric='Short' AND comparison=''
                  AND psi_model_26='Total' AND region_entity='North America'
                """
            ).fetchone()[0]
            return f"북미의 2분기 Short는 {fmt_num(value)}대입니다."

        if "유럽" in q and "법인" in q and ("숏" in q or "short" in q):
            rows = con.execute(
                """
                SELECT region_entity, CAST(value AS BIGINT) AS short_value
                FROM psi_long
                WHERE period='2분기' AND metric='Short' AND comparison=''
                  AND psi_model_26='Total'
                  AND excel_row_number BETWEEN 245 AND 937
                ORDER BY value DESC
                """
            ).fetchall()
            lines = ["유럽 법인별 2분기 Short 현황입니다.", ""]
            lines.extend(f"{i}. {entity}: {fmt_num(value)}대" for i, (entity, value) in enumerate(rows, 1))
            lines.append("")
            lines.append(f"법인별 합계는 {fmt_num(sum(v for _, v in rows))}대입니다.")
            return "\n".join(lines)

        if "사업부" in q and "fp" in q and "매출" in q:
            value = con.execute(
                """
                SELECT value FROM psi_long
                WHERE period='2분기' AND metric='매출' AND comparison=''
                  AND sub_header='FP (매출)' AND business_unit='사업부'
                  AND region_entity='Total' AND psi_model_26='Total'
                """
            ).fetchone()[0]
            return f"2분기 사업부 FP(매출)는 {fmt_num(value)}입니다."
    finally:
        con.close()
    return None


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
async def health() -> dict[str, Any]:
    url = webhook_url()
    route = webhook_route_from_url(url)
    return {
        "status": "ok",
        "webhook_url": url,
        "webhook_route": route,
        "has_webhook_secret": bool(discover_webhook_secret(route)),
        "state_db_exists": state_db_path().exists(),
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    started = time.monotonic()
    request_id = f"poc2-{uuid.uuid4().hex}"
    delivery_id = request_id

    webhook_status = post_to_hermes_webhook(req.message.strip(), request_id, delivery_id)
    if webhook_status.get("status") not in {"accepted", "delivered"}:
        raise HTTPException(status_code=502, detail=f"Unexpected Hermes webhook response: {webhook_status}")

    wait_seconds = req.timeout_seconds
    if local_fallback_enabled():
        wait_seconds = fallback_after_seconds(req.timeout_seconds)

    try:
        answer, session_id, answer_source = await wait_for_hermes_answer(request_id, wait_seconds)
    except TimeoutError as exc:
        fallback = deterministic_local_answer(req.message.strip()) if local_fallback_enabled() else None
        if not fallback:
            raise HTTPException(status_code=504, detail=str(exc)) from exc
        answer = fallback
        session_id = None
        answer_source = "local_deterministic_fallback_after_webhook"

    return ChatResponse(
        request_id=request_id,
        delivery_id=delivery_id,
        webhook_status=webhook_status,
        answer=answer,
        elapsed_seconds=round(time.monotonic() - started, 2),
        session_id=session_id,
        answer_source=answer_source,
    )
