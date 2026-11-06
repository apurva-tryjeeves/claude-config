"""The policy tables."""

from __future__ import annotations

import unittest
from datetime import timedelta

from jaidev_watch import policy
from jaidev_watch.models import Stage


class PolicyTest(unittest.TestCase):
    def test_pr_due_by_estimate(self) -> None:
        cases = [(1, 4), (2, 4), (3, 6), (5, 8), (8, 8), (None, 8)]
        for estimate, minutes in cases:
            with self.subTest(estimate=estimate):
                self.assertEqual(policy.pr_due(estimate), timedelta(minutes=minutes))

    def test_every_stage_has_a_policy(self) -> None:
        self.assertEqual(set(policy.STAGE_POLICY), set(Stage))

    def test_plan_first_check_by_pre_estimate(self) -> None:
        cases = [(1, 2), (2, 3), (3, 3), (5, 4), (None, 3)]
        for pre_estimate, minutes in cases:
            with self.subTest(pre_estimate=pre_estimate):
                self.assertEqual(policy.plan_first_check(pre_estimate), timedelta(minutes=minutes))


if __name__ == "__main__":
    unittest.main()
