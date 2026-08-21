import unittest

from scripts.run_self_profile_local_e2e import run_acceptance


class SelfProfileLocalE2ETests(unittest.TestCase):
    def test_required_questions_pass_through_local_api_boundary(self):
        report = run_acceptance()

        self.assertTrue(report["passed"], report["failures"])
        self.assertEqual(report["self_profile_questions"], 7)
        self.assertTrue(report["employment_history_passed"])
        self.assertTrue(report["profile_failure_passed"])
        self.assertEqual(report["model_calls"], 0)
        self.assertEqual(report["memory_calls"], 0)
        self.assertEqual(report["action_calls"], 0)
        self.assertEqual(report["diagnostic_events"], 9)


if __name__ == "__main__":
    unittest.main()
