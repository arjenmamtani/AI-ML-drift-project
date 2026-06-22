"""
Statistical drift detection algorithms.

Three complementary tests, each with different strengths:

  - KS (Kolmogorov-Smirnov): non-parametric test for continuous features.
    Compares empirical CDFs. Fast, well-understood, but loses power on
    multimodal distributions and is less sensitive to shifts in the tails.

  - PSI (Population Stability Index): the industry-standard metric in credit
    risk / finance for monitoring categorical or binned features. Symmetric,
    interpretable (rule-of-thumb thresholds), but requires binning continuous
    data which loses some resolution.

  - JSD (Jensen-Shannon Divergence): symmetric, bounded [0, 1] measure of
    distance between two probability distributions. More robust than KL
    divergence (which is asymmetric and unbounded), works on binned data
    like PSI but with stronger theoretical grounding.

Each detector returns a DriftResult with a score, a boolean drifted flag
based on a threshold, and (where applicable) a p-value.
"""

from dataclasses import dataclass

import numpy as np
from scipy import stats


@dataclass
class DriftResult:
    test_type: str
    drift_score: float
    p_value: float | None
    is_drifted: bool
    threshold: float
    sample_size: int


# ── Kolmogorov-Smirnov test ───────────────────────────────────────────────────

def ks_test(
    reference: np.ndarray,
    current: np.ndarray,
    alpha: float = 0.05,
) -> DriftResult:
    """
    Two-sample KS test on continuous numeric features.

    Null hypothesis: both samples are drawn from the same distribution.
    We reject the null (flag drift) when p < alpha.

    The KS statistic itself is the maximum distance between the two
    empirical CDFs — ranges from 0 (identical) to 1 (completely disjoint).
    """
    reference = np.asarray(reference, dtype=float)
    current = np.asarray(current, dtype=float)

    statistic, p_value = stats.ks_2samp(reference, current)

    return DriftResult(
        test_type="ks",
        drift_score=float(statistic),
        p_value=float(p_value),
        is_drifted=bool(p_value < alpha),
        threshold=alpha,
        sample_size=len(current),
    )


# ── Population Stability Index ────────────────────────────────────────────────

def _bin_distribution(
    reference: np.ndarray, current: np.ndarray, n_bins: int = 10
) -> tuple[np.ndarray, np.ndarray]:
    """
    Bin both arrays using quantile edges derived from the reference set.
    Using reference-derived edges (not current) is important: it ensures
    we're measuring how current data falls into "expected" buckets.
    """
    quantiles = np.linspace(0, 1, n_bins + 1)
    edges = np.quantile(reference, quantiles)
    edges[0] = -np.inf
    edges[-1] = np.inf
    edges = np.unique(edges)  # guard against degenerate/duplicate edges

    ref_counts, _ = np.histogram(reference, bins=edges)
    cur_counts, _ = np.histogram(current, bins=edges)

    # Convert to proportions, with a small epsilon to avoid log(0)
    eps = 1e-4
    ref_props = ref_counts / max(ref_counts.sum(), 1) + eps
    cur_props = cur_counts / max(cur_counts.sum(), 1) + eps

    return ref_props, cur_props


def psi(
    reference: np.ndarray,
    current: np.ndarray,
    n_bins: int = 10,
    threshold: float = 0.2,
) -> DriftResult:
    """
    Population Stability Index.

    PSI = sum( (current_i - reference_i) * ln(current_i / reference_i) )

    Industry rule of thumb (credit risk / fintech standard):
      PSI < 0.1  -> no significant shift
      0.1 - 0.25 -> moderate shift, investigate
      PSI > 0.25 -> significant shift, action required

    We default the actionable threshold to 0.2 as a reasonable middle ground.
    """
    reference = np.asarray(reference, dtype=float)
    current = np.asarray(current, dtype=float)

    ref_props, cur_props = _bin_distribution(reference, current, n_bins)

    psi_value = float(np.sum((cur_props - ref_props) * np.log(cur_props / ref_props)))

    return DriftResult(
        test_type="psi",
        drift_score=psi_value,
        p_value=None,  # PSI has no associated p-value; it's a descriptive statistic
        is_drifted=psi_value > threshold,
        threshold=threshold,
        sample_size=len(current),
    )


# ── Jensen-Shannon Divergence ─────────────────────────────────────────────────

def jensen_shannon_divergence(
    reference: np.ndarray,
    current: np.ndarray,
    n_bins: int = 10,
    threshold: float = 0.1,
) -> DriftResult:
    """
    Jensen-Shannon divergence between binned distributions.

    JSD is the symmetrized, smoothed version of KL divergence:
      JSD(P, Q) = 0.5 * KL(P || M) + 0.5 * KL(Q || M),  where M = 0.5*(P+Q)

    Bounded in [0, 1] (using log base 2), which makes it easier to set a
    consistent threshold across features than raw KL divergence.
    """
    reference = np.asarray(reference, dtype=float)
    current = np.asarray(current, dtype=float)

    ref_props, cur_props = _bin_distribution(reference, current, n_bins)

    # scipy's jensenshannon returns the distance (sqrt of divergence) by default
    js_distance = float(_jensen_shannon_distance(ref_props, cur_props))
    js_divergence = js_distance ** 2  # convert distance back to divergence

    return DriftResult(
        test_type="jsd",
        drift_score=js_divergence,
        p_value=None,
        is_drifted=js_divergence > threshold,
        threshold=threshold,
        sample_size=len(current),
    )


def _jensen_shannon_distance(p: np.ndarray, q: np.ndarray) -> float:
    """Wrapper around scipy's JS distance to keep the public API clean."""
    from scipy.spatial.distance import jensenshannon
    return jensenshannon(p, q, base=2)


# ── Categorical drift (chi-squared) ───────────────────────────────────────────

def categorical_drift(
    reference: list[str],
    current: list[str],
    alpha: float = 0.05,
) -> DriftResult:
    """
    Chi-squared test for categorical features (e.g. 'city', 'product_category').
    Compares observed frequency distributions between reference and current.
    """
    ref_arr = np.asarray(reference)
    cur_arr = np.asarray(current)

    categories = sorted(set(ref_arr.tolist()) | set(cur_arr.tolist()))

    ref_counts = np.array([np.sum(ref_arr == c) for c in categories])
    cur_counts = np.array([np.sum(cur_arr == c) for c in categories])

    # Scale reference counts to match current sample size (expected frequencies)
    ref_total = ref_counts.sum()
    cur_total = cur_counts.sum()
    expected = ref_counts * (cur_total / max(ref_total, 1))

    # Avoid zero-expected-frequency issues
    expected = np.clip(expected, 1e-6, None)

    statistic, p_value = stats.chisquare(f_obs=cur_counts, f_exp=expected)

    return DriftResult(
        test_type="chi2",
        drift_score=float(statistic),
        p_value=float(p_value),
        is_drifted=bool(p_value < alpha),
        threshold=alpha,
        sample_size=len(current),
    )
