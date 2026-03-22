import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import yfinance as yf
from pathlib import Path
import sys
import os
import time
import requests
from io import StringIO

sys.path.insert(0, str(Path(__file__).parent.parent))
from agent.config import DATA_FILES, REFRESH_THRESHOLD_HOURS


def get_sp500_tickers() -> list:
    try:
        url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv"
        response = requests.get(url, timeout=10)
        df = pd.read_csv(StringIO(response.text))
        tickers = df["Symbol"].tolist()
        tickers = [t.replace(".", "-") for t in tickers]
        return sorted(tickers)
    except Exception as e:
        print(f"Failed to fetch S&P 500 list: {e}")
        return ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM", "V", "JNJ",
                "WMT", "PG", "MA", "HD", "CVX", "ABBV", "MRK", "PEP", "KO", "COST",
                "AVGO", "CSCO", "ACN", "ABT", "DHR", "BAC", "CRM", "ADBE", "CMCSA", "NKE",
                "TXN", "PM", "NEE", "BMY", "QCOM", "LOW", "AMGN", "IBM", "SBUX", "GE",
                "ORCL", "HON", "UNP", "INTU", "RTX", "AMAT", "LRCX", "ISRG", "MDLZ", "ADI",
                "SYK", "TJX", "ZTS", "ADP", "BLK", "SCHW", "VRTX", "TMUS", "USB", "SO",
                "GD", "DE", "NSC", "CME", "BSX", "FI", "ELV", "APD", "FIS", "ICE", "WM",
                "EOG", "MCK", "KLAC", "AON", "HCA", "CL", "PNC", "TTE", "BDX", "SHW",
                "PSA", "DG", "EQIX", "EMR", "NOC", "MCO", "ETN", "F", "APH", "COF", "MSI",
                "CARR", "AJG", "HUM", "TEL", "FCX", "ORLY", "SNPS", "CDNS", "TDG", "GM",
                "AMT", "DUK", "SPG", "EW", "ECL", "NEM", "CNC", "AEP", "ALL", "ROP", "PRU",
                "PSX", "HSY", "VRSK", "MPC", "AIG", "TRV", "JCI", "LHX", "CTVA", "FTNT",
                "PAYX", "OI", "SRE", "MNST", "WELL", "D", "AMP", "O", "ROK", "IDXX", "AME",
                "PCAR", "EXC", "MSCI", "CTAS", "RSG", "PCG", "VLO", "PPG", "FISV", "CCI",
                "FAST", "BKR", "TGT", "AFL", "GIS", "KMB", "XEL", "ES", "WMB", "TSCO",
                "GPN", "DHI", "APTV", "WEC", "MCHP", "OTIS", "CPRT", "TFC", "DLR", "MS",
                "STZ", "BK", "CM", "DOV", "FDX", "IR", "KDP", "GLW", "KEYS", "ODFL", "PWR",
                "TSN", "VRSN", "WAB", "HWM", "IQV", "MLM", "NTAP", "PFG", "TYL", "DFS",
                "EBAY", "NDAQ", "SWKS", "TER", "ACGL", "ALGN", "ANSS", "BALL", "BRO",
                "CBOE", "CDW", "CHRW", "CINF", "CLX", "COO", "CTSH", "CPT", "DGX", "DLTR",
                "ED", "EIX", "EQR", "EXPD", "FANG", "FITB", "GRMN", "HAS", "HII", "HOLX",
                "HST", "IFF", "INFO", "INVH", "IT", "JBHT", "KHC", "KIM", "LEN", "LYB",
                "MAR", "MAS", "MKC", "MPWR", "MSM", "MTD", "NCLH", "NDSN", "NVR", "OKE",
                "OMC", "OSK", "PAYC", "PNR", "POOL", "RCL", "RF", "RMD", "ROL", "RVTY",
                "SBNY", "SBAC", "SJM", "SWK", "SYF", "TAP", "TFX", "TPR", "TTWO", "UDR",
                "ULTA", "VMC", "VTR", "WAT", "WDC", "WHR", "WST", "WYNN", "ZBH", "ZION",
                "ABNB", "ALB", "AMD", "APA", "ATO", "AVB", "AAL", "ADSK", "BA", "BIIB",
                "BAX", "BBY", "BWA", "BEN", "CNP", "CFG", "CMA", "CNC", "COTY", "CSX",
                "CVS", "DAL", "DG", "DPZ", "DRI", "DTE", "DVN", "EA", "ECL", "EFX",
                "ENPH", "EOG", "EPAM", "EVRG", "EXC", "EXPE", "FAST", "FCX", "FDS", "FE",
                "FTNT", "GD", "GILD", "GIS", "GM", "GNRC", "GOOG", "GOOGL", "GS", "GWW",
                "HAL", "HBAN", "HCA", "HD", "HES", "HIG", "HON", "HPE", "HPQ", "HRB",
                "HRL", "HSY", "HUM", "IBM", "ICE", "IDXX", "IEX", "INCY", "INTC", "INTU",
                "IQV", "IR", "IRM", "ISRG", "JCI", "JNJ", "JPM", "KEYS", "KHC", "KLAC",
                "KMB", "KMX", "KO", "KR", "LEG", "LEN", "LH", "LLY", "LMT", "LNC", "LNT",
                "LOW", "LUV", "LW", "LYB", "M", "MAA", "MAR", "MAS", "MCD", "MCHP", "MCK",
                "MCO", "MDLZ", "MDT", "MET", "MGM", "MHK", "MKC", "MMC", "MMM", "MNST",
                "MO", "MOS", "MPC", "MRK", "MS", "MSCI", "MSFT", "MTB", "MU", "NDAQ",
                "NEE", "NEM", "NFLX", "NI", "NKE", "NOC", "NOW", "NSC", "NTAP", "NTRS",
                "NUE", "NVDA", "NVR", "NWL", "O", "OI", "OKE", "OMC", "ORCL", "ORLY", "OXY",
                "PAYX", "PCAR", "PCG", "PEG", "PEP", "PFE", "PFG", "PG", "PGR", "PH",
                "PLD", "PM", "PNC", "PNR", "PODD", "POOL", "PRGO", "PRU", "PSA", "PWR",
                "PYPL", "QCOM", "RCL", "REG", "RF", "RHI", "RJF", "RL", "RMD", "ROK",
                "ROL", "ROP", "ROST", "RSG", "RTX", "SBAC", "SBUX", "SCHW", "SJM", "SLB",
                "SM", "SNA", "SNPS", "SO", "SPG", "SPGI", "STZ", "SWK", "SWKS", "SYF",
                "SYK", "T", "TAP", "TEAM", "TEL", "TFC", "TFX", "TJX", "TMO", "TMUS",
                "TROW", "TRV", "TSCO", "TSLA", "TT", "TTWO", "TXN", "UAL", "ULTA", "UNH",
                "UNP", "UPS", "URI", "USB", "V", "VFC", "VLO", "VMC", "VRSK", "VRSN",
                "VRTX", "VZ", "WAB", "WBA", "WDC", "WEC", "WELL", "WFC", "WMB", "WMT",
                "WRB", "WST", "WTW", "XEL", "XOM", "YUM", "ZBH", "ZION", "ZM", "ZS",
                "ZTS", "BRK-B", "BF-B"]


S_P_500_TICKERS = get_sp500_tickers()


def load_all_tickers() -> Tuple[pd.DataFrame, list, list]:
    ensure_data_dir()
    df = load_ticker_data("daily")
    
    if df.empty:
        return pd.DataFrame(), S_P_500_TICKERS, []
    
    all_tickers = sorted(df["Ticker"].unique().tolist())
    sp500_tickers = [t for t in all_tickers if t in S_P_500_TICKERS]
    other_tickers = [t for t in all_tickers if t not in S_P_500_TICKERS]
    
    return df, sp500_tickers, other_tickers


def ensure_data_dir():
    for key, filepath in DATA_FILES.items():
        filepath.parent.mkdir(parents=True, exist_ok=True)


def load_ticker_data(timeframe: str = "daily") -> pd.DataFrame:
    filepath = DATA_FILES.get(timeframe)
    if not filepath or not filepath.exists():
        return pd.DataFrame()
    
    df = pd.read_csv(filepath)
    if df.empty:
        return df
    
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
    elif "Datetime" in df.columns:
        df = df.rename(columns={"Datetime": "Date"})
        df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
    
    return df


def check_data_freshness(df: pd.DataFrame) -> Tuple[datetime, str, bool]:
    latest_date = df["Date"].max()
    now = datetime.now()
    age = now - latest_date
    
    if age.total_seconds() < 3600:
        freshness = "Fresh"
        is_stale = False
    elif age.total_seconds() < REFRESH_THRESHOLD_HOURS * 3600:
        hours = int(age.total_seconds() / 3600)
        freshness = f"{hours} hour{'s' if hours > 1 else ''} ago"
        is_stale = False
    elif age.days < 1:
        freshness = "Less than 1 day ago"
        is_stale = True
    else:
        freshness = f"{age.days} days ago"
        is_stale = True
    
    return latest_date, freshness, is_stale


def update_data_from_yfinance(tickers: list, progress_callback=None, force_full_refresh: bool = True) -> Dict:
    from tqdm import tqdm
    
    results = {"success": 0, "failed": 0, "errors": [], "updated": False}
    
    ensure_data_dir()
    filepath = DATA_FILES["daily"]
    
    if force_full_refresh:
        start_fetch = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        df_existing = pd.DataFrame()
    else:
        df_existing = pd.DataFrame()
        if filepath.exists():
            try:
                df_existing = pd.read_csv(filepath)
            except:
                pass
        
        if not df_existing.empty and "Date" in df_existing.columns:
            df_existing["Date"] = pd.to_datetime(df_existing["Date"]).dt.tz_localize(None)
            latest_date = df_existing["Date"].max()
            start_fetch = latest_date.strftime("%Y-%m-%d")
        else:
            start_fetch = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    
    batch_size = 50
    all_new_data = []
    
    for i in tqdm(range(0, len(tickers), batch_size)):
        batch = tickers[i:i + batch_size]
        
        try:
            data = yf.download(
                batch, 
                start=start_fetch, 
                interval="1d", 
                group_by="ticker",
                threads=True, 
                progress=False
            )
            
            if data.empty:
                continue
                
            for ticker in batch:
                try:
                    if len(batch) == 1:
                        t_df = data.copy()
                    elif ticker in data.columns.get_level_values(0):
                        t_df = data[ticker].dropna(how="all").reset_index()
                    else:
                        continue
                    
                    if t_df.empty:
                        continue
                    
                    if "Datetime" in t_df.columns:
                        t_df = t_df.rename(columns={"Datetime": "Date"})
                    elif isinstance(t_df.index, pd.DatetimeIndex):
                        t_df = t_df.reset_index()
                        t_df = t_df.rename(columns={"index": "Date"})
                    
                    t_df["Ticker"] = ticker
                    all_new_data.append(t_df)
                    results["success"] += 1
                    
                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append(f"{ticker}: {str(e)}")
        
        except Exception as e:
            results["errors"].append(f"Batch {i}: {str(e)}")
        
        time.sleep(0.5)
    
    if all_new_data:
        new_df = pd.concat(all_new_data, ignore_index=True)
        new_df["Date"] = pd.to_datetime(new_df["Date"])
        
        final_df = pd.concat([df_existing, new_df], ignore_index=True)
        final_df = final_df.drop_duplicates(
            subset=["Ticker", "Date"], 
            keep="last"
        ).sort_values(["Ticker", "Date"])
        
        final_df.to_csv(filepath, index=False)
        results["updated"] = True
    else:
        results["updated"] = False
    
    return results


def get_stock_price(ticker: str, df: pd.DataFrame) -> float:
    ticker_data = df[df["Ticker"] == ticker].sort_values("Date")
    if ticker_data.empty:
        return 0.0
    return float(ticker_data.iloc[-1]["Close"])


def get_price_range(price: float) -> str:
    if price < 5:
        return "penny"
    elif price < 20:
        return "low"
    elif price < 100:
        return "mid"
    else:
        return "high"
