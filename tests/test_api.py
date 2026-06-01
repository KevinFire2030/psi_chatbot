import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from app.main import create_app
from app.psi_service import PsiQueryService


class TestPsiQueryService(unittest.TestCase):
    def test_service_returns_ranked_rows_from_duckdb(self):
        with tempfile.NamedTemporaryFile(suffix=".duckdb") as tmp:
            service = PsiQueryService(tmp.name)
            service.initialize_schema_for_test()
            service.insert_test_row(
                region_entity="Europe",
                period="3분기",
                metric="Short",
                value=100.0,
            )
            service.insert_test_row(
                region_entity="Latin America",
                period="3분기",
                metric="Short",
                value=200.0,
            )

            result = service.query("3분기 Short 상위 2개 지역")

            self.assertEqual(result.intent["period"], "3분기")
            self.assertEqual(result.intent["metric"], "Short")
            self.assertEqual(result.rows[0].region_entity, "Latin America")
            self.assertEqual(result.rows[0].value, 200.0)
            self.assertIn("SELECT", result.sql)
            self.assertTrue(result.explanation)

    def test_service_executes_delta_plan(self):
        with tempfile.NamedTemporaryFile(suffix=".duckdb") as tmp:
            service = PsiQueryService(tmp.name)
            service.initialize_schema_for_test()
            service.insert_test_row("Europe", "2분기", "Short", 10.0, psi_model_26="A")
            service.insert_test_row("Europe", "3분기", "Short", 15.0, psi_model_26="A")
            service.insert_test_row("Europe", "2분기", "Short", 20.0, psi_model_26="B")
            service.insert_test_row("Europe", "3분기", "Short", 18.0, psi_model_26="B")

            result = service.query("Europe에서 2분기 대비 3분기 Short가 늘어난 모델 보여줘")

            self.assertEqual(result.intent["kind"], "period_delta_by_model")
            self.assertEqual(result.rows[0].psi_model_26, "A")
            self.assertEqual(result.rows[0].delta, 5.0)
            self.assertIn("base_value", result.rows[0].extra)


class TestFastApiApp(unittest.TestCase):
    def test_query_endpoint_returns_json(self):
        with tempfile.NamedTemporaryFile(suffix=".duckdb") as tmp:
            service = PsiQueryService(tmp.name)
            service.initialize_schema_for_test()
            service.insert_test_row(
                region_entity="SEM",
                period="9월",
                metric="WOS(EDI+FOTA)",
                value=17.6,
            )
            app = create_app(service=service)
            client = TestClient(app)

            response = client.post("/query", json={"question": "9월 WOS가 13 이상인 법인"})

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["intent"]["period"], "9월")
            self.assertEqual(payload["intent"]["metric"], "WOS(EDI+FOTA)")
            self.assertEqual(payload["rows"][0]["region_entity"], "SEM")

    def test_homepage_serves_chat_ui(self):
        with tempfile.NamedTemporaryFile(suffix=".duckdb") as tmp:
            service = PsiQueryService(tmp.name)
            service.initialize_schema_for_test()
            app = create_app(service=service)
            client = TestClient(app)

            response = client.get("/")

            self.assertEqual(response.status_code, 200)
            html = response.text
            self.assertIn("GSCM PSI Chatbot", html)
            self.assertIn("id=\"questionInput\"", html)
            self.assertIn("/query", html)


if __name__ == "__main__":
    unittest.main()
