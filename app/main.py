"""
main.py — FastAPI application factory for MIDAS web app.
Serves the API + static frontend from a single process.
"""
import logging
import re
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

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

# Matches any /static/*.js or /static/*.css reference, with or without an
# existing ?v= token, so the token can be regenerated on every request.
_ASSET_REF = re.compile(r"""(/static/[^"'?\s]+?\.(?:js|css))(\?v=[^"']*)?""")


def _asset_version(url_path: str) -> str | None:
    """Cache-busting token for a /static asset, derived from its mtime."""
    asset = STATIC_DIR / url_path.removeprefix("/static/")
    try:
        return str(int(asset.stat().st_mtime))
    except OSError:
        return None


def render_index() -> str:
    """
    Serve index.html with every JS/CSS URL stamped by the asset's mtime.

    Editing a frontend file therefore changes its URL automatically, so browsers
    can never run a stale bundle against newer markup. Nothing needs a manual
    version bump.
    """
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")

    def stamp(match: re.Match) -> str:
        url_path = match.group(1)
        version = _asset_version(url_path)
        return f"{url_path}?v={version}" if version else match.group(0)

    return _ASSET_REF.sub(stamp, html)


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
            if not index.exists():
                return {"error": "Frontend not found. Ensure app/static/index.html exists."}
            # index.html must never be cached, or the browser would keep reusing
            # an old copy and never see the freshly stamped asset URLs.
            return HTMLResponse(
                render_index(),
                headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
            )

    return app


app = create_app()
