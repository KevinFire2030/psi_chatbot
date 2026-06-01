import unittest

from scripts.query_psi import parse_query


class TestQueryPsi(unittest.TestCase):
    def test_parse_top_short_question(self):
        intent = parse_query("3분기 Short가 가장 큰 지역 Top 5 보여줘")
        self.assertEqual(intent.period, "3분기")
        self.assertEqual(intent.metric, "Short")
        self.assertEqual(intent.limit, 5)
        self.assertEqual(intent.order, "desc")

    def test_parse_wos_threshold_question(self):
        intent = parse_query("9월 WOS가 13 이상인 법인을 알려줘")
        self.assertEqual(intent.period, "9월")
        self.assertEqual(intent.metric, "WOS(EDI+FOTA)")
        self.assertEqual(intent.threshold, 13.0)


if __name__ == "__main__":
    unittest.main()
