"""
strategies.py — /api/strategies endpoint: list all available swing strategies.
"""
from fastapi import APIRouter
from app.core.strategy_adapter import list_strategies

router = APIRouter(prefix="/api/strategies", tags=["strategies"])


@router.get("")
async def get_strategies():
    """Return all available swing strategies with metadata."""
    strategies = list_strategies()
    return {"strategies": strategies, "count": len(strategies)}
