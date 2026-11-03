import unittest
import testcases


class TestReportCases(unittest.TestCase):
    def test_all_cases_from_report(self):
        for tid, scenario, expected, actual, ok in testcases.run_all():
            with self.subTest(case=tid):
                self.assertEqual(ok, "PASS", f"{tid}: expected {expected}, got {actual}")


if __name__ == "__main__":
    unittest.main()
