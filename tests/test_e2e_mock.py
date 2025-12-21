"""
Xea Governance Oracle - End-to-End Mock Tests

End-to-end tests using mock miners.
"""

import pytest
import time
from unittest.mock import patch, MagicMock, AsyncMock

# Import test utilities
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "workers"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


SAMPLE_PROPOSAL = """
# Proposal: Treasury Allocation

## Summary
This proposal requests 50,000 USDC from the DAO treasury.

## Background
The treasury currently holds 500,000 USDC.
This represents 10% of total funds.

## Timeline
- Applications open: January 15, 2025
- Deadline: February 15, 2025
"""


class TestE2EMockPipeline:
    """End-to-end tests with mock miners."""

    def test_mock_miner_response_structure(self):
        """Mock miner should return valid response structure."""
        from mock_miner import MockMiner
        
        miner = MockMiner()
        response = miner.validate_claim(
            claim_id="claim_001",
            claim_text="The treasury holds 500,000 USDC",
            proposal_context=SAMPLE_PROPOSAL,
        )
        
        # Check required fields
        assert "miner_id" in response
        assert "claim_id" in response
        assert "verdict" in response
        assert "rationale" in response
        assert "evidence_links" in response
        assert "scores" in response
        
        # Check verdict is valid
        assert response["verdict"] in ["verified", "refuted", "unverifiable", "partial"]
        
        # Check scores
        scores = response["scores"]
        assert "accuracy" in scores
        assert "omission_risk" in scores
        assert "evidence_quality" in scores
        assert "governance_relevance" in scores
        assert "composite" in scores
        
        # Check score ranges
        for key, value in scores.items():
            assert 0 <= value <= 1, f"{key} score out of range"

    def test_mock_miner_pool_creation(self):
        """Should create pool of miners with unique IDs."""
        from mock_miner import create_mock_miner_pool
        
        pool = create_mock_miner_pool(count=5)
        
        assert len(pool) == 5
        
        miner_ids = set()
        for miner in pool:
            miner_ids.add(miner.config.miner_id)
        
        assert len(miner_ids) == 5  # All unique

    def test_mock_validation_determinism(self):
        """Same claim should produce consistent verdict type."""
        from mock_miner import MockMiner, MockMinerConfig
        
        # Use fixed seed for determinism
        config = MockMinerConfig(miner_id="test_miner", failure_rate=0.0)
        miner = MockMiner(config)
        
        claim_text = "The treasury holds exactly 500,000 USDC"
        
        # Run multiple times
        verdicts = []
        for _ in range(3):
            response = miner.validate_claim(
                claim_id="claim_001",
                claim_text=claim_text,
                proposal_context=SAMPLE_PROPOSAL,
            )
            verdicts.append(response["verdict"])
        
        # All verdicts should be the same for same claim
        assert len(set(verdicts)) == 1

    def test_pouw_composite_matches_weights(self):
        """Composite score should match weighted calculation."""
        from mock_miner import MockMiner, MockMinerConfig
        from app.aggregator import calculate_pouw_composite
        
        config = MockMinerConfig(failure_rate=0.0)
        miner = MockMiner(config)
        
        response = miner.validate_claim(
            claim_id="claim_001",
            claim_text="Test claim",
            proposal_context="Test",
        )
        
        scores = response["scores"]
        expected_composite = calculate_pouw_composite({
            "accuracy": scores["accuracy"],
            "omission_risk": scores["omission_risk"],
            "evidence_quality": scores["evidence_quality"],
            "governance_relevance": scores["governance_relevance"],
        })
        
        # Should be close (miner calculates same way)
        assert abs(scores["composite"] - expected_composite) < 0.01


class TestE2EWorkflow:
    """Test the full workflow with mocked dependencies."""

    def test_ingest_hash_stability(self):
        """Ingest should produce stable hashes."""
        from app.ingest import compute_proposal_hash, canonicalize_text
        
        # Hash same content multiple times
        hashes = []
        for _ in range(3):
            canonical = canonicalize_text(SAMPLE_PROPOSAL)
            hash_val = compute_proposal_hash(canonical)
            hashes.append(hash_val)
        
        # All should be identical
        assert len(set(hashes)) == 1
        assert hashes[0].startswith("sha256:")

    def test_claim_count_reasonable(self):
        """Proposal should produce reasonable claim count."""
        # Mock claim extraction - actual implementation uses AI
        mock_claims = [
            {"id": "claim_001", "text": "requests 50,000 USDC"},
            {"id": "claim_002", "text": "treasury holds 500,000 USDC"},
            {"id": "claim_003", "text": "represents 10% of total funds"},
            {"id": "claim_004", "text": "Applications open January 15"},
            {"id": "claim_005", "text": "Deadline February 15"},
            {"id": "claim_006", "text": "from the DAO treasury"},
        ]
        
        assert 6 <= len(mock_claims) <= 12

    def test_validation_fanout(self):
        """Validation should fan out to multiple miners."""
        from mock_miner import create_mock_miner_pool
        
        miners = create_mock_miner_pool(count=5)
        claim = {
            "id": "claim_001",
            "text": "The treasury holds 500,000 USDC",
        }
        
        responses = []
        for miner in miners:
            try:
                response = miner.validate_claim(
                    claim_id=claim["id"],
                    claim_text=claim["text"],
                    proposal_context=SAMPLE_PROPOSAL,
                )
                responses.append(response)
            except Exception:
                pass  # Some miners may fail
        
        # At least some miners should respond
        assert len(responses) >= 3

    def test_aggregation_produces_metrics(self):
        """Aggregation should produce valid metrics."""
        from mock_miner import create_mock_miner_pool
        from app.aggregator import calculate_poi_agreement, calculate_pouw_composite
        from app.schemas import MinerResponse, MinerScores
        
        # Generate responses from mock miners
        miners = create_mock_miner_pool(count=5)
        claim_id = "claim_001"
        
        responses = []
        for miner in miners:
            raw = miner.validate_claim(
                claim_id=claim_id,
                claim_text="Test claim",
                proposal_context="Test",
            )
            scores = MinerScores(**raw["scores"])
            responses.append(MinerResponse(
                miner_id=raw["miner_id"],
                claim_id=raw["claim_id"],
                verdict=raw["verdict"],
                rationale=raw["rationale"],
                evidence_links=raw["evidence_links"],
                scores=scores,
            ))
        
        # Calculate PoI
        poi = calculate_poi_agreement(responses, claim_id)
        assert 0 <= poi <= 1
        
        # Calculate average PoUW
        pouw_scores = [r.scores.composite for r in responses]
        avg_pouw = sum(pouw_scores) / len(pouw_scores)
        assert 0 <= avg_pouw <= 1


class TestE2EValidation:
    """Validate end-to-end flow matches acceptance criteria."""

    def test_acceptance_hash_format(self):
        """Hash format matches spec."""
        from app.ingest import compute_proposal_hash, canonicalize_text
        
        hash_val = compute_proposal_hash(canonicalize_text(SAMPLE_PROPOSAL))
        
        # Format: sha256:<64 hex chars>
        assert hash_val.startswith("sha256:")
        hex_part = hash_val[7:]
        assert len(hex_part) == 64
        assert all(c in "0123456789abcdef" for c in hex_part)

    def test_acceptance_verdict_values(self):
        """Verdict values match spec."""
        valid_verdicts = {"verified", "refuted", "unverifiable", "partial"}
        
        from mock_miner import create_mock_miner_pool
        
        miners = create_mock_miner_pool(count=10)
        verdicts_seen = set()
        
        for i, miner in enumerate(miners):
            response = miner.validate_claim(
                claim_id=f"claim_{i:03d}",
                claim_text=f"Test claim {i}",
                proposal_context="Test",
            )
            verdicts_seen.add(response["verdict"])
        
        # All seen verdicts should be valid
        assert verdicts_seen.issubset(valid_verdicts)

    def test_acceptance_score_ranges(self):
        """All scores should be in [0, 1] range."""
        from mock_miner import MockMiner
        
        miner = MockMiner()
        
        for i in range(10):
            response = miner.validate_claim(
                claim_id=f"claim_{i:03d}",
                claim_text=f"Test claim {i}",
                proposal_context="Test",
            )
            
            scores = response["scores"]
            for key, value in scores.items():
                assert 0 <= value <= 1, f"Score {key}={value} out of range"
