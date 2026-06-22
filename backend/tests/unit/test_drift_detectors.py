"""
Unit tests for drift detection algorithms.

These tests are deliberately built around synthetic distributions with
KNOWN properties, so we can assert the detectors behave correctly:
  - Identical distributions should NOT trigger drift
  - Clearly shifted distributions SHOULD trigger drift
  - Edge cases (tiny samples, identical values) should not crash
"""

import numpy as np
import pytest

from app.drift.detectors import (
    categorical_drift,
    jensen_shannon_divergence,
    ks_test,
    psi,
)


@pytest.fixture
def rng():
    return np.random.default_rng(42)


class TestKSTest:
    def test_identical_distributions_no_drift(self, rng):
        reference = rng.normal(50, 10, size=1000)
        current = rng.normal(50, 10, size=1000)

        result = ks_test(reference, current)

        assert result.test_type == "ks"
        assert result.is_drifted is False
        assert result.p_value > 0.05

    def test_shifted_distribution_detects_drift(self, rng):
        reference = rng.normal(50, 10, size=1000)
        # Shift mean by 3 standard deviations — should be obviously different
        current = rng.normal(80, 10, size=1000)

        result = ks_test(reference, current)

        assert result.is_drifted is True
        assert result.p_value < 0.05
        assert result.drift_score > 0.3  # large KS statistic expected

    def test_subtle_shift_lower_score_than_large_shift(self, rng):
        reference = rng.normal(50, 10, size=1000)
        small_shift = rng.normal(53, 10, size=1000)
        large_shift = rng.normal(80, 10, size=1000)

        small_result = ks_test(reference, small_shift)
        large_result = ks_test(reference, large_shift)

        assert small_result.drift_score < large_result.drift_score

    def test_sample_size_recorded(self, rng):
        reference = rng.normal(0, 1, size=500)
        current = rng.normal(0, 1, size=237)

        result = ks_test(reference, current)
        assert result.sample_size == 237


class TestPSI:
    def test_identical_distributions_low_psi(self, rng):
        reference = rng.normal(50, 10, size=2000)
        current = rng.normal(50, 10, size=2000)

        result = psi(reference, current)

        assert result.test_type == "psi"
        assert result.is_drifted is False
        assert result.drift_score < 0.1  # well below "no shift" threshold

    def test_major_shift_high_psi(self, rng):
        reference = rng.normal(50, 10, size=2000)
        current = rng.normal(100, 10, size=2000)

        result = psi(reference, current)

        assert result.is_drifted is True
        assert result.drift_score > 0.25  # well above "significant shift" threshold

    def test_psi_threshold_is_configurable(self, rng):
        reference = rng.normal(50, 10, size=1000)
        current = rng.normal(55, 10, size=1000)  # moderate shift

        strict_result = psi(reference, current, threshold=0.05)
        lenient_result = psi(reference, current, threshold=0.9)

        # Same data, different thresholds, possibly different drift conclusion
        assert strict_result.drift_score == lenient_result.drift_score
        assert strict_result.threshold == 0.05
        assert lenient_result.threshold == 0.9


class TestJensenShannon:
    def test_identical_distributions_zero_divergence(self, rng):
        reference = rng.normal(50, 10, size=2000)
        current = rng.normal(50, 10, size=2000)

        result = jensen_shannon_divergence(reference, current)

        assert result.test_type == "jsd"
        assert result.drift_score < 0.05
        assert result.is_drifted is False

    def test_completely_disjoint_distributions_high_divergence(self, rng):
        reference = rng.normal(0, 1, size=2000)
        current = rng.normal(200, 1, size=2000)  # totally separate

        result = jensen_shannon_divergence(reference, current)

        assert result.is_drifted is True
        # JSD with log base 2 is bounded by 1.0 — disjoint distributions
        # should approach that ceiling
        assert result.drift_score > 0.5

    def test_jsd_is_bounded(self, rng):
        reference = rng.uniform(0, 1, size=1000)
        current = rng.uniform(1000, 2000, size=1000)

        result = jensen_shannon_divergence(reference, current)
        assert 0.0 <= result.drift_score <= 1.01  # small float tolerance


class TestCategoricalDrift:
    def test_identical_category_distribution_no_drift(self, rng):
        categories = ["A", "B", "C"]
        reference = rng.choice(categories, size=1000, p=[0.5, 0.3, 0.2]).tolist()
        current = rng.choice(categories, size=1000, p=[0.5, 0.3, 0.2]).tolist()

        result = categorical_drift(reference, current)
        assert result.is_drifted is False

    def test_shifted_category_balance_detects_drift(self, rng):
        categories = ["A", "B", "C"]
        reference = rng.choice(categories, size=1000, p=[0.8, 0.1, 0.1]).tolist()
        # Completely flip the distribution
        current = rng.choice(categories, size=1000, p=[0.1, 0.1, 0.8]).tolist()

        result = categorical_drift(reference, current)
        assert result.is_drifted is True

    def test_new_category_appearing_in_current(self, rng):
        reference = ["A"] * 500 + ["B"] * 500
        current = ["A"] * 400 + ["B"] * 400 + ["C"] * 200  # "C" is new

        result = categorical_drift(reference, current)
        assert result.is_drifted is True


class TestEdgeCases:
    def test_small_but_valid_sample_sizes_dont_crash(self, rng):
        reference = rng.normal(0, 1, size=35)
        current = rng.normal(0, 1, size=35)

        # Should not raise
        ks_test(reference, current)
        psi(reference, current)
        jensen_shannon_divergence(reference, current)

    def test_constant_feature_no_crash(self):
        # All identical values — degenerate distribution
        reference = np.array([5.0] * 100)
        current = np.array([5.0] * 100)

        result = ks_test(reference, current)
        assert result.drift_score == 0.0
        assert result.is_drifted is False
