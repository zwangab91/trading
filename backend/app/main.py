from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.routers import dashboard, data, policy
from backend.app.schemas import HealthResponse


def create_app() -> FastAPI:
    app = FastAPI(
        title="Trading Agent API",
        description="Backtest, policy, and dashboard API for the trading agent.",
        version="0.1.0",
    )

    default_origins = "http://localhost:3000,http://127.0.0.1:3000"
    allowed_origins = [
        origin.strip()
        for origin in os.environ.get("ALLOWED_ORIGINS", default_origins).split(",")
        if origin.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(policy.router)
    app.include_router(dashboard.router)
    app.include_router(data.router)

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.get("/")
    def root() -> dict:
        return {"message": "Trading Agent API", "docs": "/docs"}

    return app


app = create_app()
