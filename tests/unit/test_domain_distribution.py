"""Unit tests for simulation domain distribution algorithm.

Validates that the largest remainder method distributes questions
proportionally to AI-103 domain weights (within ±1 due to rounding)
and that the total always equals the configured num_questions.

Validates: Requirements 5.1, 5.6
"""

import pytest

from src.api.application.services.session_service import SessionService
from src.api.domain.enums.domain_type import DomainType, get_domain_weights


class TestDistributeQuestions:
    """Tests for SessionService._distribute_questions static method."""

    def setup_method(self) -> None:
        """Set up AI-103 domain weights for tests."""
        self.weights = get_domain_weights()

    def test_total_equals_n_for_default_simulation(self) -> None:
        """Total distributed questions must equal N=20."""
        result = SessionService._distribute_questions(self.weights, 20)
        assert sum(result.values()) == 20

    def test_total_equals_n_for_various_sizes(self) -> None:
        """Total distributed questions must equal N for various values."""
        for n in [5, 10, 15, 20, 25, 30, 50, 100]:
            result = SessionService._distribute_questions(self.weights, n)
            assert sum(result.values()) == n, f"Failed for N={n}"

    def test_each_domain_within_plus_minus_one_of_ideal(self) -> None:
        """Each domain's count is within ±1 of weight * N."""
        n = 20
        result = SessionService._distribute_questions(self.weights, n)

        for domain, count in result.items():
            ideal = domain.weight * n
            assert abs(count - ideal) <= 1, (
                f"Domain {domain.value}: count={count}, ideal={ideal:.2f}, "
                f"diff={abs(count - ideal):.2f}"
            )

    def test_expected_distribution_for_n20(self) -> None:
        """For N=20, the expected distribution is 7, 3, 4, 3, 3."""
        result = SessionService._distribute_questions(self.weights, 20)

        # Generative AI: 0.35 * 20 = 7.0 → 7
        assert result[DomainType.GENERATIVE_AI_AND_AGENTS] == 7
        # Computer Vision: 0.15 * 20 = 3.0 → 3
        assert result[DomainType.COMPUTER_VISION] == 3
        # Text Analysis: 0.20 * 20 = 4.0 → 4
        assert result[DomainType.TEXT_ANALYSIS] == 4
        # Information Extraction: 0.15 * 20 = 3.0 → 3
        assert result[DomainType.INFORMATION_EXTRACTION] == 3
        # Plan and Manage: 0.15 * 20 = 3.0 → 3
        assert result[DomainType.PLAN_AND_MANAGE] == 3

    def test_all_domains_represented_for_reasonable_n(self) -> None:
        """All domains get at least 1 question when N is large enough.

        With min weight 0.15, we need N such that floor(0.15 * N) >= 1,
        i.e., N >= 7 (floor(0.15*7)=1). For N >= 7 every domain is
        guaranteed at least 1 question with these weights.
        """
        for n in range(7, 50):
            result = SessionService._distribute_questions(self.weights, n)
            for domain, count in result.items():
                assert count >= 1, (
                    f"Domain {domain.value} got 0 questions for N={n}"
                )

    def test_all_domains_present_in_result(self) -> None:
        """Result contains all domains from the weights dict."""
        result = SessionService._distribute_questions(self.weights, 20)
        assert set(result.keys()) == set(self.weights.keys())

    def test_n_equals_zero_returns_all_zeros(self) -> None:
        """When N=0, all domains get 0 questions."""
        result = SessionService._distribute_questions(self.weights, 0)
        assert sum(result.values()) == 0
        for count in result.values():
            assert count == 0

    def test_rounding_with_non_integer_products(self) -> None:
        """For N=13, weights produce non-integer ideals; total still = 13."""
        # 0.35*13=4.55, 0.15*13=1.95, 0.20*13=2.60, 0.15*13=1.95, 0.15*13=1.95
        result = SessionService._distribute_questions(self.weights, 13)
        assert sum(result.values()) == 13

        for domain, count in result.items():
            ideal = domain.weight * 13
            assert abs(count - ideal) <= 1, (
                f"Domain {domain.value}: count={count}, ideal={ideal:.2f}"
            )
