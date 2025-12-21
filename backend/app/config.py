"""
Xea Governance Oracle - Configuration

Application settings loaded from environment variables.
"""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Redis configuration
    redis_url: str = "redis://localhost:6379/0"

    # Security
    secret_key: str = "changeme"

    # IPFS
    ipfs_api_url: str = "http://localhost:5001"

    # Cortensor / Miner routing
    cortensor_router_url: str = ""

    # Ethereum signing
    signer_private_key: str = ""
    xea_signer_address: str = ""

    # Application settings
    debug: bool = True
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
