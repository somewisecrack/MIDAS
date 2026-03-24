import time
import threading
import json
import os
from datetime import datetime, time as dtime
from typing import Optional, List, Dict
from pathlib import Path

from agent.scanner import Scanner
from agent.notifications import get_notification_service
from agent.data_loader import load_all_tickers, update_data_from_yfinance


class BackgroundAgent:
    def __init__(self):
        self.scanner = Scanner()
        self.notifier = get_notification_service()
        self.running = False
        self.thread: Optional[threading.Thread] = None
        
        self.schedule = {
            "market_close": dtime(16, 0),
            "pre_market": dtime(9, 30),
        }
        
        self.last_scan_time: Optional[datetime] = None
        self.last_scan_results: Optional[Dict] = None
        
        self.results_dir = Path(__file__).parent.parent / "results"
        self.results_dir.mkdir(exist_ok=True)
    
    def start(self):
        if self.running:
            return {"status": "already_running"}
        
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        
        return {
            "status": "started",
            "schedule": "Runs after market close (4 PM ET)",
            "web_ui": "http://localhost:8000"
        }
    
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        return {"status": "stopped"}
    
    def _run_loop(self):
        while self.running:
            try:
                now = datetime.now()
                
                if self._should_run_after_close(now):
                    self._run_full_scan()
                    time.sleep(3600)
                
                time.sleep(60)
                
            except Exception as e:
                print(f"Background agent error: {e}")
                time.sleep(300)
    
    def _should_run_after_close(self, now: datetime) -> bool:
        if now.hour == 16 and now.minute == 0:
            if self.last_scan_time:
                time_since = (now - self.last_scan_time).total_seconds()
                if time_since < 1800:
                    return False
            return True
        return False
    
    def run_now(self, update_data: bool = True) -> Dict:
        print("Background Agent: Running scan now...")
        
        if update_data:
            print("Updating data from Yahoo Finance...")
            _, tickers = load_all_tickers()
            update_data_from_yfinance(tickers)
        
        self.scanner = Scanner()
        result = self.scanner.scan()
        
        self.last_scan_time = result.scan_time
        self.last_scan_results = result.model_dump()
        
        self._save_results(result.model_dump())
        
        recs_dict = [
            {
                "rank": r.rank,
                "ticker": r.ticker,
                "type": r.type,
                "stock_price": r.stock_price,
                "entry_price": r.entry_price,
                "stop_loss": r.stop_loss,
                "take_profit": r.take_profit,
                "holding_period": r.holding_period,
                "confidence_score": r.confidence_score,
                "reasoning": r.reasoning,
                "strategies_triggered": [
                    {"name": s.name, "win_rate": s.win_rate, "signal": s.signal, "priority": s.priority}
                    for s in r.strategies_triggered
                ]
            }
            for r in result.recommendations
        ]
        
        self.notifier.send_scan_complete(
            recommendations=recs_dict,
            regime=result.regime,
            scan_time=result.scan_time
        )
        
        return {
            "status": "scan_complete",
            "recommendations_count": len(result.recommendations),
            "regime": result.regime,
            "scan_id": result.scan_id,
            "top_5": [
                {
                    "rank": r.rank,
                    "ticker": r.ticker,
                    "type": r.type,
                    "confidence": r.confidence_score,
                    "strategies": [s.name for s in r.strategies_triggered]
                }
                for r in result.recommendations[:5]
            ]
        }
    
    def _run_full_scan(self):
        print(f"Background Agent: Scheduled scan started at {datetime.now()}")
        try:
            result = self.run_now(update_data=True)
            print(f"Background Agent: Scan complete. Found {result['recommendations_count']} recommendations")
        except Exception as e:
            print(f"Background Agent: Scan failed - {e}")
    
    def _save_results(self, results: Dict):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = self.results_dir / f"scan_{timestamp}.json"
        
        with open(filepath, "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        self._cleanup_old_results()
    
    def _cleanup_old_results(self, keep_days: int = 30):
        cutoff = datetime.now().timestamp() - (keep_days * 86400)
        for f in self.results_dir.glob("scan_*.json"):
            if f.stat().st_mtime < cutoff:
                f.unlink()
    
    def get_latest_results(self) -> Optional[Dict]:
        if self.last_scan_results:
            return self.last_scan_results
        
        files = sorted(self.results_dir.glob("scan_*.json"), reverse=True)
        if files:
            with open(files[0]) as f:
                return json.load(f)
        
        return None
    
    def get_historical_scans(self, limit: int = 10) -> List[Dict]:
        files = sorted(self.results_dir.glob("scan_*.json"), reverse=True)[:limit]
        results = []
        for f in files:
            with open(f) as fp:
                data = json.load(fp)
                results.append({
                    "scan_id": data.get("scan_id"),
                    "scan_time": data.get("scan_time"),
                    "recommendations_count": len(data.get("recommendations", [])),
                    "regime": data.get("regime"),
                    "filename": f.name
                })
        return results
    
    def get_status(self) -> Dict:
        return {
            "running": self.running,
            "last_scan": self.last_scan_time.isoformat() if self.last_scan_time else None,
            "recommendations_cached": len(self.last_scan_results.get("recommendations", [])) if self.last_scan_results else 0,
            "schedule": "After market close (4 PM ET)",
            "notifications_configured": self.notifier.notification_enabled
        }


_agent = None

def get_agent() -> BackgroundAgent:
    global _agent
    if _agent is None:
        _agent = BackgroundAgent()
    return _agent
