import uvicorn
import sys
import os
import argparse
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_scan():
    print("=" * 60)
    print("  MIDAS - SCAN MODE")
    print("=" * 60)
    print()
    
    from agent.scanner import Scanner
    from agent.notifications import get_notification_service
    from agent.data_loader import load_all_tickers, update_data_from_yfinance
    
    print("Loading data...")
    _, sp500_tickers, other_tickers = load_all_tickers()
    tickers = sp500_tickers + other_tickers
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
    email_sent = notifier.send_scan_complete(
        recommendations=[r.model_dump() for r in result.recommendations],
        regime=result.regime,
        scan_time=result.scan_time
    )
    print("  Email sent!" if email_sent else "  Email failed!")
    
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
            update_results = update_data_from_yfinance(all_tickers, force_full_refresh=True)
            
            scanner = Scanner()
            result = scanner.scan()

            expected_count = 40
            if len(result.recommendations) < expected_count:
                return {
                    "status": "error",
                    "message": f"Scan completed but produced {len(result.recommendations)} recommendations, expected {expected_count}.",
                    "regime": result.regime,
                    "count": len(result.recommendations),
                    "sp500_scanned": result.sp500_scanned,
                    "other_scanned": result.other_scanned,
                    "update_results": update_results
                }
            
            notifier = get_notification_service()
            email_sent = notifier.send_scan_complete(
                recommendations=[r.model_dump() for r in result.recommendations],
                regime=result.regime,
                scan_time=result.scan_time,
                sp500_count=result.sp500_scanned,
                other_count=result.other_scanned
            )
            if not email_sent:
                return {
                    "status": "error",
                    "message": "Scan completed but email delivery failed.",
                    "regime": result.regime,
                    "count": len(result.recommendations),
                    "sp500_scanned": result.sp500_scanned,
                    "other_scanned": result.other_scanned
                }
            
            return {
                "status": "success",
                "message": f"Scan complete. {len(result.recommendations)} recommendations sent to email.",
                "regime": result.regime,
                "count": len(result.recommendations),
                "sp500_scanned": result.sp500_scanned,
                "other_scanned": result.other_scanned,
                "update_results": update_results
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
    print("  MIDAS v2.0")
    print("  Automated Strategy Scanner")
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
