"""
Xea Governance Oracle - Worker Jobs

RQ worker job definitions for background processing.
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from redis import Redis

from app.config import settings
from app.ingest import load_claims
from app.miner_client import create_miner_clients, MinerClient
from app.schemas import Claim, ClaimCanonical, MinerResponse
from app.utils import generate_job_id

logger = logging.getLogger(__name__)

# Configure structured JSON logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='{"time":"%(asctime)s","level":"%(levelname)s","message":"%(message)s","module":"%(module)s"}',
)


# Data directory for job responses
def get_responses_dir() -> Path:
    """Get the responses data directory."""
    responses_dir = Path(settings.data_dir) / "responses"
    if not responses_dir.exists():
        # Fallback to local directory
        responses_dir = Path(__file__).parent.parent.parent / "data" / "responses"
    responses_dir.mkdir(parents=True, exist_ok=True)
    return responses_dir


def get_jobs_dir() -> Path:
    """Get the jobs data directory."""
    jobs_dir = Path(settings.data_dir) / "jobs"
    if not jobs_dir.exists():
        jobs_dir = Path(__file__).parent.parent.parent / "data" / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    return jobs_dir


# ============================================================================
# Job State Management
# ============================================================================

class JobStateManager:
    """Manage job state in Redis and file system."""
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.redis_url
        self._redis: Optional[Redis] = None
    
    @property
    def redis(self) -> Redis:
        if self._redis is None:
            self._redis = Redis.from_url(self.redis_url, decode_responses=True)
        return self._redis
    
    def create_job(self, job_id: str, proposal_hash: str, claims: List[dict]) -> dict:
        """Create a new job record."""
        job_data = {
            "job_id": job_id,
            "proposal_hash": proposal_hash,
            "status": "queued",
            "claims_total": len(claims),
            "claims_validated": 0,
            "miners_contacted": 0,
            "miners_responded": 0,
            "created_at": datetime.utcnow().isoformat(),
            "started_at": None,
            "completed_at": None,
            "claim_ids": [c.get("id", f"c{i+1}") for i, c in enumerate(claims)],
            "responses": {},  # claim_id -> [responses]
        }
        
        # Store in Redis
        self.redis.hset(f"job:{job_id}", mapping={
            k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) if v is not None else ""
            for k, v in job_data.items()
        })
        self.redis.expire(f"job:{job_id}", 86400)  # 24h TTL
        
        # Also persist to file for durability
        self._save_job_to_file(job_id, job_data)
        
        return job_data
    
    def get_job(self, job_id: str) -> Optional[dict]:
        """Get job data from Redis or file."""
        # Try Redis first
        data = self.redis.hgetall(f"job:{job_id}")
        if data:
            return self._parse_job_data(data)
        
        # Fallback to file
        return self._load_job_from_file(job_id)
    
    def update_job(self, job_id: str, updates: dict):
        """Update job fields."""
        for key, value in updates.items():
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            elif value is None:
                value = ""
            else:
                value = str(value)
            self.redis.hset(f"job:{job_id}", key, value)
        
        # Sync to file
        job_data = self.get_job(job_id)
        if job_data:
            self._save_job_to_file(job_id, job_data)
    
    def add_response(self, job_id: str, claim_id: str, response: dict):
        """Add a miner response for a claim."""
        job_data = self.get_job(job_id)
        if not job_data:
            return
        
        responses = job_data.get("responses", {})
        if claim_id not in responses:
            responses[claim_id] = []
        responses[claim_id].append(response)
        
        # Update counts
        miners_responded = sum(len(r) for r in responses.values())
        
        self.update_job(job_id, {
            "responses": responses,
            "miners_responded": miners_responded,
        })
        
        # Also append to raw responses file
        self._append_raw_response(job_id, claim_id, response)
    
    def _parse_job_data(self, data: dict) -> dict:
        """Parse job data from Redis strings."""
        parsed = {}
        for key, value in data.items():
            if key in ("claims_total", "claims_validated", "miners_contacted", "miners_responded"):
                parsed[key] = int(value) if value else 0
            elif key in ("claim_ids", "responses"):
                try:
                    parsed[key] = json.loads(value) if value else ([] if key == "claim_ids" else {})
                except json.JSONDecodeError:
                    parsed[key] = [] if key == "claim_ids" else {}
            else:
                parsed[key] = value if value else None
        return parsed
    
    def _save_job_to_file(self, job_id: str, job_data: dict):
        """Save job data to JSON file."""
        jobs_dir = get_jobs_dir()
        file_path = jobs_dir / f"{job_id}.json"
        with open(file_path, "w") as f:
            json.dump(job_data, f, indent=2, default=str)
    
    def _load_job_from_file(self, job_id: str) -> Optional[dict]:
        """Load job data from JSON file."""
        jobs_dir = get_jobs_dir()
        file_path = jobs_dir / f"{job_id}.json"
        if not file_path.exists():
            return None
        with open(file_path, "r") as f:
            return json.load(f)
    
    def _append_raw_response(self, job_id: str, claim_id: str, response: dict):
        """Append raw response to audit file."""
        responses_dir = get_responses_dir()
        file_path = responses_dir / f"{job_id}.json"
        
        # Load existing or create new
        if file_path.exists():
            with open(file_path, "r") as f:
                raw_data = json.load(f)
        else:
            raw_data = {"job_id": job_id, "responses": []}
        
        raw_data["responses"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "claim_id": claim_id,
            "response": response,
        })
        
        with open(file_path, "w") as f:
            json.dump(raw_data, f, indent=2, default=str)


# Global job state manager
job_state = JobStateManager()


# ============================================================================
# Validation Worker Jobs
# ============================================================================

async def _validate_single_claim(
    claim: Claim,
    proposal_hash: str,
    miners: List[MinerClient],
    job_id: str,
    timeout: float,
    min_quorum: int,
) -> List[MinerResponse]:
    """
    Validate a single claim across multiple miners.
    
    Waits for:
    - All N responses, OR
    - Timeout, OR
    - min_quorum responses
    """
    tasks = []
    for miner in miners:
        task = asyncio.create_task(
            miner.validate_claim(claim, proposal_hash)
        )
        tasks.append(task)
    
    responses = []
    start_time = time.time()
    remaining_timeout = timeout
    
    # Wait for quorum or timeout
    pending = set(tasks)
    
    while pending and len(responses) < min_quorum and remaining_timeout > 0:
        done, pending = await asyncio.wait(
            pending,
            timeout=min(1.0, remaining_timeout),
            return_when=asyncio.FIRST_COMPLETED,
        )
        
        for task in done:
            try:
                response = task.result()
                responses.append(response)
                
                # Log response
                logger.info(
                    f"Miner response received",
                    extra={
                        "job_id": job_id,
                        "claim_id": claim.id,
                        "miner_id": response.miner_id,
                        "verdict": response.verdict,
                        "elapsed_ms": round((time.time() - start_time) * 1000),
                    }
                )
                
                # Persist response
                job_state.add_response(job_id, claim.id, response.model_dump())
                
            except Exception as e:
                logger.error(f"Miner task failed: {e}")
        
        remaining_timeout = timeout - (time.time() - start_time)
    
    # Cancel any remaining tasks
    for task in pending:
        task.cancel()
    
    return responses


async def _run_validation_async(
    job_id: str,
    proposal_hash: str,
    claims: List[Claim],
) -> dict:
    """Run the async validation loop."""
    settings_obj = settings
    
    # Create miners
    miners = create_miner_clients(
        count=settings_obj.miner_count,
        use_mock=settings_obj.use_mock_miners,
    )
    
    # Update job - started
    job_state.update_job(job_id, {
        "status": "running",
        "started_at": datetime.utcnow().isoformat(),
        "miners_contacted": len(miners) * len(claims),
    })
    
    logger.info(
        f"Starting validation",
        extra={
            "job_id": job_id,
            "claims_count": len(claims),
            "miners_count": len(miners),
        }
    )
    
    # Validate each claim
    all_responses = {}
    claims_validated = 0
    
    for claim in claims:
        logger.info(f"Validating claim {claim.id}")
        
        responses = await _validate_single_claim(
            claim=claim,
            proposal_hash=proposal_hash,
            miners=miners,
            job_id=job_id,
            timeout=settings_obj.miner_timeout_seconds,
            min_quorum=settings_obj.miner_quorum,
        )
        
        all_responses[claim.id] = [r.model_dump() for r in responses]
        claims_validated += 1
        
        # Update progress
        job_state.update_job(job_id, {
            "claims_validated": claims_validated,
        })
    
    # Mark complete
    job_state.update_job(job_id, {
        "status": "completed",
        "completed_at": datetime.utcnow().isoformat(),
    })
    
    logger.info(
        f"Validation completed",
        extra={
            "job_id": job_id,
            "claims_validated": claims_validated,
        }
    )
    
    return {"job_id": job_id, "status": "completed", "responses": all_responses}


def validate_claims_job(proposal_hash: str, job_id: str = None) -> dict:
    """
    RQ worker job to validate all claims for a proposal.
    
    Args:
        proposal_hash: Hash of the proposal to validate
        job_id: Optional existing job ID. If not provided, a new one is generated.
        
    Returns:
        Job result with status and responses
    """
    # Load claims for proposal
    claims_data = load_claims(proposal_hash)
    if not claims_data:
        logger.error(f"Proposal not found: {proposal_hash}")
        return {"error": "Proposal not found", "proposal_hash": proposal_hash}
    
    # Parse claims
    claims = []
    for claim_dict in claims_data.get("claims", []):
        canonical_data = claim_dict.get("canonical", {})
        canonical = ClaimCanonical(
            numbers=canonical_data.get("numbers", []),
            addresses=canonical_data.get("addresses", []),
            urls=canonical_data.get("urls", []),
        )
        claims.append(Claim(
            id=claim_dict["id"],
            text=claim_dict["text"],
            paragraph_index=claim_dict.get("paragraph_index", 0),
            char_range=claim_dict.get("char_range", [0, 0]),
            type=claim_dict.get("type", "factual"),
            canonical=canonical,
        ))
    
    if not claims:
        logger.error(f"No claims found for proposal: {proposal_hash}")
        return {"error": "No claims found", "proposal_hash": proposal_hash}
    
    # Use provided job ID or generate new one
    if not job_id:
        job_id = generate_job_id()
        # Create job record only if we generated the ID (new job)
        job_state.create_job(job_id, proposal_hash, claims_data.get("claims", []))
    else:
        # Ensure job exists if ID provided
        if not job_state.get_job(job_id):
             job_state.create_job(job_id, proposal_hash, claims_data.get("claims", []))
    
    # Run async validation
    # Handle both sync and async contexts
    try:
        loop = asyncio.get_running_loop()
        # Already in async context - use a thread to run our async code
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(
                lambda: asyncio.run(_run_validation_async(job_id, proposal_hash, claims))
            )
            result = future.result()
    except RuntimeError:
        # No running loop - create one
        result = asyncio.run(_run_validation_async(job_id, proposal_hash, claims))
    
    return result


def validate_proposal_job(proposal_hash: str) -> dict:
    """Alias for validate_claims_job."""
    return validate_claims_job(proposal_hash)


def aggregate_results_job(job_id: str) -> dict:
    """
    RQ worker job to aggregate miner responses.
    
    TODO: Implement full aggregation logic.
    """
    job_data = job_state.get_job(job_id)
    if not job_data:
        return {"error": "Job not found", "job_id": job_id}
    
    # TODO: Implement aggregation
    return {
        "job_id": job_id,
        "status": "aggregated",
        "aggregated_at": datetime.utcnow().isoformat(),
    }


def attest_evidence_job(evidence_bundle: dict) -> dict:
    """
    RQ worker job to create attestation.
    
    TODO: Implement attestation logic.
    """
    # TODO: Implement attestation
    return {
        "status": "attested",
        "attested_at": datetime.utcnow().isoformat(),
    }
