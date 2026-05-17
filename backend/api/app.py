"""FastAPI application factory."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from api.routes.design import router as design_router
from api.routes.health import router as health_router
from api.routes.workspace import router as workspace_router
from api.ws.design_ws import design_ws_handler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    # Ensure workspace and upload dirs exist
    for d in ["uploads", "workspaces"]:
        Path(d).mkdir(parents=True, exist_ok=True)
    logger.info("AI Frontend Designer backend starting up.")
    yield
    logger.info("AI Frontend Designer backend shutting down.")


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Frontend Designer API",
        description="Upload screenshots → get frontend code. Multi-turn feedback loop.",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS — allow all origins in dev; restrict in production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # REST routes
    app.include_router(design_router, prefix="/api/v1")
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(workspace_router, prefix="/api/v1")

    # WebSocket route
    @app.websocket("/ws/design/{session_id}")
    async def ws_design(websocket: WebSocket, session_id: str):
        await design_ws_handler(websocket, session_id)

    @app.get("/")
    async def root():
        return {"message": "AI Frontend Designer API", "docs": "/docs"}

    return app


app = create_app()
