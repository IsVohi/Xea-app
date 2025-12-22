"""
Xea Governance Oracle - Main FastAPI Application

Entry point for the backend API server with WebSocket support.
"""

import asyncio
import json
import logging
from typing import Dict, Set
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.api import router
from app.config import settings

logger = logging.getLogger(__name__)


# ============================================================================
# WebSocket Connection Manager
# ============================================================================

class ConnectionManager:
    """Manages WebSocket connections for job updates."""
    
    def __init__(self):
        # job_id -> set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, job_id: str):
        """Accept and register a WebSocket connection."""
        await websocket.accept()
        if job_id not in self.active_connections:
            self.active_connections[job_id] = set()
        self.active_connections[job_id].add(websocket)
        logger.info(f"WebSocket connected for job {job_id}")
    
    def disconnect(self, websocket: WebSocket, job_id: str):
        """Remove a WebSocket connection."""
        if job_id in self.active_connections:
            self.active_connections[job_id].discard(websocket)
            if not self.active_connections[job_id]:
                del self.active_connections[job_id]
        logger.info(f"WebSocket disconnected for job {job_id}")
    
    async def broadcast(self, job_id: str, message: dict):
        """Broadcast a message to all connections for a job."""
        if job_id not in self.active_connections:
            return
        
        message_json = json.dumps(message, default=str)
        disconnected = set()
        
        for websocket in self.active_connections[job_id]:
            try:
                await websocket.send_text(message_json)
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket: {e}")
                disconnected.add(websocket)
        
        # Clean up disconnected sockets
        for ws in disconnected:
            self.active_connections[job_id].discard(ws)
    
    async def send_miner_response(
        self,
        job_id: str,
        claim_id: str,
        miner_response: dict,
    ):
        """Send a miner response update."""
        await self.broadcast(job_id, {
            "type": "miner_response",
            "job_id": job_id,
            "claim_id": claim_id,
            "miner_response": miner_response,
        })
    
    async def send_status_update(
        self,
        job_id: str,
        status: str,
        progress: dict,
    ):
        """Send a status update."""
        await self.broadcast(job_id, {
            "type": "status",
            "job_id": job_id,
            "status": status,
            "progress": progress,
        })
    
    async def send_aggregate(
        self,
        job_id: str,
        evidence_bundle: dict,
    ):
        """Send aggregation complete message."""
        await self.broadcast(job_id, {
            "type": "aggregate",
            "job_id": job_id,
            "evidence_bundle": evidence_bundle,
        })


# Global connection manager
ws_manager = ConnectionManager()


# ============================================================================
# Application Lifespan
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Xea Governance Oracle starting...")
    yield
    logger.info("Xea Governance Oracle shutting down...")


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="Xea Governance Oracle",
    description="Verifiable governance intelligence powered by decentralized inference",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
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


# ============================================================================
# Root Endpoints
# ============================================================================

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


# ============================================================================
# WebSocket Endpoints
# ============================================================================

@app.websocket("/ws/jobs/{job_id}")
async def websocket_job_updates(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for streaming job updates.
    
    Messages sent:
    - { type: "miner_response", claim_id, miner_response }
    - { type: "status", status, progress }
    - { type: "aggregate", evidence_bundle }
    
    The connection remains open until the client disconnects or
    the aggregation is complete.
    """
    await ws_manager.connect(websocket, job_id)
    
    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "job_id": job_id,
            "message": "Connected to job updates stream",
        })
        
        # Keep connection alive, handle client messages
        while True:
            try:
                # Wait for client messages (ping/pong or disconnect)
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )
                
                # Handle ping
                if data == "ping":
                    await websocket.send_json({"type": "pong"})
                    
            except asyncio.TimeoutError:
                # Send keepalive
                try:
                    await websocket.send_json({"type": "keepalive"})
                except Exception:
                    break
                    
    except WebSocketDisconnect:
        logger.info(f"Client disconnected from job {job_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        ws_manager.disconnect(websocket, job_id)


# ============================================================================
# Export for workers to use
# ============================================================================

def get_ws_manager() -> ConnectionManager:
    """Get the WebSocket connection manager."""
    return ws_manager
