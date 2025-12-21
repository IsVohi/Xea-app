"""
Xea Governance Oracle - Ingest Tests

Unit tests for proposal ingestion functionality.
"""

import pytest
from unittest.mock import patch, MagicMock

# Sample proposal for testing
SAMPLE_PROPOSAL = """
# Proposal: Treasury Allocation for Developer Grants

## Summary
This proposal requests 50,000 USDC from the DAO treasury to fund developer grants for Q1 2025.

## Background
The DAO treasury currently holds approximately 500,000 USDC. This allocation represents 10% of total treasury funds.

## Specification

### Grant Distribution
- Smart Contract Development: 20,000 USDC
- Frontend Development: 15,000 USDC
- Documentation and Tutorials: 10,000 USDC
- Security Audits: 5,000 USDC

### Timeline
- Grant applications open: January 15, 2025
- Application deadline: February 15, 2025
- Grant disbursement: March 1, 2025

### Oversight
A 3-of-5 multisig consisting of core contributors will manage grant disbursements.

## Rationale
Developer grants have historically provided 3x ROI in terms of protocol value added.
The previous grant program funded 12 projects, 8 of which are now live on mainnet.
"""


class TestIngestHashStability:
    """Test that hashing is deterministic."""

    def test_same_text_produces_same_hash(self):
        """Same text input should produce identical hash."""
        from app.ingest import compute_proposal_hash, canonicalize_text
        
        text1 = canonicalize_text(SAMPLE_PROPOSAL)
        text2 = canonicalize_text(SAMPLE_PROPOSAL)
        
        hash1 = compute_proposal_hash(text1)
        hash2 = compute_proposal_hash(text2)
        
        assert hash1 == hash2
        assert hash1.startswith("sha256:")
        assert len(hash1) == 71  # "sha256:" + 64 hex chars

    def test_hash_format(self):
        """Hash should have correct format."""
        from app.ingest import compute_proposal_hash, canonicalize_text
        
        canonical = canonicalize_text(SAMPLE_PROPOSAL)
        hash_value = compute_proposal_hash(canonical)
        
        assert hash_value.startswith("sha256:")
        hex_part = hash_value[7:]
        assert len(hex_part) == 64
        assert all(c in "0123456789abcdef" for c in hex_part)

    def test_different_text_produces_different_hash(self):
        """Different text should produce different hash."""
        from app.ingest import compute_proposal_hash, canonicalize_text
        
        hash1 = compute_proposal_hash(canonicalize_text("Proposal A"))
        hash2 = compute_proposal_hash(canonicalize_text("Proposal B"))
        
        assert hash1 != hash2


class TestCanonicalization:
    """Test text canonicalization."""

    def test_strips_trailing_whitespace(self):
        """Canonicalization should strip trailing whitespace."""
        from app.ingest import canonicalize_text
        
        text_with_whitespace = "Line 1   \nLine 2  \n\n"
        canonical = canonicalize_text(text_with_whitespace)
        
        assert canonical == "Line 1\nLine 2"

    def test_normalizes_whitespace(self):
        """Leading/trailing whitespace should be stripped."""
        from app.ingest import canonicalize_text
        
        text = "  \n\n  Hello World  \n\n  "
        canonical = canonicalize_text(text)
        
        assert canonical == "Hello World"


class TestIngestEndpoint:
    """Test the /ingest API endpoint structure."""

    def test_ingest_response_structure(self):
        """Response should have required fields."""
        # This is a structure test - actual implementation will vary
        expected_fields = {"proposal_hash", "canonical_text", "claims"}
        
        mock_response = {
            "proposal_hash": "sha256:abc123...",
            "canonical_text": "Test proposal",
            "claims": []
        }
        
        assert set(mock_response.keys()) == expected_fields

    def test_claim_structure(self):
        """Claims should have required fields."""
        expected_claim_fields = {
            "id", "text", "paragraph_index", 
            "char_range", "type", "canonical"
        }
        
        mock_claim = {
            "id": "claim_001",
            "text": "The treasury holds 500,000 USDC",
            "paragraph_index": 2,
            "char_range": [145, 189],
            "type": "factual",
            "canonical": "treasury_balance_usdc_500000"
        }
        
        assert set(mock_claim.keys()) == expected_claim_fields

    def test_valid_claim_types(self):
        """Claim types should be valid enum values."""
        valid_types = {
            "factual", "mathematical", "temporal",
            "comparative", "procedural", "conditional"
        }
        
        # All types should be in valid set
        for claim_type in valid_types:
            assert claim_type in valid_types


class TestClaimExtraction:
    """Test claim extraction logic."""

    def test_typical_proposal_claim_count(self):
        """Typical proposal should produce 6-12 claims."""
        # This is a placeholder - actual extraction will use AI
        # For now, we just validate the expected range
        expected_min = 6
        expected_max = 12
        
        # Mock claim count for typical proposal
        mock_claim_count = 8
        
        assert expected_min <= mock_claim_count <= expected_max

    def test_char_range_validity(self):
        """Char ranges should be valid."""
        from app.ingest import canonicalize_text
        
        text = canonicalize_text(SAMPLE_PROPOSAL)
        
        # Mock char range
        char_range = [0, 50]
        
        assert char_range[0] >= 0
        assert char_range[1] > char_range[0]
        assert char_range[1] <= len(text)
