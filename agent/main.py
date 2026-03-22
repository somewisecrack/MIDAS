import uvicorn
import sys
import os
import argparse
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_scan():
    print("=" * 60)
    print("  TRADING AGENT - SCAN MODE")
    print("=" * 60)
    print()
    
    from agent.scanner import Scanner
    from agent.notifications import get_notification_service
    from agent.data_loader import load_all_tickers, update_data_from_yfinance
    
    print("Loading data...")
    _, tickers = load_all_tickers()
    print(f"  {len(tickers)} tickers loaded")
    
    print("\nUpdating data from Yahoo Finance...")
    try:
        results = update_data_from_yfinance(tickers)
        print(f"  Updated: {results.get('success', 0)} tickers")
    except Exception as e:
        print(f"  Update failed: {e}")
    
    print("\nRunning strategy scan...")
    scanner = Scanner()
    result = scanner.scan()
    
    print(f"  Found {len(result.recommendations)} recommendations")
    print(f"  Regime: {result.regime}")
    
    print("\nSending email notification...")
    notifier = get_notification_service()
    notifier.send_scan_complete(
        recommendations=[r.model_dump() for r in result.recommendations],
        regime=result.regime,
        scan_time=result.scan_time
    )
    print("  Email sent!")
    
    print()
    print("=" * 60)
    print("  SCAN COMPLETE")
    print("=" * 60)


def create_server_app():
    from agent.api import app as api_app
    from agent.scanner import Scanner
    from agent.notifications import get_notification_service
    from agent.data_loader import load_all_tickers, update_data_from_yfinance
    
    @api_app.get("/health")
    async def health():
        return {"status": "healthy"}
    
    @api_app.post("/scan")
    async def cloud_run_scan():
        try:
            _, sp500_tickers, other_tickers = load_all_tickers()
            all_tickers = sp500_tickers + other_tickers
            results = update_data_from_yfinance(all_tickers, force_full_refresh=True)
            
            scanner = Scanner()
            result = scanner.scan()
            
            notifier = get_notification_service()
            notifier.send_scan_complete(
                recommendations=[r.model_dump() for r in result.recommendations],
                regime=result.regime,
                scan_time=result.scan_time,
                sp500_count=result.sp500_scanned,
                other_count=result.other_scanned
            )
            
            return {
                "status": "success",
                "message": f"Scan complete. {len(result.recommendations)} recommendations sent to email.",
                "regime": result.regime,
                "count": len(result.recommendations),
                "sp500_scanned": result.sp500_scanned,
                "other_scanned": result.other_scanned
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    return api_app


def main():
    parser = argparse.ArgumentParser(description="MIDAS Trading Scanner")
    parser.add_argument("--scan-only", action="store_true", help="Run scan and send email, then exit")
    parser.add_argument("--cloud-run", action="store_true", help="Run as Cloud Run service")
    parser.add_argument("--update-data", action="store_true", default=True, help="Update data before scan")
    parser.add_argument("--start-agent", action="store_true", help="Start background agent on launch")
    parser.add_argument("--port", type=int, default=8080, help="Port to run server on")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    args = parser.parse_args()
    
    if args.scan_only:
        run_scan()
        return
    
    if args.cloud_run:
        port = int(os.environ.get("PORT", 8080))
        app = create_server_app()
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
        return
    
    print("=" * 60)
    print("  TRADING AGENT v2.0")
    print("  AI-Powered Strategy Scanner")
    print("=" * 60)
    print()
    
    if args.start_agent:
        from agent.background_agent import get_agent
        agent = get_agent()
        agent.start()
        print("  [✓] Background Agent: RUNNING")
    else:
        print("  [ ] Background Agent: Manual start required")
    
    print()
    print("  Server starting...")
    print(f"  Web UI:     http://localhost:{args.port}")
    print(f"  API Docs:   http://localhost:{args.port}/docs")
    print()
    print("  Commands:")
    print("    curl -X POST http://localhost:8000/api/agent/start  - Start background agent")
    print("    curl -X POST http://localhost:8000/api/agent/run-now - Run scan immediately")
    print()
    print("=" * 60)
    
    from agent.api import app
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=False,
        log_level="info"
    )


if __name__ == "__main__":
    main()
