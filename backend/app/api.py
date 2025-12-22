"""
Xea Governance Oracle - API Routes

FastAPI router with all API endpoints.
"""

import json
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse
from typing import Optional, List

from app.schemas import (
    IngestRequest,
    IngestResponse,
    ValidateRequest,
    ValidateResponse,
    StatusResponse,
    JobProgress,
    AggregateRequest,
    AggregateResponse,
    AttestRequest,
    AttestResponse,
    Claim,
    ClaimCanonical,
    ClaimsEditRequest,
    MinerResponse,
    MinerScores,
)
from app.ingest import process_ingest, load_claims, persist_claims, get_data_dir
from app.utils import generate_job_id
from app.workers import job_state, validate_claims_job
from app.aggregator import aggregate_job, load_evidence_bundle
from app.attest import create_attestation as attest_create_attestation

router = APIRouter()


# ============================================================================
# Ingest Endpoints
# ============================================================================

@router.post("/ingest", response_model=IngestResponse)
async def ingest_proposal(request: IngestRequest) -> IngestResponse:
    """
    Ingest a DAO proposal from URL or raw text and extract atomic claims.

    Returns:
        IngestResponse with proposal_hash, canonical_text, and extracted claims
    """
    try:
        result = await process_ingest(request)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.get("/claims/{proposal_hash}")
async def get_claims(proposal_hash: str):
    """
    Get claims for a proposal by hash.
    """
    if not proposal_hash.startswith("sha256:"):
        proposal_hash = f"sha256:{proposal_hash}"
    
    data = load_claims(proposal_hash)
    if not data:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    return data


@router.get("/claims/{proposal_hash}/edit", response_class=HTMLResponse)
async def edit_claims_form(proposal_hash: str):
    """Get HTML form for editing claims."""
    if not proposal_hash.startswith("sha256:"):
        proposal_hash = f"sha256:{proposal_hash}"
    
    data = load_claims(proposal_hash)
    if not data:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    claims = data.get("claims", [])
    canonical_text = data.get("canonical_text", "")
    
    # Build simplified HTML form
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Edit Claims - Xea</title>
    <style>
        body {{ font-family: system-ui; background: #0a0a0f; color: #fff; padding: 2rem; }}
        h1 {{ color: #6366f1; }}
        .claim {{ background: #1a1a24; padding: 1rem; border-radius: 8px; margin: 1rem 0; }}
        textarea, input, select {{ width: 100%; padding: 0.5rem; margin: 0.25rem 0; background: #0a0a0f; border: 1px solid #2a2a3a; color: #fff; border-radius: 4px; }}
        .btn {{ padding: 0.75rem 1.5rem; background: #6366f1; color: white; border: none; border-radius: 8px; cursor: pointer; margin: 0.5rem 0; }}
    </style>
</head>
<body>
    <h1>Edit Claims</h1>
    <p>Proposal Hash: {proposal_hash}</p>
    <form id="form">
        {"".join(f'''
        <div class="claim">
            <strong>{c.get("id")}</strong>
            <select name="type_{i}"><option value="factual" {"selected" if c.get("type")=="factual" else ""}>factual</option><option value="numeric" {"selected" if c.get("type")=="numeric" else ""}>numeric</option></select>
            <textarea name="text_{i}">{c.get("text", "")}</textarea>
        </div>''' for i, c in enumerate(claims))}
        <button type="submit" class="btn">Save</button>
    </form>
    <script>
        document.getElementById('form').onsubmit = async (e) => {{
            e.preventDefault();
            const claims = [];
            document.querySelectorAll('.claim').forEach((el, i) => {{
                claims.push({{
                    id: 'c' + (i+1),
                    text: el.querySelector('textarea').value,
                    type: el.querySelector('select').value,
                    paragraph_index: 0,
                    char_range: [0, 0],
                    canonical: {{numbers: [], addresses: [], urls: []}}
                }});
            }});
            await fetch('/claims/{proposal_hash.replace("sha256:", "")}', {{
                method: 'PUT',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{claims}})
            }});
            alert('Saved!');
        }};
    </script>
</body>
</html>"""
    return html


@router.put("/claims/{proposal_hash}")
async def update_claims(proposal_hash: str, request: ClaimsEditRequest):
    """Update claims for a proposal."""
    if not proposal_hash.startswith("sha256:"):
        proposal_hash = f"sha256:{proposal_hash}"
    
    data = load_claims(proposal_hash)
    if not data:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    persist_claims(proposal_hash, request.claims, data.get("canonical_text", ""))
    return {"status": "success"}


# ============================================================================
# Validation Endpoints
# ============================================================================

def _run_validation_background(proposal_hash: str, job_id: str):
    """Background task to run validation."""
    try:
        validate_claims_job(proposal_hash, job_id=job_id)
    except Exception as e:
        import logging
        logging.error(f"Background validation failed: {e}")


@router.post("/validate", response_model=ValidateResponse)
async def validate_proposal(
    request: ValidateRequest,
    background_tasks: BackgroundTasks,
) -> ValidateResponse:
    """
    Start an asynchronous validation job for a proposal.
    """
    # Normalize hash
    proposal_hash = request.proposal_hash
    if not proposal_hash.startswith("sha256:"):
        proposal_hash = f"sha256:{proposal_hash}"
    
    # Check proposal exists
    claims_data = load_claims(proposal_hash)
    if not claims_data:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    claims = claims_data.get("claims", [])
    if not claims:
        raise HTTPException(status_code=400, detail="No claims to validate")
    
    # Create job
    job_id = generate_job_id()
    job_state.create_job(job_id, proposal_hash, claims)
    
    # Start background validation
    background_tasks.add_task(_run_validation_background, proposal_hash, job_id)
    
    return ValidateResponse(
        job_id=job_id,
        proposal_hash=proposal_hash,
        status="queued",
        created_at=datetime.now(timezone.utc),
        estimated_completion=None,
    )


@router.get("/status/{job_id}", response_model=StatusResponse)
async def get_job_status(job_id: str) -> StatusResponse:
    """
    Get the current status and partial results of a validation job.
    """
    job_data = job_state.get_job(job_id)
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Build progress
    progress = JobProgress(
        claims_total=job_data.get("claims_total", 0),
        claims_validated=job_data.get("claims_validated", 0),
        miners_contacted=job_data.get("miners_contacted", 0),
        miners_responded=job_data.get("miners_responded", 0),
    )
    
    # Parse responses into MinerResponse models
    partial_results = []
    responses = job_data.get("responses", {})
    for claim_id, claim_responses in responses.items():
        for resp in claim_responses:
            try:
                scores_data = resp.get("scores", {})
                scores = MinerScores(
                    accuracy=scores_data.get("accuracy", 0),
                    omission_risk=scores_data.get("omission_risk", 0),
                    evidence_quality=scores_data.get("evidence_quality", 0),
                    governance_relevance=scores_data.get("governance_relevance", 0),
                    composite=scores_data.get("composite", 0),
                )
                partial_results.append(MinerResponse(
                    miner_id=resp.get("miner_id", "unknown"),
                    claim_id=resp.get("claim_id", claim_id),
                    verdict=resp.get("verdict", "unverifiable"),
                    rationale=resp.get("rationale", ""),
                    evidence_links=resp.get("evidence_links", []),
                    embedding=resp.get("embedding"),
                    scores=scores,
                ))
            except Exception:
                pass
    
    # Parse datetime fields
    started_at = None
    updated_at = None
    completed_at = None
    
    if job_data.get("started_at"):
        try:
            started_at = datetime.fromisoformat(job_data["started_at"])
        except (ValueError, TypeError):
            pass
    
    if job_data.get("completed_at"):
        try:
            completed_at = datetime.fromisoformat(job_data["completed_at"])
        except (ValueError, TypeError):
            pass
    
    status = job_data.get("status", "unknown")
    ready_for_aggregation = status == "completed" and len(partial_results) > 0
    
    return StatusResponse(
        job_id=job_id,
        status=status,
        progress=progress,
        partial_results=partial_results,
        started_at=started_at,
        updated_at=updated_at,
        completed_at=completed_at,
        ready_for_aggregation=ready_for_aggregation,
    )


# ============================================================================
# Aggregation & Evidence Endpoints
# ============================================================================

@router.post("/aggregate", response_model=AggregateResponse)
async def aggregate_results(request: AggregateRequest) -> AggregateResponse:
    """
    Aggregate miner responses into a final evidence bundle.
    
    This endpoint:
    1. Loads raw miner responses for the job
    2. Computes per-claim PoI and PoUW metrics
    3. Detects outliers via Mahalanobis distance
    4. Generates critical flags
    5. Saves and returns the evidence bundle
    """
    job_id = request.job_id
    
    # Check job exists
    job_data = job_state.get_job(job_id)
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check job is completed
    if job_data.get("status") != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job not ready for aggregation. Status: {job_data.get('status')}"
        )
    
    # Run aggregation
    bundle = aggregate_job(job_id)
    if not bundle:
        raise HTTPException(status_code=500, detail="Aggregation failed")
    
    # Optionally publish to IPFS
    ipfs_cid = None
    if request.publish:
        from app.attest import publish_bundle_dict
        ipfs_cid = publish_bundle_dict(bundle)
    
    return AggregateResponse(
        job_id=job_id,
        evidence_bundle=bundle,
        ipfs_cid=ipfs_cid,
    )


@router.get("/evidence/{job_id}")
async def get_evidence_bundle(job_id: str):
    """
    Get a saved evidence bundle by job ID.
    """
    bundle = load_evidence_bundle(job_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="Evidence bundle not found")
    
    return bundle


# ============================================================================
# Attestation Endpoints
# ============================================================================

@router.post("/attest", response_model=AttestResponse)
async def create_attestation(request: AttestRequest) -> AttestResponse:
    """
    Create an on-chain attestation for an evidence bundle.
    
    This endpoint:
    1. Loads the evidence bundle for the job
    2. Signs it with ECDSA (or mock if no key configured)
    3. Optionally publishes to IPFS
    4. Returns signature and verification instructions
    """
    job_id = request.job_id
    
    # Load evidence bundle
    bundle = load_evidence_bundle(job_id)
    if not bundle:
        # Try to aggregate first
        bundle = aggregate_job(job_id)
        if not bundle:
            raise HTTPException(status_code=404, detail="Evidence bundle not found")
    
    # Create attestation
    attestation = attest_create_attestation(bundle, publish=request.publish)
    
    return AttestResponse(
        job_id=job_id,
        proposal_hash=bundle.get("proposal_hash", ""),
        ipfs_cid=attestation.get("ipfs_cid"),
        signature=attestation["signature"],
        signer=attestation["signer"],
        message_hash=attestation["message_hash"],
        verification_instructions=attestation["verification_instructions"],
    )
