"""
Xea Governance Oracle - Attestation

Handles signing and on-chain attestation of evidence bundles.
"""

from typing import Optional
from eth_account import Account
from eth_account.messages import encode_defunct
import hashlib

from app.config import settings


def compute_evidence_hash(evidence_bundle: dict) -> str:
    """
    Compute hash of evidence bundle for signing.

    Args:
        evidence_bundle: Evidence bundle dictionary

    Returns:
        Hex string of SHA-256 hash
    """
    import json
    canonical = json.dumps(evidence_bundle, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def sign_evidence(evidence_hash: str, private_key: Optional[str] = None) -> str:
    """
    Sign evidence hash with Ethereum private key.

    Args:
        evidence_hash: Hex string of evidence hash
        private_key: Ethereum private key (defaults to settings)

    Returns:
        Signature hex string
    """
    key = private_key or settings.signer_private_key
    if not key:
        raise ValueError("No signer private key configured")

    message = encode_defunct(text=evidence_hash)
    signed = Account.sign_message(message, private_key=key)
    return signed.signature.hex()


def verify_signature(evidence_hash: str, signature: str, expected_address: str) -> bool:
    """
    Verify evidence signature.

    Args:
        evidence_hash: Original evidence hash
        signature: Signature to verify
        expected_address: Expected signer address

    Returns:
        True if signature is valid and from expected address
    """
    message = encode_defunct(text=evidence_hash)
    recovered = Account.recover_message(message, signature=signature)
    return recovered.lower() == expected_address.lower()


async def submit_attestation(
    evidence_cid: str,
    signature: str,
) -> Optional[str]:
    """
    Submit attestation to blockchain.

    Args:
        evidence_cid: IPFS CID of evidence bundle
        signature: Signature of evidence hash

    Returns:
        Transaction hash if submitted, None if not configured
    """
    # TODO: Implement blockchain submission
    # - Connect to Ethereum network
    # - Call attestation contract
    # - Return transaction hash
    return None


async def upload_to_ipfs(data: dict) -> str:
    """
    Upload evidence bundle to IPFS.

    Args:
        data: Evidence bundle to upload

    Returns:
        IPFS CID
    """
    # TODO: Implement IPFS upload
    # - Connect to IPFS node
    # - Upload JSON data
    # - Return CID
    raise NotImplementedError("IPFS upload not yet implemented")
