# MIDAS — Swing Strategy Test Bench

MIDAS is a state-of-the-art Swing Strategy Test Bench designed to backtest, analyze, and discover trading patterns across the stock market. Powered by an interactive web UI, robust Python backend, and Gemma-based AI, MIDAS allows traders to batch backtest dozens of strategies across hundreds of tickers effortlessly.

## Key Features

- **Batch Backtesting Engine**: Backtest up to 100 tickers simultaneously against multiple strategies in a single click. 
- **Portfolio-Level Reporting**: Get aggregated stats (Win Rate, Profit Factor, Total Return, Max Drawdown) for your entire batch run, alongside a ticker-by-ticker breakdown.
- **Interactive Charting**: Built with Lightweight Charts. Seamlessly navigate price action with native Zoom, Pan, and Reset controls. Automatically overlay Entry and Exit signals on the chart.
- **AI-Powered Insights**: Integrated with Ollama/Gemma to automatically analyze backtest results, discover patterns, and answer questions via an interactive multi-modal chat window.
- **Extensive Strategy Library**: Over 20 built-in swing and intraday strategies including Turtle Systems, VPA/VSA shakeouts, Minervini SEPA, Camarilla breakouts, and more.
- **Auto-Fetching**: Missing ticker data? MIDAS automatically fetches and caches missing OHLCV data from Yahoo Finance on the fly.
- **Local Persistence**: All trades, runs, and historical data are stored natively in an optimized SQLite WAL-mode database.

## Installation & Setup

### 1. Requirements
- Python 3.10+
- macOS/Linux
- [Ollama](https://ollama.com/) (installed and running locally to use the AI chat features)
- Gemma Model (run `ollama run gemma:2b` or `gemma:7b` to pull the models locally)

### 2. Environment Setup
```bash
# Clone the repository
git clone https://github.com/somewisecrack/MIDAS.git
cd MIDAS

# Create virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Run the App
```bash
./run.sh
```
By default, the server will start on `http://localhost:7432`.

## How to Use

1. **Load Data**: Enter a ticker in the search bar and click `Load Data`, or use the **[📄 Batch]** button to paste up to 100 tickers at once.
2. **Select Strategies**: Pick one or more strategies from the left-side panel.
3. **Run Backtest**: Click the gold **Run Backtest** button.
4. **Analyze**: Use the right-side panel to view detailed trade logs, or click the **Chat** tab to ask the local Gemma AI to interpret your results and suggest optimizations.

## Architecture

- **Frontend**: Vanilla JavaScript + HTML/CSS (Glassmorphic dark-mode UI). 
- **Backend**: Python (FastAPI). 
- **Database**: SQLite (`midas.db`) powered by SQLAlchemy ORM.
- **Data Source**: `yfinance` for automated OHLCV loading.
- **AI**: Local execution via `httpx` forwarding to `http://localhost:11434` (Ollama).

## License
MIT
