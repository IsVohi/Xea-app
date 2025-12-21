"""
Xea Governance Oracle - Main FastAPI Application

Entry point for the backend API server.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router
from app.config import settings

app = FastAPI(
    title="Xea Governance Oracle",
    description="Verifiable governance intelligence powered by decentralized inference",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "name": "Xea Governance Oracle",
        "version": "0.1.0",
        "status": "healthy",
    }


@app.get("/health")
async def health():
    """Detailed health check."""
    return {
        "status": "healthy",
        "redis": "connected",  # TODO: Implement actual check
        "version": "0.1.0",
    }
