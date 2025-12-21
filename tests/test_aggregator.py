"""
Xea Governance Oracle - Aggregator Tests

Unit tests for PoI/PoUW aggregation functionality.
"""

import pytest
from typing import Any


# Synthetic miner responses for testing
def create_mock_miner_response(
    miner_id: str,
    claim_id: str,
    verdict: str,
    accuracy: float = 0.9,
    omission_risk: float = 0.1,
    evidence_quality: float = 0.85,
    governance_relevance: float = 0.9,
) -> dict[str, Any]:
    """Create a mock miner response for testing."""
    return {
        "miner_id": miner_id,
        "claim_id": claim_id,
        "verdict": verdict,
        "rationale": f"Test rationale from {miner_id}",
        "evidence_links": ["https://example.com/evidence"],
        "embedding": [0.1, 0.2, 0.3],
        "scores": {
            "accuracy": accuracy,
            "omission_risk": omission_risk,
            "evidence_quality": evidence_quality,
            "governance_relevance": governance_relevance,
            "composite": 0.0,  # Will be calculated
        }
    }


class TestPoUWCalculation:
    """Test Proof of Useful Work score calculation."""

    def test_pouw_composite_calculation(self):
        """Composite score should match weighted sum."""
        from app.aggregator import calculate_pouw_composite
        
        scores = {
            "accuracy": 0.9,
            "omission_risk": 0.1,
            "evidence_quality": 0.8,
            "governance_relevance": 0.95,
        }
        
        # Expected: 0.4*0.9 + 0.3*0.1 + 0.2*0.8 + 0.1*0.95
        # = 0.36 + 0.03 + 0.16 + 0.095 = 0.645
        expected = 0.645
        
        result = calculate_pouw_composite(scores)
        
        assert abs(result - expected) < 0.001

    def test_pouw_weights_sum_to_one(self):
        """PoUW weights should sum to 1.0."""
        from app.aggregator import POUW_WEIGHTS
        
        total = sum(POUW_WEIGHTS.values())
        assert abs(total - 1.0) < 0.0001

    def test_pouw_correct_weights(self):
        """PoUW weights should match spec."""
        from app.aggregator import POUW_WEIGHTS
        
        assert POUW_WEIGHTS["accuracy"] == 0.4
        assert POUW_WEIGHTS["omission_risk"] == 0.3
        assert POUW_WEIGHTS["evidence_quality"] == 0.2
        assert POUW_WEIGHTS["governance_relevance"] == 0.1

    def test_pouw_score_range(self):
        """PoUW score should be in [0, 1] range."""
        from app.aggregator import calculate_pouw_composite
        
        # Test with all zeros
        scores_zero = {
            "accuracy": 0.0,
            "omission_risk": 0.0,
            "evidence_quality": 0.0,
            "governance_relevance": 0.0,
        }
        assert calculate_pouw_composite(scores_zero) == 0.0
        
        # Test with all ones
        scores_one = {
            "accuracy": 1.0,
            "omission_risk": 1.0,
            "evidence_quality": 1.0,
            "governance_relevance": 1.0,
        }
        assert calculate_pouw_composite(scores_one) == 1.0


class TestPoICalculation:
    """Test Proof of Inference agreement calculation."""

    def test_poi_perfect_agreement(self):
        """All same verdicts should give 1.0 agreement."""
        from app.aggregator import calculate_poi_agreement
        from app.schemas import MinerResponse, MinerScores
        
        # Create responses with same verdict
        responses = []
        for i in range(5):
            scores = MinerScores(
                accuracy=0.9, omission_risk=0.1, 
                evidence_quality=0.8, governance_relevance=0.9,
                composite=0.8
            )
            responses.append(MinerResponse(
                miner_id=f"miner_{i}",
                claim_id="claim_001",
                verdict="verified",
                rationale="Test",
                evidence_links=[],
                scores=scores,
            ))
        
        agreement = calculate_poi_agreement(responses, "claim_001")
        assert agreement == 1.0

    def test_poi_split_agreement(self):
        """Split verdicts should reflect majority."""
        from app.aggregator import calculate_poi_agreement
        from app.schemas import MinerResponse, MinerScores
        
        responses = []
        verdicts = ["verified", "verified", "verified", "refuted", "partial"]
        
        for i, verdict in enumerate(verdicts):
            scores = MinerScores(
                accuracy=0.9, omission_risk=0.1,
                evidence_quality=0.8, governance_relevance=0.9,
                composite=0.8
            )
            responses.append(MinerResponse(
                miner_id=f"miner_{i}",
                claim_id="claim_001",
                verdict=verdict,
                rationale="Test",
                evidence_links=[],
                scores=scores,
            ))
        
        agreement = calculate_poi_agreement(responses, "claim_001")
        # 3 out of 5 agree = 0.6
        assert agreement == 0.6

    def test_poi_no_responses(self):
        """No responses should give 0.0 agreement."""
        from app.aggregator import calculate_poi_agreement
        
        agreement = calculate_poi_agreement([], "claim_001")
        assert agreement == 0.0


class TestConfidenceInterval:
    """Test confidence interval calculation."""

    def test_ci_single_value(self):
        """Single value should have same lower/upper."""
        from app.aggregator import calculate_confidence_interval
        
        lower, upper = calculate_confidence_interval([0.8])
        assert lower == upper == 0.8

    def test_ci_range(self):
        """CI should be within valid range."""
        from app.aggregator import calculate_confidence_interval
        
        values = [0.7, 0.8, 0.85, 0.9, 0.75]
        lower, upper = calculate_confidence_interval(values)
        
        assert 0 <= lower <= 1
        assert 0 <= upper <= 1
        assert lower <= upper

    def test_ci_empty_list(self):
        """Empty list should return (0, 0)."""
        from app.aggregator import calculate_confidence_interval
        
        lower, upper = calculate_confidence_interval([])
        assert lower == 0.0
        assert upper == 0.0


class TestAggregation:
    """Test full aggregation flow."""

    def test_aggregated_metrics_structure(self):
        """Aggregated metrics should have required fields."""
        from app.schemas import AggregatedMetrics
        
        metrics = AggregatedMetrics(
            poi_agreement=0.9,
            poi_confidence_interval=(0.85, 0.95),
            pouw_score=0.8,
            pouw_confidence_interval=(0.75, 0.85),
            total_miners=5,
            responding_miners=5,
            consensus_verdict="verified",
            claim_coverage=1.0,
        )
        
        assert 0 <= metrics.poi_agreement <= 1
        assert 0 <= metrics.pouw_score <= 1
        assert metrics.total_miners >= metrics.responding_miners
        assert metrics.consensus_verdict in ["verified", "refuted", "unverifiable", "partial"]

    def test_recommendation_structure(self):
        """Recommendation should have required fields."""
        from app.schemas import Recommendation
        
        rec = Recommendation(
            action="approve",
            confidence=0.89,
            risk_flags=[],
            summary="All claims verified with high confidence.",
        )
        
        assert rec.action in ["approve", "reject", "review"]
        assert 0 <= rec.confidence <= 1
        assert isinstance(rec.risk_flags, list)
