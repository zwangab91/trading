from __future__ import annotations

from fastapi import APIRouter

from backend.app.schemas import PolicyResponse
from backend.app.serialization import serialize_policy
from trading_agent.config import load_policy


router = APIRouter(prefix="/api/policy", tags=["policy"])


@router.get("", response_model=PolicyResponse)
def get_policy() -> PolicyResponse:
    return serialize_policy(load_policy())
