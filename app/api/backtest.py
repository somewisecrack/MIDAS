"""
backtest.py — /api/backtest/* endpoints: run, list, get, patch, delete.
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.backtest_engine import run_backtest
from app.core.data_service import load_from_cache, rows_to_dataframe, resolve_preset
from app.core.db import (
    save_backtest_run,
    list_backtest_runs,
    get_backtest_run,
    delete_backtest_run,
    update_backtest_run_label,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/backtest", tags=["backtest"])


class BacktestRequest(BaseModel):
    ticker: Optional[str] = None
    tickers: Optional[List[str]] = None
    sp500: Optional[bool] = False
    strategy_ids: List[str]
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    preset: Optional[str] = None
    label: str = ""


class LabelPatch(BaseModel):
    label: str


@router.post("/run")
async def run(req: BacktestRequest):
    """Run a backtest and save the results."""
    if not req.strategy_ids:
        raise HTTPException(status_code=422, detail="At least one strategy_id required.")

    if req.preset:
        date_from, date_to = resolve_preset(req.preset)
    elif req.date_from and req.date_to:
        date_from, date_to = req.date_from, req.date_to
    else:
        date_from, date_to = resolve_preset("1Y")

    from app.core.strategy_adapter import get_strategy
    strategy_names = [
        (get_strategy(sid).name if get_strategy(sid) else sid)
        for sid in req.strategy_ids
    ]

    # S&P 500 override
    if req.sp500:
        from agent.data_loader import get_sp500_tickers
        try:
            req.tickers = get_sp500_tickers()
        except Exception as e:
            logger.error(f"Failed to fetch S&P 500: {e}")
            raise HTTPException(status_code=500, detail="Could not fetch S&P 500 ticker list")

    # Batch Backtesting
    if req.tickers and len(req.tickers) > 0:
        from app.core.backtest_engine import run_batch_backtest
        
        tickers_list = req.tickers
        # If ticker is provided, add it to the batch as well just in case
        if req.ticker and req.ticker not in tickers_list:
            tickers_list.insert(0, req.ticker)
            
        result = run_batch_backtest(
            tickers=tickers_list,
            strategy_ids=req.strategy_ids,
            date_from=date_from,
            date_to=date_to,
        )
        
        run_id = save_backtest_run(
            ticker="BATCH",
            strategy_names=strategy_names,
            date_from=date_from,
            date_to=date_to,
            stats=result["stats"],
            trades=result["trades"],
            label=req.label or f"Batch ({len(tickers_list)} tickers)",
        )
        
        return {
            "status": "ok",
            "run_id": run_id,
            "ticker": "BATCH",
            "date_from": date_from,
            "date_to": date_to,
            "strategies": strategy_names,
            **result,
        }

    # Single Ticker Backtesting
    if not req.ticker:
        raise HTTPException(status_code=422, detail="Either ticker or tickers must be provided.")

    try:
        raw_rows = load_from_cache(req.ticker, date_from, date_to)
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=f"No data cached for {req.ticker.upper()} {date_from}→{date_to}. "
                   f"Fetch data first via POST /api/data/fetch. ({e})"
        )

    df = rows_to_dataframe(raw_rows)

    result = run_backtest(
        ticker=req.ticker.upper(),
        strategy_ids=req.strategy_ids,
        df=df,
        date_from=date_from,
        date_to=date_to,
    )

    if "error" in result:
        return {"status": "warning", **result}

    run_id = save_backtest_run(
        ticker=req.ticker.upper(),
        strategy_names=strategy_names,
        date_from=date_from,
        date_to=date_to,
        stats=result["stats"],
        trades=result["trades"],
        label=req.label,
    )

    return {
        "status": "ok",
        "run_id": run_id,
        "ticker": req.ticker.upper(),
        "date_from": date_from,
        "date_to": date_to,
        "strategies": strategy_names,
        **result,
    }


@router.get("/runs")
async def list_runs():
    """List all saved backtest runs."""
    runs = list_backtest_runs()
    return {"runs": runs, "count": len(runs)}


@router.get("/runs/{run_id}")
async def get_run(run_id: str):
    """Get full details of a saved backtest run including all trades."""
    run = get_backtest_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")
    return run


@router.delete("/runs/{run_id}")
async def delete_run(run_id: str):
    """Delete a saved backtest run."""
    run = get_backtest_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")
    delete_backtest_run(run_id)
    return {"status": "deleted", "run_id": run_id}


@router.patch("/runs/{run_id}")
async def patch_run(run_id: str, body: LabelPatch):
    """Update the label of a saved backtest run."""
    run = get_backtest_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")
    update_backtest_run_label(run_id, body.label)
    return {"status": "updated", "run_id": run_id, "label": body.label}


@router.post("/scan")
async def run_scan(req: BacktestRequest):
    """Scan S&P 500 (or batch) tickers to find active setups on the last available day."""
    if not req.strategy_ids:
        raise HTTPException(status_code=422, detail="At least one strategy_id required.")

    if not req.sp500 and not req.tickers:
        raise HTTPException(status_code=422, detail="Scan requires sp500 or batch tickers")

    from app.core.strategy_adapter import scan_strategy, get_strategy
    from app.core.data_service import fetch_and_cache

    if req.preset:
        date_from, date_to = resolve_preset(req.preset)
    elif req.date_from and req.date_to:
        date_from, date_to = req.date_from, req.date_to
    else:
        date_from, date_to = resolve_preset("1Y")

    if req.sp500:
        from agent.data_loader import get_sp500_tickers
        try:
            tickers = get_sp500_tickers()
        except Exception as e:
            logger.error(f"Failed to fetch S&P 500: {e}")
            raise HTTPException(status_code=500, detail="Could not fetch S&P 500 ticker list")
    else:
        tickers = req.tickers

    results = []
    
    for ticker in tickers:
        try:
            raw_rows = load_from_cache(ticker, date_from, date_to)
        except ValueError:
            try:
                fetch_and_cache(ticker, date_from, date_to, force=False)
                raw_rows = load_from_cache(ticker, date_from, date_to)
            except Exception as e:
                logger.warning(f"Scan skipping {ticker} due to data fetch error: {e}")
                continue

        df = rows_to_dataframe(raw_rows)
        if df.empty or len(df) < 30:
            continue

        for sid in req.strategy_ids:
            signal = scan_strategy(sid, df, ticker)
            if signal:
                last_bar = df.iloc[-1]
                close_price = float(last_bar["Close"])
                strat_meta = get_strategy(sid)
                strat_name = strat_meta.name if strat_meta else sid
                
                results.append({
                    "ticker": ticker,
                    "strategy": strat_name,
                    "close_price": close_price,
                    "direction": signal.get("type", "LONG"),
                    "entry_price": signal.get("entry_price", close_price),
                    "stop_loss": signal.get("stop_loss", 0),
                    "confidence": signal.get("confidence", 70),
                    "reasoning": signal.get("reasoning", "")
                })

    results.sort(key=lambda x: x["close_price"])
    
    return {
        "status": "ok",
        "date_from": date_from,
        "date_to": date_to,
        "results": results
    }
