import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import duckdb
from fastapi.testclient import TestClient

from PoC2.app import app
from PoC2.fast_path import build_fast_path_answer, detect_fast_path_intent


class Poc2FastPathTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "psi.duckdb"
        with duckdb.connect(str(self.db_path)) as con:
            con.execute(
                """
                CREATE TABLE psi_long (
                    period TEXT,
                    region_entity TEXT,
                    business_unit TEXT,
                    psi_model_26 TEXT,
                    sales_model_26 TEXT,
                    model_code TEXT,
                    metric TEXT,
                    sub_header TEXT,
                    comparison TEXT,
                    value DOUBLE
                )
                """
            )
            rows = [
                ("2분기", "SEA", "", "Total", "Total(PC포함)", "", "매출", "FP (매출)", "", 3818141000.0),
                ("2분기", "SEA", "", "Total", "Total(PC포함)", "", "매출전년", "25년 (매출)", "", 3857377349.0055532),
                ("2분기", "SEA", "", "Total", "Total(PC포함)", "", "매출", "", "전년比(매출)", -39236349.005553246),
                ("2분기", "SEA", "", "Total", "Total(PC포함)", "", "매출", "", "(%)", 0.9875315585578998),
                ("2분기", "SEA", "", "Total", "Total(PC포함)", "", "매출", "", "전주比", -865000.0),
                ("6월", "Total", "사업부", "Total", "", "", "WOS(EDI+FOTA)", "WOS", "", 10.92),
                ("6월", "Total", "사업부", "Total", "", "", "T.WOS", "T.WOS", "", 8.88),
                ("6월", "Total", "사업부", "Total", "", "", "WOS(EDI+FOTA)", "", "적정比", 1.23),
                ("6월", "Total", "사업부", "Total", "", "", "WOS(EDI+FOTA)전주", "", "", -0.07),
                ("6월", "Total", "사업부", "Total", "", "", "WOS (F4)", "WOS (F4)", "", 10.07),
            ]
            con.executemany("INSERT INTO psi_long VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)
        self.addCleanup(self.tmpdir.cleanup)

    def test_detects_quarter_entity_sales_fast_path(self):
        intent = detect_fast_path_intent("2분기 sea 매출 알려줘")
        self.assertIsNotNone(intent)
        self.assertEqual(intent.kind, "entity_quarter_sales")
        self.assertEqual(intent.period, "2분기")
        self.assertEqual(intent.region_entity, "SEA")

    def test_builds_sales_answer_from_duckdb_in_under_three_seconds(self):
        started = time.monotonic()
        answer = build_fast_path_answer("2분기 sea 매출 알려줘", db_path=str(self.db_path))
        elapsed = time.monotonic() - started

        self.assertLess(elapsed, 3.0)
        self.assertIn("W23_Pre plan 기준", answer)
        self.assertIn("2분기 **SEA 매출(FP)**은 **3,818.1 백만불**", answer)
        self.assertIn("전년 대비: **-39.2 백만불**", answer)
        self.assertIn("전년비: **98.8%**", answer)

    def test_builds_business_unit_wos_answer_from_duckdb(self):
        answer = build_fast_path_answer("6월 사업부 wos 알려줘", db_path=str(self.db_path))

        self.assertIn("6월 사업부 WOS는 **10.92주**", answer)
        self.assertIn("T.WOS: **8.88주**", answer)
        self.assertIn("적정比: **123.0%**", answer)
        self.assertIn("전주 대비: **-0.07주**", answer)

    def test_chat_endpoint_uses_fast_path_without_calling_hermes_webhook(self):
        with patch.dict(os.environ, {"PSI_FAST_PATH_DB": str(self.db_path), "PSI_FAST_PATH_ENABLED": "1"}):
            with patch("PoC2.app.post_to_hermes_webhook") as post_to_hermes:
                client = TestClient(app)
                response = client.post("/api/chat", json={"message": "2분기 sea 매출 알려줘"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["answer_source"], "local_duckdb_fast_path")
        self.assertIn("3,818.1 백만불", payload["answer"])
        self.assertLess(payload["elapsed_seconds"], 3.0)
        post_to_hermes.assert_not_called()

    def test_telegram_fast_path_endpoint_accepts_message_text(self):
        with patch.dict(os.environ, {"PSI_FAST_PATH_DB": str(self.db_path), "PSI_FAST_PATH_ENABLED": "1"}):
            client = TestClient(app)
            response = client.post(
                "/api/telegram/fast-path",
                json={"message": {"text": "2분기 sea 매출 알려줘", "chat": {"id": -100}, "message_id": 1}},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["handled"])
        self.assertEqual(payload["answer_source"], "local_duckdb_fast_path")
        self.assertIn("3,818.1 백만불", payload["answer"])


if __name__ == "__main__":
    unittest.main()
