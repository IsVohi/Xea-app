"""
Xea Governance Oracle - API Routes

FastAPI router with all API endpoints.
"""

import json
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import HTMLResponse
from typing import Optional

from app.schemas import (
    IngestRequest,
    IngestResponse,
    ValidateRequest,
    ValidateResponse,
    StatusResponse,
    AggregateRequest,
    EvidenceBundle,
    AttestRequest,
    AttestResponse,
    Claim,
    ClaimCanonical,
    ClaimsEditRequest,
)
from app.ingest import process_ingest, load_claims, persist_claims, get_data_dir

router = APIRouter()


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
    
    Args:
        proposal_hash: The proposal hash (with or without sha256: prefix)
        
    Returns:
        Claims data for the proposal
    """
    # Normalize hash format
    if not proposal_hash.startswith("sha256:"):
        proposal_hash = f"sha256:{proposal_hash}"
    
    data = load_claims(proposal_hash)
    if not data:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    return data


@router.get("/claims/{proposal_hash}/edit", response_class=HTMLResponse)
async def edit_claims_form(proposal_hash: str):
    """
    Get HTML form for editing claims.
    
    This is a simple fallback UI for manually correcting ambiguous claims.
    
    Args:
        proposal_hash: The proposal hash
        
    Returns:
        HTML form for editing claims
    """
    # Normalize hash format
    if not proposal_hash.startswith("sha256:"):
        proposal_hash = f"sha256:{proposal_hash}"
    
    data = load_claims(proposal_hash)
    if not data:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    claims = data.get("claims", [])
    canonical_text = data.get("canonical_text", "")
    
    # Build HTML form
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Edit Claims - Xea</title>
    <style>
        :root {{
            --bg: #0a0a0f;
            --bg-card: #1a1a24;
            --text: #ffffff;
            --text-muted: #a0a0b0;
            --accent: #6366f1;
            --border: #2a2a3a;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Inter', -apple-system, sans-serif;
            background: var(--bg);
            color: var(--text);
            padding: 2rem;
            line-height: 1.6;
        }}
        h1 {{ color: var(--accent); margin-bottom: 1rem; }}
        .hash {{ font-size: 0.875rem; color: var(--text-muted); word-break: break-all; margin-bottom: 2rem; }}
        .proposal-text {{
            background: var(--bg-card);
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 2rem;
            max-height: 200px;
            overflow-y: auto;
            white-space: pre-wrap;
            font-size: 0.875rem;
            border: 1px solid var(--border);
        }}
        .claim {{
            background: var(--bg-card);
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1rem;
            border: 1px solid var(--border);
        }}
        .claim-header {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 0.5rem;
        }}
        .claim-id {{ font-weight: bold; color: var(--accent); }}
        .claim-type {{
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
            background: var(--border);
        }}
        label {{ display: block; margin-bottom: 0.25rem; color: var(--text-muted); font-size: 0.875rem; }}
        textarea, input, select {{
            width: 100%;
            padding: 0.5rem;
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: 4px;
            color: var(--text);
            font-size: 0.875rem;
            margin-bottom: 0.5rem;
        }}
        textarea {{ min-height: 80px; resize: vertical; }}
        .btn {{
            padding: 0.75rem 1.5rem;
            background: var(--accent);
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1rem;
            font-weight: 600;
        }}
        .btn:hover {{ opacity: 0.9; }}
        .btn-delete {{
            background: #ef4444;
            padding: 0.5rem;
            font-size: 0.875rem;
        }}
        .actions {{ margin-top: 2rem; display: flex; gap: 1rem; }}
        .success {{ color: #22c55e; margin-top: 1rem; }}
        .error {{ color: #ef4444; margin-top: 1rem; }}
    </style>
</head>
<body>
    <h1>🔮 Edit Claims</h1>
    <p class="hash"><strong>Proposal Hash:</strong> {proposal_hash}</p>
    
    <details>
        <summary style="cursor: pointer; margin-bottom: 1rem;">View Canonical Text</summary>
        <div class="proposal-text">{canonical_text[:2000]}{'...' if len(canonical_text) > 2000 else ''}</div>
    </details>
    
    <form id="claims-form">
        <input type="hidden" name="proposal_hash" value="{proposal_hash}">
        
        <div id="claims-container">
"""
    
    for i, claim in enumerate(claims):
        claim_type = claim.get("type", "factual")
        canonical = claim.get("canonical", {})
        numbers = canonical.get("numbers", [])
        addresses = canonical.get("addresses", [])
        
        html += f"""
            <div class="claim" data-index="{i}">
                <div class="claim-header">
                    <span class="claim-id">{claim.get('id', f'c{i+1}')}</span>
                    <select name="claims[{i}][type]">
                        <option value="factual" {'selected' if claim_type == 'factual' else ''}>factual</option>
                        <option value="numeric" {'selected' if claim_type == 'numeric' else ''}>numeric</option>
                        <option value="normative" {'selected' if claim_type == 'normative' else ''}>normative</option>
                    </select>
                </div>
                <input type="hidden" name="claims[{i}][id]" value="{claim.get('id', f'c{i+1}')}">
                <input type="hidden" name="claims[{i}][paragraph_index]" value="{claim.get('paragraph_index', 0)}">
                <input type="hidden" name="claims[{i}][char_range]" value="{json.dumps(claim.get('char_range', [0, 0]))}">
                
                <label>Claim Text</label>
                <textarea name="claims[{i}][text]">{claim.get('text', '')}</textarea>
                
                <label>Canonical Numbers (comma-separated)</label>
                <input type="text" name="claims[{i}][canonical_numbers]" value="{', '.join(str(n) for n in numbers)}">
                
                <label>Canonical Addresses (comma-separated)</label>
                <input type="text" name="claims[{i}][canonical_addresses]" value="{', '.join(addresses)}">
                
                <button type="button" class="btn btn-delete" onclick="this.closest('.claim').remove()">Delete Claim</button>
            </div>
"""
    
    html += f"""
        </div>
        
        <div class="actions">
            <button type="submit" class="btn">💾 Save Changes</button>
            <button type="button" class="btn" onclick="addClaim()">➕ Add Claim</button>
        </div>
        
        <div id="message"></div>
    </form>
    
    <script>
        let claimCount = {len(claims)};
        
        function addClaim() {{
            claimCount++;
            const container = document.getElementById('claims-container');
            const div = document.createElement('div');
            div.className = 'claim';
            div.innerHTML = `
                <div class="claim-header">
                    <span class="claim-id">c${{claimCount}}</span>
                    <select name="claims[${{claimCount-1}}][type]">
                        <option value="factual">factual</option>
                        <option value="numeric">numeric</option>
                        <option value="normative">normative</option>
                    </select>
                </div>
                <input type="hidden" name="claims[${{claimCount-1}}][id]" value="c${{claimCount}}">
                <input type="hidden" name="claims[${{claimCount-1}}][paragraph_index]" value="0">
                <input type="hidden" name="claims[${{claimCount-1}}][char_range]" value="[0, 0]">
                
                <label>Claim Text</label>
                <textarea name="claims[${{claimCount-1}}][text]"></textarea>
                
                <label>Canonical Numbers (comma-separated)</label>
                <input type="text" name="claims[${{claimCount-1}}][canonical_numbers]" value="">
                
                <label>Canonical Addresses (comma-separated)</label>
                <input type="text" name="claims[${{claimCount-1}}][canonical_addresses]" value="">
                
                <button type="button" class="btn btn-delete" onclick="this.closest('.claim').remove()">Delete Claim</button>
            `;
            container.appendChild(div);
        }}
        
        document.getElementById('claims-form').addEventListener('submit', async (e) => {{
            e.preventDefault();
            const formData = new FormData(e.target);
            const claims = [];
            
            document.querySelectorAll('.claim').forEach((claimDiv, i) => {{
                const id = claimDiv.querySelector('[name*="[id]"]').value;
                const text = claimDiv.querySelector('textarea').value;
                const type = claimDiv.querySelector('select').value;
                const paraIndex = parseInt(claimDiv.querySelector('[name*="[paragraph_index]"]').value) || 0;
                const charRange = JSON.parse(claimDiv.querySelector('[name*="[char_range]"]').value || '[0,0]');
                const numbers = claimDiv.querySelector('[name*="[canonical_numbers]"]').value
                    .split(',').map(s => parseFloat(s.trim())).filter(n => !isNaN(n));
                const addresses = claimDiv.querySelector('[name*="[canonical_addresses]"]').value
                    .split(',').map(s => s.trim().toLowerCase()).filter(s => s);
                
                claims.push({{
                    id,
                    text,
                    paragraph_index: paraIndex,
                    char_range: charRange,
                    type,
                    canonical: {{ numbers, addresses, urls: [] }}
                }});
            }});
            
            try {{
                const response = await fetch('/claims/{proposal_hash.replace("sha256:", "")}', {{
                    method: 'PUT',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ claims }})
                }});
                
                if (response.ok) {{
                    document.getElementById('message').innerHTML = '<p class="success">✓ Claims saved successfully!</p>';
                }} else {{
                    const data = await response.json();
                    document.getElementById('message').innerHTML = `<p class="error">Error: ${{data.detail}}</p>`;
                }}
            }} catch (err) {{
                document.getElementById('message').innerHTML = `<p class="error">Error: ${{err.message}}</p>`;
            }}
        }});
    </script>
</body>
</html>
"""
    
    return html


@router.put("/claims/{proposal_hash}")
async def update_claims(proposal_hash: str, request: ClaimsEditRequest):
    """
    Update claims for a proposal.
    
    Args:
        proposal_hash: The proposal hash
        request: Updated claims
        
    Returns:
        Success message
    """
    # Normalize hash format
    if not proposal_hash.startswith("sha256:"):
        proposal_hash = f"sha256:{proposal_hash}"
    
    data = load_claims(proposal_hash)
    if not data:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    canonical_text = data.get("canonical_text", "")
    
    # Persist updated claims
    persist_claims(proposal_hash, request.claims, canonical_text)
    
    return {"status": "success", "message": "Claims updated successfully"}


@router.post("/validate", response_model=ValidateResponse)
async def validate_proposal(request: ValidateRequest) -> ValidateResponse:
    """
    Start an asynchronous validation job for a proposal.

    The job fans out claims to multiple miners for independent validation.

    Returns:
        ValidateResponse with job_id and initial status
    """
    # TODO: Implement validation job creation
    # - Create job in Redis
    # - Enqueue validation tasks for workers
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.get("/status/{job_id}", response_model=StatusResponse)
async def get_job_status(job_id: str) -> StatusResponse:
    """
    Get the current status and partial results of a validation job.

    Args:
        job_id: The job identifier returned by /validate

    Returns:
        StatusResponse with progress and partial results
    """
    # TODO: Implement job status retrieval
    # - Fetch job state from Redis
    # - Return progress and partial results
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.post("/aggregate", response_model=EvidenceBundle)
async def aggregate_results(request: AggregateRequest) -> EvidenceBundle:
    """
    Aggregate miner responses into a final evidence bundle.

    Computes PoI agreement and PoUW scores with confidence intervals.

    Args:
        request: AggregateRequest with job_id

    Returns:
        EvidenceBundle with aggregated metrics and recommendation
    """
    # TODO: Implement aggregation logic
    # - Fetch all miner responses for job
    # - Compute PoI agreement
    # - Compute PoUW scores
    # - Generate recommendation
    # - Optionally upload to IPFS
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.post("/attest", response_model=AttestResponse)
async def create_attestation(request: AttestRequest) -> AttestResponse:
    """
    Create an on-chain attestation for an evidence bundle.

    Signs the evidence bundle and optionally submits to blockchain.

    Args:
        request: AttestRequest with evidence_cid or bundle

    Returns:
        AttestResponse with signature and optional tx_hash
    """
    # TODO: Implement attestation logic
    # - Sign evidence bundle hash
    # - Optionally submit to blockchain
    raise HTTPException(status_code=501, detail="Not implemented yet")
