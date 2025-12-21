"""
Xea Governance Oracle - Pydantic Schemas

Request/Response schemas for API endpoints.
"""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field


# ============================================================================
# Claim Schemas
# ============================================================================

class Claim(BaseModel):
    """Atomic claim extracted from a proposal."""

    id: str = Field(..., description="Unique identifier for the claim", pattern=r"^claim_\d{3,}$")
    text: str = Field(..., description="The verbatim claim text extracted from the proposal")
    paragraph_index: int = Field(..., ge=0, description="Zero-indexed paragraph number")
    char_range: tuple[int, int] = Field(..., description="Character start and end positions")
    type: Literal["factual", "mathematical", "temporal", "comparative", "procedural", "conditional"]
    canonical: str = Field(..., description="Normalized identifier for deduplication")


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
    evidence_links: list[str] = Field(default_factory=list)
    embedding: Optional[list[float]] = None
    scores: MinerScores


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

    proposal_hash: str = Field(..., description="SHA-256 hash of canonical text")
    canonical_text: str = Field(..., description="Canonicalized proposal text")
    claims: list[Claim] = Field(..., description="Extracted atomic claims")


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
    partial_results: list[MinerResponse] = Field(default_factory=list)
    started_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    ready_for_aggregation: bool = False


# ============================================================================
# Aggregate Schemas
# ============================================================================

class AggregateRequest(BaseModel):
    """Request to aggregate validation results."""

    job_id: str


class AggregatedMetrics(BaseModel):
    """Aggregated metrics from all miner responses."""

    poi_agreement: float = Field(..., ge=0, le=1, description="Proof of Inference agreement")
    poi_confidence_interval: tuple[float, float]
    pouw_score: float = Field(..., ge=0, le=1, description="Proof of Useful Work score")
    pouw_confidence_interval: tuple[float, float]
    total_miners: int
    responding_miners: int
    consensus_verdict: Literal["verified", "refuted", "unverifiable", "partial"]
    claim_coverage: float = Field(..., ge=0, le=1)


class Recommendation(BaseModel):
    """Governance recommendation based on validation."""

    action: Literal["approve", "reject", "review"]
    confidence: float = Field(..., ge=0, le=1)
    risk_flags: list[str] = Field(default_factory=list)
    summary: str


class EvidenceBundle(BaseModel):
    """Complete evidence bundle with aggregated results."""

    proposal_hash: str
    claims: list[Claim]
    miners: list[MinerResponse]
    aggregated_metrics: AggregatedMetrics
    recommendation: Recommendation
    ipfs_cid: Optional[str] = None
    signature: Optional[str] = None


# ============================================================================
# Attest Schemas
# ============================================================================

class AttestRequest(BaseModel):
    """Request to create attestation."""

    evidence_cid: Optional[str] = None
    bundle: Optional[EvidenceBundle] = None

    def model_post_init(self, __context):
        if not self.evidence_cid and not self.bundle:
            raise ValueError("Either 'evidence_cid' or 'bundle' must be provided")


class AttestResponse(BaseModel):
    """Response from attestation creation."""

    attestation_id: str
    evidence_cid: str
    signature: str
    signer_address: str
    tx_hash: Optional[str] = None
    tx_link: Optional[str] = None
    status: Literal["signed", "submitted", "confirmed"]
    created_at: datetime
