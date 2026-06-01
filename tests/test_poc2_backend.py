import hashlib
import hmac
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from PoC2.app import (
    deterministic_local_answer,
    find_session_for_request,
    is_unusable_hermes_answer,
    latest_final_assistant_message,
    sign_body,
)


class Poc2BackendTests(unittest.TestCase):
    def test_sign_body_matches_hmac_sha256(self):
        body = b'{"question":"hello"}'
        secret = "test-secret"
        self.assertEqual(
            sign_body(body, secret),
            hmac.new(secret.encode(), body, hashlib.sha256).hexdigest(),
        )

    def test_finds_final_answer_by_request_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "state.db"
            conn = sqlite3.connect(db)
            conn.executescript(
                """
                CREATE TABLE sessions (
                    id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    user_id TEXT,
                    started_at REAL,
                    title TEXT
                );
                CREATE TABLE messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT,
                    tool_calls TEXT,
                    timestamp REAL
                );
                """
            )
            conn.execute(
                "INSERT INTO sessions(id, source, user_id, started_at) VALUES (?, ?, ?, ?)",
                ("s1", "webhook", "webhook:gscm-psi-chat", 1.0),
            )
            conn.execute(
                "INSERT INTO messages(session_id, role, content, tool_calls, timestamp) VALUES (?, ?, ?, ?, ?)",
                ("s1", "user", "request_id=poc2-abc 질문", None, 1.1),
            )
            conn.execute(
                "INSERT INTO messages(session_id, role, content, tool_calls, timestamp) VALUES (?, ?, ?, ?, ?)",
                ("s1", "assistant", "", json.dumps([{"name": "terminal"}]), 1.2),
            )
            conn.execute(
                "INSERT INTO messages(session_id, role, content, tool_calls, timestamp) VALUES (?, ?, ?, ?, ?)",
                ("s1", "assistant", "최종 답변입니다", None, 1.3),
            )
            conn.commit()

            self.assertEqual(find_session_for_request(conn, "poc2-abc"), "s1")
            self.assertEqual(latest_final_assistant_message(conn, "s1"), "최종 답변입니다")
            conn.close()

    def test_detects_unusable_hermes_tool_apology(self):
        self.assertTrue(
            is_unusable_hermes_answer(
                "죄송합니다. 현재 세션에는 터미널/파일 조회 도구가 제공되지 않아 실제 조회할 수 없습니다."
            )
        )
        self.assertTrue(
            is_unusable_hermes_answer(
                "현재 세션에는 DuckDB를 실제 조회할 수 있는 터미널/DB 실행 도구가 제공되지 않아 psi_long 테이블 조회를 수행할 수 없습니다."
            )
        )
        self.assertTrue(
            is_unusable_hermes_answer(
                "현재 세션에서 DuckDB를 조회할 terminal 도구가 제공되지 않아 psi_long 실제 조회를 수행할 수 없습니다."
            )
        )
        self.assertTrue(
            is_unusable_hermes_answer(
                "죄송합니다. 현재 세션에는 DuckDB를 직접 조회할 수 있는 터미널 실행 도구가 연결되어 있지 않아, `psi_long` 실제 조회 결과를 확인할 수 없습니다."
            )
        )
        self.assertFalse(is_unusable_hermes_answer("사업부 2분기 채널 Short는 1,185,642대입니다."))

    def test_channel_short_fallback_query(self):
        answer = deterministic_local_answer("사업부 2분기 채널숏 알려줘")
        self.assertIsNotNone(answer)
        assert answer is not None
        self.assertIn("Short-Ch_Constraint: 1,185,642대", answer)
        self.assertIn("전주비: -285,032대", answer)

    def test_q3_short_top5_fallback_query(self):
        answer = deterministic_local_answer("3분기 Short가 가장 큰 지역 Top 5 보여줘")
        self.assertIsNotNone(answer)
        assert answer is not None
        self.assertIn("1. Latin America: 3,668,584대", answer)
        self.assertIn("5. SELA: 1,271,879대", answer)


if __name__ == "__main__":
    unittest.main()
