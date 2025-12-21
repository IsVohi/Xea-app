"""
Xea Governance Oracle - Mock Miner

Mock miner for local development and testing.
Simulates decentralized inference responses.
"""

import random
import hashlib
from typing import Optional
from dataclasses import dataclass


@dataclass
class MockMinerConfig:
    """Configuration for mock miner behavior."""

    miner_id: str = "mock_miner_001"
    accuracy_range: tuple[float, float] = (0.7, 0.98)
    delay_range: tuple[float, float] = (0.1, 0.5)
    failure_rate: float = 0.05


class MockMiner:
    """
    Mock miner that simulates validation responses.

    Used for local development and testing without
    connecting to actual Cortensor miners.
    """

    def __init__(self, config: Optional[MockMinerConfig] = None):
        self.config = config or MockMinerConfig()

    def validate_claim(
        self,
        claim_id: str,
        claim_text: str,
        proposal_context: str,
    ) -> dict:
        """
        Simulate claim validation.

        Args:
            claim_id: ID of the claim to validate
            claim_text: Text of the claim
            proposal_context: Full proposal context

        Returns:
            Simulated miner response
        """
        # Simulate occasional failures
        if random.random() < self.config.failure_rate:
            raise Exception("Simulated miner failure")

        # Generate deterministic-ish verdict based on claim
        claim_hash = hashlib.md5(claim_text.encode()).hexdigest()
        verdict_seed = int(claim_hash[:8], 16) % 100

        if verdict_seed < 70:
            verdict = "verified"
        elif verdict_seed < 85:
            verdict = "partial"
        elif verdict_seed < 95:
            verdict = "unverifiable"
        else:
            verdict = "refuted"

        # Generate scores with some variance
        base_accuracy = random.uniform(*self.config.accuracy_range)
        scores = {
            "accuracy": round(base_accuracy, 3),
            "omission_risk": round(random.uniform(0.05, 0.3), 3),
            "evidence_quality": round(random.uniform(0.6, 0.95), 3),
            "governance_relevance": round(random.uniform(0.7, 0.98), 3),
        }

        # Compute composite score
        weights = {
            "accuracy": 0.4,
            "omission_risk": 0.3,
            "evidence_quality": 0.2,
            "governance_relevance": 0.1,
        }
        composite = sum(weights[k] * scores[k] for k in weights)
        scores["composite"] = round(composite, 3)

        return {
            "miner_id": self.config.miner_id,
            "claim_id": claim_id,
            "verdict": verdict,
            "rationale": f"Mock validation of claim: {claim_text[:50]}...",
            "evidence_links": [
                "https://example.com/evidence/mock",
                f"ipfs://Qm{claim_hash[:40]}",
            ],
            "embedding": [random.uniform(-1, 1) for _ in range(10)],
            "scores": scores,
        }


def create_mock_miner_pool(count: int = 5) -> list[MockMiner]:
    """
    Create a pool of mock miners with varying characteristics.

    Args:
        count: Number of miners to create

    Returns:
        List of MockMiner instances
    """
    miners = []
    for i in range(count):
        config = MockMinerConfig(
            miner_id=f"mock_miner_{i:03d}",
            accuracy_range=(0.65 + i * 0.05, 0.90 + i * 0.02),
            failure_rate=0.05 + i * 0.01,
        )
        miners.append(MockMiner(config))
    return miners


# Example usage for testing
if __name__ == "__main__":
    miner = MockMiner()
    response = miner.validate_claim(
        claim_id="claim_001",
        claim_text="The treasury holds 500,000 USDC",
        proposal_context="This is a test proposal...",
    )
    print("Mock response:", response)
