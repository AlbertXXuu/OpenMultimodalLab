from __future__ import annotations

import unittest

from openmultimodal_lab.metrics import (
    keyword_score,
    numeric_tolerance_score,
    normalized_exact_match,
    score_response,
)
from openmultimodal_lab.models import EvaluationTask, ScoringConfig


class DeterministicMetricTests(unittest.TestCase):
    def test_legacy_keyword_coverage_remains_unchanged(self) -> None:
        result = keyword_score(
            "A red circle is beside a blue square.",
            ("red circle", "blue square"),
        )

        self.assertEqual(result.name, "keyword_coverage")
        self.assertEqual(result.score, 1.0)

    def test_normalized_exact_match_accepts_case_and_punctuation(self) -> None:
        result = normalized_exact_match(" LEFT. ", ("left",))

        self.assertEqual(result.score, 1.0)
        self.assertEqual(result.matched, ("left",))

    def test_normalized_exact_match_rejects_extra_words(self) -> None:
        result = normalized_exact_match("The answer is left.", ("left",))

        self.assertEqual(result.score, 0.0)

    def test_attribute_groups_accept_separated_but_bound_attributes(self) -> None:
        task = EvaluationTask(
            id="shapes",
            prompt="Describe the shapes.",
            expected_keywords=("red circle", "blue square"),
            scoring=ScoringConfig(
                type="attribute_groups",
                groups=(("red", "circle"), ("blue", "square")),
            ),
        )
        response = """The image contains two shapes.

- **Red Shape**: This is a circle. It is colored solid red.
- **Blue Shape**: This is a square. It is colored solid blue.
"""

        result = score_response(task, response)

        self.assertEqual(result.score, 1.0)
        self.assertEqual(result.matched, ("red circle", "blue square"))

    def test_attribute_groups_do_not_accept_swapped_attributes(self) -> None:
        task = EvaluationTask(
            id="shapes",
            prompt="Describe the shapes.",
            expected_keywords=("red circle", "blue square"),
            scoring=ScoringConfig(
                type="attribute_groups",
                groups=(("red", "circle"), ("blue", "square")),
            ),
        )

        result = score_response(task, "A red square and a blue circle.")

        self.assertEqual(result.score, 0.0)
        self.assertEqual(result.matched, ())

    def test_ordered_attribute_groups_penalize_reversed_lists(self) -> None:
        task = EvaluationTask(
            id="ordered-shapes",
            prompt="List the shapes.",
            expected_keywords=("blue circle", "yellow triangle", "green square"),
            scoring=ScoringConfig(
                type="attribute_groups",
                groups=(
                    ("blue", "circle"),
                    ("yellow", "triangle"),
                    ("green", "square"),
                ),
                ordered=True,
            ),
        )
        response = "- green square\n- yellow triangle\n- blue circle"

        result = score_response(task, response)

        self.assertEqual(result.score, 1 / 3)
        self.assertEqual(result.matched, ("blue circle",))

    def test_numeric_tolerance_accepts_value_at_boundary(self) -> None:
        result = numeric_tolerance_score("$1,234.51", 1234.5, 0.01)

        self.assertEqual(result.score, 1.0)
        self.assertEqual(result.details["candidate_count"], 1)

    def test_numeric_tolerance_accepts_negative_value(self) -> None:
        result = numeric_tolerance_score("-20", -20.0, 0.0)

        self.assertEqual(result.score, 1.0)

    def test_numeric_tolerance_rejects_value_outside_tolerance(self) -> None:
        result = numeric_tolerance_score("8.39", 8.37, 0.01)

        self.assertEqual(result.score, 0.0)
        self.assertAlmostEqual(result.details["absolute_error"], 0.02)

    def test_numeric_tolerance_rejects_multiple_candidates(self) -> None:
        result = numeric_tolerance_score("It is 8.37, not 8.36.", 8.37, 0.01)

        self.assertEqual(result.score, 0.0)
        self.assertTrue(result.details["ambiguous"])

    def test_numeric_tolerance_rejects_response_without_number(self) -> None:
        result = numeric_tolerance_score("unknown", 8.37, 0.01)

        self.assertEqual(result.score, 0.0)
        self.assertEqual(result.details["candidate_count"], 0)


if __name__ == "__main__":
    unittest.main()
