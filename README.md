# MIDAS - Market Intelligence for Daily Automated Strategies

Automated trading strategy scanner that scans S&P 500 stocks and other tickers daily, identifies technical patterns using 36 strategies, and sends email recommendations.

## Features

- Scans 800+ stocks (S&P 500 + other tickers from bundled data)
- 36 trading strategies (22 swing + 14 intraday)
- Daily automated scan at 4 PM ET (weekdays)
- Email notifications with top 10 recommendations per category:
  - Top 10 S&P 500 SWING trades
  - Top 10 S&P 500 INTRADAY trades
  - Top 10 Other SWING trades
  - Top 10 Other INTRADAY trades
- Segregated results for S&P 500 vs other stocks (small cap, penny, etc.)

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your values:

```bash
cp agent/.env.example .env
```

Edit `.env`:
- `SMTP_EMAIL`: Your Gmail address
- `SMTP_PASSWORD`: Gmail App Password (16 characters)
- Set `NOTIFICATIONS_ENABLED=true` to enable emails

### 3. Get Gmail App Password

1. Enable 2-Factor Authentication on your Google Account
2. Go to https://myaccount.google.com/apppasswords
3. Create a new App Password for "Mail"
4. Copy the 16-character password to `.env`

### 4. Run Locally

```bash
python -m agent.main --scan-only
```

## Deployment to Google Cloud

### Prerequisites

- Google Cloud SDK installed (`gcloud`)
- Docker installed
- GCP project with billing enabled

### Deploy

```bash
./deploy.sh YOUR_PROJECT_ID us-central1
```

### Create Secrets

Before deploying, create your secrets in Secret Manager:

```bash
# Set your SMTP email
echo -n "your_email@gmail.com" | gcloud secrets create smtp-email --data-file=-

# Set your SMTP password (App Password)
echo -n "your_16_char_app_password" | gcloud secrets create smtp-password --data-file=-
```

### Verify Deployment

```bash
# Test the scan
curl -X POST https://YOUR_SERVICE_URL/scan

# Check health
curl https://YOUR_SERVICE_URL/health
```

## Architecture

```
agent/
├── main.py          # Entry point (local scan + Cloud Run server)
├── scanner.py      # Strategy engine, ranking, S&P 500 segregation
├── notifications.py # Email HTML formatting
├── data_loader.py  # Data loading, S&P 500 filtering, yfinance updates
├── models.py       # Pydantic models
├── api.py          # FastAPI endpoints
└── templates/      # Web UI templates (optional)

data/
└── tickers_ohlcv.csv  # Bundled ticker list (~838 tickers)

strategies/         # Trading strategy implementations
scripts/            # Utility scripts
results/           # Scan results (gitignored)
```

## Cloud Run Details

- **Service**: Runs on Google Cloud Run
- **Schedule**: Cloud Scheduler triggers at 4 PM ET on weekdays (21:00 UTC)
- **Resources**: 2 vCPU, 2GB RAM, 600s timeout
- **Scaling**: Max 1 instance (full refresh takes ~10 min)

## Data Refresh

- Daily full refresh downloads last 365 days for all tickers
- Uses `yfinance` for OHLCV data
- S&P 500 list fetched from GitHub dataset for accurate filtering

## License

MIT
