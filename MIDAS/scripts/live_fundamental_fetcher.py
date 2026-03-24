import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import os

def get_quarterly_fundamentals_live(ticker):
    """
    Scrapes quarterly financials from StockAnalysis.com.
    Returns a DataFrame with Date, EPS, and Revenue for CAN SLIM verification.
    """
    url = f"https://stockanalysis.com/stocks/{ticker.lower()}/financials/quarterly/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"Error {response.status_code} for {ticker}")
            return None
        
        soup = BeautifulSoup(response.content, "html.parser")
        table = soup.find("table")
        if not table:
            return None
            
        rows = table.find_all("tr")
        
        # 1. Extract Dates/Periods
        header_row = rows[0].find_all(["th", "td"])
        periods = [h.get_text(strip=True) for h in header_row[1:]]
        
        # 2. Extract specific rows (EPS and Revenue)
        data = {"Period": periods}
        
        for row in rows:
            label = row.find(["th", "td"]).get_text(strip=True)
            
            if "EPS (Diluted)" == label:
                values = [v.get_text(strip=True).replace("$", "").replace(",", "") for v in row.find_all("td")[1:]]
                data["EPS"] = [float(v) if v and v != "-" else 0.0 for v in values]
                
            if "Revenue" == label:
                values = [v.get_text(strip=True).replace("$", "").replace(",", "").replace("B", "e9").replace("M", "e6") for v in row.find_all("td")[1:]]
                # Convert B/M to numbers
                parsed_rev = []
                for v in values:
                    try:
                        parsed_rev.append(float(pd.eval(v)) if v and v != "-" else 0.0)
                    except:
                        parsed_rev.append(0.0)
                data["Revenue"] = parsed_rev

        if "EPS" in data and "Revenue" in data:
            df = pd.DataFrame(data)
            return df
            
        return None
    except Exception as e:
        print(f"Scrape Error for {ticker}: {e}")
        return None

if __name__ == "__main__":
    test_ticker = "AAPL"
    print(f"Testing live quarterly fetch for {test_ticker}...")
    df = get_quarterly_fundamentals_live(test_ticker)
    if df is not None:
        print(df.head(10))
    else:
        print("Failed to fetch data.")
