from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import os

from agent.scanner import get_scanner
from agent.models import ScanResponse, DataStatus, StrategyInfo
from agent.strategies.swing import SWING_STRATEGIES
from agent.strategies.intraday import INTRADAY_STRATEGIES
from agent.strategies.meta import META_STRATEGIES
from agent.data_loader import update_data_from_yfinance, load_all_tickers
from agent.background_agent import get_agent

app = FastAPI(
    title="MIDAS",
    description="AI-powered trading strategy scanner",
    version="2.0.0"
)


class ScanRequest(BaseModel):
    update_data: bool = True


class UpdateResponse(BaseModel):
    status: str
    message: str
    success_count: Optional[int] = None
    failed_count: Optional[int] = None


class AgentResponse(BaseModel):
    status: str
    message: Optional[str] = None
    recommendations_count: Optional[int] = None
    regime: Optional[str] = None
    scan_id: Optional[str] = None


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates_dir = os.path.join(BASE_DIR, "agent", "templates")


@app.get("/", response_class=HTMLResponse)
async def root():
    html_path = os.path.join(templates_dir, "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r") as f:
            return f.read()
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>MIDAS</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-900 text-white min-h-screen p-8">
        <div class="max-w-4xl mx-auto">
            <h1 class="text-4xl font-bold mb-8 text-center">MIDAS</h1>
            <div class="text-center">
                <p class="text-gray-400 mb-4">UI template not found. API is running.</p>
                <a href="/docs" class="text-blue-400 hover:underline">View API Documentation</a>
            </div>
        </div>
    </body>
    </html>
    """


@app.get("/api/data/status", response_model=DataStatus)
async def data_status():
    scanner = get_scanner()
    return scanner.initialize()


@app.post("/api/data/update", response_model=UpdateResponse)
async def update_data():
    try:
        _, sp500_tickers, other_tickers = load_all_tickers()
        results = update_data_from_yfinance(sp500_tickers + other_tickers)
        
        if results.get("updated"):
            return UpdateResponse(
                status="success",
                message=f"Data updated. {results.get('success', 0)} tickers updated.",
                success_count=results.get("success", 0),
                failed_count=results.get("failed", 0)
            )
        else:
            return UpdateResponse(
                status="info",
                message="No new data available or update failed.",
                success_count=results.get("success", 0),
                failed_count=results.get("failed", 0)
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/scan", response_model=ScanResponse)
async def scan():
    try:
        scanner = get_scanner()
        return scanner.scan()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/agent/start")
async def start_agent():
    agent = get_agent()
    result = agent.start()
    return result


@app.post("/api/agent/stop")
async def stop_agent():
    agent = get_agent()
    result = agent.stop()
    return result


@app.post("/api/agent/run-now")
async def run_agent_now(request: ScanRequest):
    agent = get_agent()
    try:
        result = agent.run_now(update_data=request.update_data)
        return AgentResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agent/status")
async def agent_status():
    agent = get_agent()
    return agent.get_status()


@app.get("/api/agent/results/latest")
async def agent_latest_results():
    agent = get_agent()
    results = agent.get_latest_results()
    if results is None:
        return {"status": "no_results", "message": "No scan results available"}
    return results


@app.get("/api/agent/results/history")
async def agent_history():
    agent = get_agent()
    history = agent.get_historical_scans()
    return {"scans": history}


@app.get("/api/strategies")
async def list_strategies():
    swing_strategies = [
        StrategyInfo(
            name=s["name"],
            type="SWING",
            priority="MEDIUM",
            description=f"Swing trading strategy: {s['name']}"
        )
        for s in SWING_STRATEGIES
    ]
    
    intraday_strategies = [
        StrategyInfo(
            name=s["name"],
            type="INTRADAY",
            priority="MEDIUM",
            description=f"Intraday trading strategy: {s['name']}"
        )
        for s in INTRADAY_STRATEGIES
    ]
    
    meta_strategies = [
        StrategyInfo(
            name=s["name"],
            type="META",
            priority="REQUIRED",
            description=f"Market filter: {s['name']}"
        )
        for s in META_STRATEGIES
    ]
    
    return {
        "swing": swing_strategies,
        "intraday": intraday_strategies,
        "meta": meta_strategies,
        "total": len(SWING_STRATEGIES) + len(INTRADAY_STRATEGIES) + len(META_STRATEGIES)
    }


@app.get("/api/health")
async def health():
    agent = get_agent()
    return {
        "status": "healthy",
        "agent_running": agent.running,
        "timestamp": datetime.now().isoformat()
    }
