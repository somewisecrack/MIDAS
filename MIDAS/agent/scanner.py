from typing import Dict, List, Optional
import pandas as pd
from datetime import datetime
from collections import defaultdict

from agent.data_loader import (
    load_all_tickers, 
    check_data_freshness, 
    get_stock_price, 
    get_price_range
)
from agent.strategies.swing import SWING_STRATEGIES
from agent.strategies.intraday import INTRADAY_STRATEGIES
from agent.strategies.meta import detect_regime, apply_meta_filters
from agent.models import (
    Recommendation, 
    TriggeredStrategy, 
    ScanResponse,
    DataStatus
)
from agent.config import MAX_RECOMMENDATIONS, STRATEGY_WEIGHTS


INTRADAY_KEYWORDS = ["same day", "intraday", "day trade only", "scalp", "3-5 bars", "5 bars", "10 bars"]


def is_intraday_trade(holding_period: str) -> bool:
    hp_lower = holding_period.lower()
    for keyword in INTRADAY_KEYWORDS:
        if keyword in hp_lower:
            return True
    return False


def calculate_risk_reward(entry: float, stop: float, direction: str) -> float:
    risk = abs(entry - stop)
    
    if direction == "SHORT":
        target = entry - (risk * 2)
        if target >= entry:
            target = entry - risk * 1.5
    else:
        target = entry + (risk * 2)
        if target <= entry:
            target = entry + risk * 1.5
    
    return round(target, 2)


class Scanner:
    def __init__(self):
        self.df = None
        self.ticker_dataframes = {}
        self.ticker_prices = {}
        self.ticker_price_categories = {}
        self.sp500_tickers = []
        self.other_tickers = []
        self.regime = "UNKNOWN"
        self.data_last_updated = None
        self.data_freshness = ""
        self.is_stale = False
    
    def initialize(self) -> DataStatus:
        self.df, self.sp500_tickers, self.other_tickers = load_all_tickers()
        self.data_last_updated, self.data_freshness, self.is_stale = check_data_freshness(self.df)
        self.regime = detect_regime(self.df)
        
        all_tickers = self.sp500_tickers + self.other_tickers
        for ticker in all_tickers:
            ticker_df = self.df[self.df["Ticker"] == ticker].sort_values("Date")
            if len(ticker_df) >= 30:
                self.ticker_dataframes[ticker] = ticker_df
                self.ticker_prices[ticker] = ticker_df["Close"].iloc[-1]
                self.ticker_price_categories[ticker] = get_price_range(self.ticker_prices[ticker])
        
        return DataStatus(
            last_updated=self.data_last_updated,
            freshness=self.data_freshness,
            stocks=len(all_tickers),
            is_stale=self.is_stale
        )
    
    def scan(self) -> ScanResponse:
        if self.df is None:
            self.initialize()
        
        all_signals = []
        strategies_run = len(SWING_STRATEGIES) + len(INTRADAY_STRATEGIES)
        
        for ticker in self.ticker_dataframes.keys():
            ticker_df = self.ticker_dataframes[ticker]
            current_price = self.ticker_prices[ticker]
            price_category = self.ticker_price_categories[ticker]
            
            swing_signals = self._scan_swing_strategies(ticker, ticker_df, current_price, price_category)
            all_signals.extend(swing_signals)
            
            intraday_signals = self._scan_intraday_strategies(ticker, ticker_df, current_price, price_category)
            all_signals.extend(intraday_signals)
        
        recommendations = self._rank_and_aggregate(all_signals)
        
        sp500_recs = []
        other_recs = []
        for rec in recommendations:
            if rec.ticker in self.sp500_tickers:
                rec.is_sp500 = True
                sp500_recs.append(rec)
            else:
                rec.is_sp500 = False
                other_recs.append(rec)
        
        all_recs = sp500_recs + other_recs
        for i, rec in enumerate(all_recs):
            rec.rank = i + 1
        
        scan_id = f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return ScanResponse(
            scan_id=scan_id,
            scan_time=datetime.now(),
            data_freshness=self.data_freshness,
            data_last_updated=self.data_last_updated,
            stocks_scanned=len(self.sp500_tickers) + len(self.other_tickers),
            sp500_scanned=len(self.sp500_tickers),
            other_scanned=len(self.other_tickers),
            strategies_run=strategies_run,
            regime=self.regime,
            recommendations=all_recs
        )
    
    def _scan_swing_strategies(
        self, 
        ticker: str, 
        df: pd.DataFrame, 
        price: float, 
        price_category: str
    ) -> List[Dict]:
        signals = []
        
        for strategy in SWING_STRATEGIES:
            try:
                result = strategy["func"](df, ticker)
                if result:
                    meta = apply_meta_filters(ticker, df, "SWING", self.regime)
                    if not meta["apply_strategy"]:
                        continue
                    
                    if price_category not in result["price_ranges"] and "all" not in result["price_ranges"]:
                        continue
                    
                    result["ticker"] = ticker
                    result["stock_price"] = price
                    result["category"] = "SWING"
                    base_confidence = result["confidence"]
                    result["confidence"] = int(base_confidence * meta["weight_modifier"])
                    result["meta_reason"] = meta["reason"]
                    signals.append(result)
            except Exception:
                continue
        
        return signals
    
    def _scan_intraday_strategies(
        self, 
        ticker: str, 
        df: pd.DataFrame, 
        price: float, 
        price_category: str
    ) -> List[Dict]:
        signals = []
        
        for strategy in INTRADAY_STRATEGIES:
            try:
                result = strategy["func"](df, ticker)
                if result:
                    meta = apply_meta_filters(ticker, df, "INTRADAY", self.regime)
                    if not meta["apply_strategy"]:
                        continue
                    
                    if price_category not in result["price_ranges"] and "all" not in result["price_ranges"]:
                        continue
                    
                    result["ticker"] = ticker
                    result["stock_price"] = price
                    result["category"] = "INTRADAY"
                    base_confidence = result["confidence"]
                    result["confidence"] = int(base_confidence * meta["weight_modifier"])
                    result["meta_reason"] = meta["reason"]
                    signals.append(result)
            except Exception:
                continue
        
        return signals
    
    def _rank_and_aggregate(self, signals: List[Dict]) -> List[Recommendation]:
        ticker_signals = defaultdict(list)
        for signal in signals:
            ticker_signals[signal["ticker"]].append(signal)
        
        ticker_scores = []
        for ticker, ticker_signal_list in ticker_signals.items():
            base_score = 0
            triggered_strategies = []
            
            swing_strats = []
            intraday_strats = []
            
            for sig in ticker_signal_list:
                weight = STRATEGY_WEIGHTS.get(sig.get("priority", "MEDIUM"), 1.0)
                capped_confidence = min(sig["confidence"], 70)
                base_score += capped_confidence * weight
                
                triggered_strategies.append(TriggeredStrategy(
                    name=sig["strategy"],
                    win_rate=sig.get("win_rate", "N/A"),
                    max_gain=sig.get("max_gain"),
                    signal=sig["signal"],
                    priority=sig.get("priority", "MEDIUM")
                ))
                
                if sig.get("category") == "INTRADAY":
                    intraday_strats.append(sig)
                else:
                    swing_strats.append(sig)
            
            composite_score = base_score / len(ticker_signal_list)
            
            avg_entry = sum(s.get("entry_price", 0) for s in ticker_signal_list) / len(ticker_signal_list)
            avg_stop = sum(s.get("stop_loss", 0) for s in ticker_signal_list) / len(ticker_signal_list)
            
            long_strats = [s for s in ticker_signal_list if s.get("type") == "LONG"]
            short_strats = [s for s in ticker_signal_list if s.get("type") == "SHORT"]
            
            if len(long_strats) >= len(short_strats):
                direction = "LONG"
            else:
                direction = "SHORT"
            
            if len(intraday_strats) > len(swing_strats):
                trade_category = "INTRADAY"
                holding_period = "Same day"
            else:
                trade_category = "SWING"
                holding_period = swing_strats[0]["holding_period"] if swing_strats else ticker_signal_list[0]["holding_period"]
            
            trade_type = f"{direction} {trade_category}"
            
            corrected_entry = avg_entry
            corrected_stop = avg_stop
            
            if direction == "SHORT":
                if corrected_stop < corrected_entry:
                    corrected_stop = corrected_entry * 1.03
            else:
                if corrected_stop > corrected_entry:
                    corrected_stop = corrected_entry * 0.97
            
            target = calculate_risk_reward(corrected_entry, corrected_stop, direction)
            
            reasoning_parts = []
            for sig in ticker_signal_list[:5]:
                reasoning_parts.append(f"{sig['strategy']}: {sig['signal']}")
            
            meta_reason = ticker_signal_list[0].get("meta_reason", "")
            if meta_reason:
                reasoning_parts.append(f"Meta: {meta_reason}")
            
            reasoning = ". ".join(reasoning_parts)
            
            ticker_scores.append({
                "ticker": ticker,
                "stock_price": f"${ticker_signal_list[0]['stock_price']:.2f}",
                "type": trade_type,
                "direction": direction,
                "category": trade_category,
                "strategies_triggered": triggered_strategies,
                "entry_price": round(corrected_entry, 2),
                "stop_loss": round(corrected_stop, 2),
                "take_profit": target,
                "holding_period": holding_period,
                "confidence_score": min(int(composite_score), 100),
                "reasoning": reasoning,
                "is_sp500": ticker in self.sp500_tickers
            })
        
        ticker_scores.sort(key=lambda x: (x["confidence_score"], len(x["strategies_triggered"])), reverse=True)
        
        sp500_swing = [ts for ts in ticker_scores if ts["is_sp500"] and ts["category"] == "SWING"][:10]
        sp500_intraday = [ts for ts in ticker_scores if ts["is_sp500"] and ts["category"] == "INTRADAY"][:10]
        other_swing = [ts for ts in ticker_scores if not ts["is_sp500"] and ts["category"] == "SWING"][:10]
        other_intraday = [ts for ts in ticker_scores if not ts["is_sp500"] and ts["category"] == "INTRADAY"][:10]
        
        final_scores = sp500_swing + sp500_intraday + other_swing + other_intraday
        
        recommendations = []
        for i, ts in enumerate(final_scores, 1):
            recommendations.append(Recommendation(
                rank=i,
                ticker=ts["ticker"],
                stock_price=ts["stock_price"],
                type=ts["type"],
                strategies_triggered=ts["strategies_triggered"],
                entry_price=ts["entry_price"],
                stop_loss=ts["stop_loss"],
                take_profit=ts["take_profit"],
                holding_period=ts["holding_period"],
                confidence_score=ts["confidence_score"],
                reasoning=ts["reasoning"],
                is_sp500=ts["is_sp500"]
            ))
        
        return recommendations


_scanner_instance = None

def get_scanner() -> Scanner:
    global _scanner_instance
    if _scanner_instance is None:
        _scanner_instance = Scanner()
    return _scanner_instance
