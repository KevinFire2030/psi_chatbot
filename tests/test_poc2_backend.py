import hashlib
import hmac
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

import PoC2.app as poc2_app
from PoC2.app import (
    DEFAULT_TIMEOUT_SECONDS,
    find_session_for_request,
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

    def test_no_local_duckdb_fallback_is_present(self):
        self.assertFalse(hasattr(poc2_app, "deterministic_local_answer"))
        self.assertFalse(hasattr(poc2_app, "local_fallback_enabled"))
        self.assertFalse(hasattr(poc2_app, "fallback_after_seconds"))
        self.assertFalse(hasattr(poc2_app, "is_unusable_hermes_answer"))

    def test_default_timeout_waits_for_gateway_agent(self):
        self.assertEqual(DEFAULT_TIMEOUT_SECONDS, 1800)
        timeout_field = poc2_app.ChatRequest.model_fields["timeout_seconds"]
        metadata = {type(item).__name__: item for item in timeout_field.metadata}
        self.assertEqual(metadata["Ge"].ge, 10)
        self.assertEqual(metadata["Le"].le, 1800)


if __name__ == "__main__":
    unittest.main()
