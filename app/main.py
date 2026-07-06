"""
main.py — FastAPI application factory for MIDAS web app.
Serves the API + static frontend from a single process.
"""
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.db import init_db
from app.api.data import router as data_router
from app.api.strategies import router as strategies_router
from app.api.backtest import router as backtest_router
from app.api.gemma import router as gemma_router
from app.core.gemma_client import is_available

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"


def create_app() -> FastAPI:
    app = FastAPI(
        title="MIDAS — Swing Strategy Test Bench",
        version="2.0.0",
        description="Backtesting and pattern discovery for swing trading strategies.",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Startup ────────────────────────────────────────────────────────────────
    @app.on_event("startup")
    async def startup():
        logger.info("Initialising MIDAS database...")
        init_db()
        logger.info("Database ready.")

        ollama = is_available()
        if ollama["available"]:
            models = ollama.get("models", [])
            logger.info("Ollama: online | models: %s", models)
        else:
            logger.warning(
                "Ollama: OFFLINE — Gemma features will be unavailable. "
                "Install Ollama and run: ollama pull gemma3:12b"
            )

    # ── Health ─────────────────────────────────────────────────────────────────
    @app.get("/api/health", tags=["system"])
    async def health():
        from app.core.db import get_cached_tickers
        ollama = is_available()
        cached = get_cached_tickers()
        return {
            "status": "ok",
            "ollama": ollama,
            "cached_tickers": len(cached),
        }

    # ── API routers ─────────────────────────────────────────────────────────────
    app.include_router(data_router)
    app.include_router(strategies_router)
    app.include_router(backtest_router)
    app.include_router(gemma_router)

    # ── Static files (frontend) ────────────────────────────────────────────────
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(full_path: str):
            """Serve index.html for any unmatched route (SPA catch-all)."""
            index = STATIC_DIR / "index.html"
            if index.exists():
                return FileResponse(index)
            return {"error": "Frontend not found. Ensure app/static/index.html exists."}

    return app


app = create_app()
