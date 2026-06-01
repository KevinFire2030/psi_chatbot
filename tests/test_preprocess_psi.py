import unittest

from scripts.preprocess_psi import (
    col_to_index,
    index_to_col,
    parse_metric_header,
    unique_metric_key,
)


class TestPreprocessPsi(unittest.TestCase):
    def test_excel_column_roundtrip(self):
        examples = {
            "A": 0,
            "Z": 25,
            "AA": 26,
            "BT": 71,
            "AJA": 936,
        }
        for col, idx in examples.items():
            self.assertEqual(col_to_index(col), idx)
            self.assertEqual(index_to_col(idx), col)

    def test_parse_metric_header_splits_period_and_metric(self):
        parsed = parse_metric_header("3분기Short-Ch_Constraint전주比")
        self.assertEqual(parsed["period"], "3분기")
        self.assertEqual(parsed["metric"], "Short-Ch_Constraint")
        self.assertEqual(parsed["comparison"], "전주比")

    def test_parse_metric_header_handles_wos_variant(self):
        parsed = parse_metric_header("9월WOS(EDI+FOTA)적정比")
        self.assertEqual(parsed["period"], "9월")
        self.assertEqual(parsed["metric"], "WOS(EDI+FOTA)")
        self.assertEqual(parsed["comparison"], "적정比")

    def test_unique_metric_key_includes_source_column_for_duplicate_headers(self):
        first = unique_metric_key("1분기Demand", "AA", "DP (FP)")
        second = unique_metric_key("1분기Demand", "AB", "전주")
        self.assertNotEqual(first, second)
        self.assertIn("AA", first)
        self.assertIn("AB", second)


if __name__ == "__main__":
    unittest.main()
