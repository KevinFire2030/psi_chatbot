import unittest

from app.query_planner import QueryPlanner


class TestQueryPlanner(unittest.TestCase):
    def test_plans_period_delta_by_model_question(self):
        planner = QueryPlanner()
        plan = planner.plan("Europe에서 2분기 대비 3분기 Short가 늘어난 모델 보여줘")

        self.assertEqual(plan.kind, "period_delta_by_model")
        self.assertEqual(plan.region_entity, "Europe")
        self.assertEqual(plan.base_period, "2분기")
        self.assertEqual(plan.compare_period, "3분기")
        self.assertEqual(plan.metric, "Short")
        self.assertIn("WITH base AS", plan.sql)
        self.assertIn("delta", plan.sql)
        self.assertIn("psi_model_26 <> 'Total'", plan.sql)
        self.assertEqual(plan.params, ["2분기", "Short", "Europe", "3분기", "Short", "Europe", 10])
        self.assertIn("2분기와 3분기의 Short를 모델별로 비교", plan.explanation)


if __name__ == "__main__":
    unittest.main()
