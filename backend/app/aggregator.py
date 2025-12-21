"""
Xea Governance Oracle - Aggregator

Aggregates miner responses and computes PoI/PoUW metrics.
"""

from typing import Optional
import statistics

from app.schemas import MinerResponse, AggregatedMetrics, Recommendation


# PoUW Rubric Weights
POUW_WEIGHTS = {
    "accuracy": 0.4,
    "omission_risk": 0.3,
    "evidence_quality": 0.2,
    "governance_relevance": 0.1,
}


def calculate_pouw_composite(scores: dict) -> float:
    """
    Calculate PoUW composite score from individual criteria scores.

    Uses weights:
    - accuracy: 0.4
    - omission_risk: 0.3
    - evidence_quality: 0.2
    - governance_relevance: 0.1

    Args:
        scores: Dict with keys accuracy, omission_risk, evidence_quality, governance_relevance
                Each value should be in range [0.0, 1.0]

    Returns:
        Composite score in range [0.0, 1.0]
    """
    composite = sum(POUW_WEIGHTS[k] * scores.get(k, 0) for k in POUW_WEIGHTS)
    return round(composite, 3)


def calculate_poi_agreement(responses: list[MinerResponse], claim_id: str) -> float:
    """
    Calculate Proof of Inference agreement for a claim.

    Measures consensus among miner verdicts.

    Args:
        responses: List of miner responses
        claim_id: Claim to calculate agreement for

    Returns:
        Agreement score in range [0.0, 1.0]
    """
    claim_responses = [r for r in responses if r.claim_id == claim_id]
    if not claim_responses:
        return 0.0

    verdicts = [r.verdict for r in claim_responses]
    if not verdicts:
        return 0.0

    # Find majority verdict
    verdict_counts = {}
    for v in verdicts:
        verdict_counts[v] = verdict_counts.get(v, 0) + 1

    max_count = max(verdict_counts.values())
    agreement = max_count / len(verdicts)
    return round(agreement, 3)


def calculate_confidence_interval(
    values: list[float],
    confidence: float = 0.95,
) -> tuple[float, float]:
    """
    Calculate confidence interval for a list of values.

    Args:
        values: List of numeric values
        confidence: Confidence level (default 0.95 for 95% CI)

    Returns:
        Tuple of (lower, upper) bounds
    """
    if not values:
        return (0.0, 0.0)

    if len(values) == 1:
        return (values[0], values[0])

    mean = statistics.mean(values)
    stdev = statistics.stdev(values)
    n = len(values)

    # Approximate z-score for common confidence levels
    z_scores = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
    z = z_scores.get(confidence, 1.96)

    margin = z * (stdev / (n ** 0.5))
    lower = max(0.0, round(mean - margin, 3))
    upper = min(1.0, round(mean + margin, 3))

    return (lower, upper)


def aggregate_miner_responses(
    responses: list[MinerResponse],
    claim_ids: list[str],
) -> AggregatedMetrics:
    """
    Aggregate all miner responses into metrics.

    Computes:
    - PoI agreement across all claims
    - PoUW scores with confidence intervals
    - Consensus verdict

    Args:
        responses: All miner responses
        claim_ids: List of claim IDs being validated

    Returns:
        AggregatedMetrics with all computed values
    """
    # TODO: Implement full aggregation logic
    # - Calculate per-claim PoI
    # - Average PoUW scores
    # - Determine consensus verdict
    # - Compute confidence intervals

    # Placeholder return
    return AggregatedMetrics(
        poi_agreement=0.0,
        poi_confidence_interval=(0.0, 0.0),
        pouw_score=0.0,
        pouw_confidence_interval=(0.0, 0.0),
        total_miners=0,
        responding_miners=0,
        consensus_verdict="unverifiable",
        claim_coverage=0.0,
    )


def generate_recommendation(metrics: AggregatedMetrics) -> Recommendation:
    """
    Generate governance recommendation from aggregated metrics.

    Args:
        metrics: Aggregated validation metrics

    Returns:
        Recommendation with action, confidence, and summary
    """
    # TODO: Implement recommendation logic
    # - Determine action based on consensus and confidence
    # - Identify risk flags
    # - Generate human-readable summary

    return Recommendation(
        action="review",
        confidence=0.0,
        risk_flags=[],
        summary="Insufficient data to generate recommendation",
    )
