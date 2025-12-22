"""
Xea Governance Oracle - Pydantic Schemas

Request/Response schemas for API endpoints.
"""

from datetime import datetime
from typing import Optional, Literal, Dict, List, Any
from pydantic import BaseModel, Field


# ============================================================================
# Claim Schemas
# ============================================================================

class ClaimCanonical(BaseModel):
    """Canonical extracted values from a claim."""
    
    numbers: List[float] = Field(default_factory=list, description="Normalized numeric values (e.g., 10% -> 0.10)")
    addresses: List[str] = Field(default_factory=list, description="Normalized ETH addresses (lowercased)")
    urls: List[str] = Field(default_factory=list, description="Normalized URLs")


class Claim(BaseModel):
    """Atomic claim extracted from a proposal."""

    id: str = Field(..., description="Claim identifier (c1, c2, ...)")
    text: str = Field(..., description="The verbatim claim text extracted from the proposal")
    paragraph_index: int = Field(..., ge=0, description="Zero-indexed paragraph number")
    char_range: List[int] = Field(..., description="Character start and end positions [start, end]")
    type: Literal["factual", "normative", "numeric"] = Field(..., description="Claim type classification")
    canonical: ClaimCanonical = Field(default_factory=ClaimCanonical, description="Canonicalized values")


# ============================================================================
# Ingest Schemas
# ============================================================================

class IngestRequest(BaseModel):
    """Request to ingest a proposal."""

    url: Optional[str] = Field(None, description="URL of the proposal to ingest")
    text: Optional[str] = Field(None, description="Raw text of the proposal")

    def model_post_init(self, __context):
        if not self.url and not self.text:
            raise ValueError("Either 'url' or 'text' must be provided")


class IngestResponse(BaseModel):
    """Response from proposal ingestion."""

    proposal_hash: str = Field(..., description="SHA-256 hash of canonical text with URI")
    canonical_text: str = Field(..., description="Canonicalized proposal text")
    claims: List[Claim] = Field(..., description="Extracted atomic claims")


# ============================================================================
# Miner Schemas
# ============================================================================

class MinerScores(BaseModel):
    """PoUW scoring breakdown for a miner response."""

    accuracy: float = Field(..., ge=0, le=1)
    omission_risk: float = Field(..., ge=0, le=1)
    evidence_quality: float = Field(..., ge=0, le=1)
    governance_relevance: float = Field(..., ge=0, le=1)
    composite: float = Field(..., ge=0, le=1)


class MinerResponse(BaseModel):
    """Response from a single miner for a claim."""

    miner_id: str
    claim_id: str
    verdict: Literal["verified", "refuted", "unverifiable", "partial"]
    rationale: str
    evidence_links: List[str] = Field(default_factory=list)
    embedding: Optional[List[float]] = None
    scores: MinerScores


# ============================================================================
# Validate Schemas
# ============================================================================

class ValidateRequest(BaseModel):
    """Request to start validation job."""

    proposal_hash: str = Field(..., description="Hash of proposal to validate")


class ValidateResponse(BaseModel):
    """Response from validation job creation."""

    job_id: str
    proposal_hash: str
    status: Literal["queued", "running", "completed", "failed"]
    created_at: datetime
    estimated_completion: Optional[datetime] = None


# ============================================================================
# Status Schemas
# ============================================================================

class JobProgress(BaseModel):
    """Progress information for a validation job."""

    claims_total: int
    claims_validated: int
    miners_contacted: int
    miners_responded: int


class StatusResponse(BaseModel):
    """Response for job status query."""

    job_id: str
    status: Literal["queued", "running", "completed", "failed"]
    progress: JobProgress
    partial_results: List[MinerResponse] = Field(default_factory=list)
    started_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    ready_for_aggregation: bool = False


# ============================================================================
# Aggregate Schemas
# ============================================================================

class AggregateRequest(BaseModel):
    """Request to aggregate validation results."""

    job_id: str = Field(..., description="Job ID to aggregate")
    publish: bool = Field(False, description="Whether to publish to IPFS")


class ClaimAggregation(BaseModel):
    """Aggregated results for a single claim."""
    
    id: str
    text: str = ""
    poi_agreement: float = Field(..., ge=0, le=1)
    mode_verdict: str
    embedding_dispersion: float = Field(..., ge=0)
    pouw_mean: float = Field(..., ge=0, le=1)
    pouw_ci_95: List[float] = Field(..., min_length=2, max_length=2)
    outliers: List[str] = Field(default_factory=list)
    final_recommendation: Literal["supported", "disputed", "supported_with_caution"]
    miner_responses: List[Dict[str, Any]] = Field(default_factory=list)


class AggregateResponse(BaseModel):
    """Response from aggregation."""
    
    job_id: str
    evidence_bundle: Dict[str, Any]
    ipfs_cid: Optional[str] = None


# ============================================================================
# Evidence Bundle Schema (matches exact spec)
# ============================================================================

class EvidenceBundle(BaseModel):
    """
    Complete evidence bundle with aggregated results.
    
    Schema:
    {
      "proposal_hash": "<sha256>",
      "job_id": "<job_id>",
      "claims": [...aggregated claim data...],
      "overall_poi_agreement": <float>,
      "overall_pouw_score": <float>,
      "overall_ci_95": [low, high],
      "critical_flags": [...],
      "timestamp": "ISO8601"
    }
    """
    
    proposal_hash: str
    job_id: str
    claims: List[ClaimAggregation]
    overall_poi_agreement: float = Field(..., ge=0, le=1)
    overall_pouw_score: float = Field(..., ge=0, le=1)
    overall_ci_95: List[float] = Field(..., min_length=2, max_length=2)
    critical_flags: List[str] = Field(default_factory=list)
    timestamp: str


# ============================================================================
# Attest Schemas
# ============================================================================

class AttestRequest(BaseModel):
    """Request to create attestation."""

    job_id: str = Field(..., description="Job ID to attest")
    publish: bool = Field(False, description="Whether to publish to IPFS")


class AttestResponse(BaseModel):
    """Response from attestation creation."""

    job_id: str
    proposal_hash: str
    ipfs_cid: Optional[str] = None
    signature: str
    signer: str
    message_hash: str
    verification_instructions: Dict[str, str]


# ============================================================================
# Claims Edit Schemas
# ============================================================================

class ClaimsEditRequest(BaseModel):
    """Request to update claims for a proposal."""
    
    claims: List[Claim] = Field(..., description="Updated claims list")


# ============================================================================
# WebSocket Message Schemas
# ============================================================================

class WSMinerResponseMessage(BaseModel):
    """WebSocket message for miner response."""
    
    type: Literal["miner_response"] = "miner_response"
    job_id: str
    claim_id: str
    miner_response: Dict[str, Any]


class WSAggregateMessage(BaseModel):
    """WebSocket message for aggregation complete."""
    
    type: Literal["aggregate"] = "aggregate"
    job_id: str
    evidence_bundle: Dict[str, Any]


class WSStatusMessage(BaseModel):
    """WebSocket message for job status update."""
    
    type: Literal["status"] = "status"
    job_id: str
    status: str
    progress: Dict[str, int]
