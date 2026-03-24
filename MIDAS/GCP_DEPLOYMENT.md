# Google Cloud Deployment Guide

Deploy the Trading Agent to Google Cloud Run for fully automated daily scans at 4 PM ET.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     GOOGLE CLOUD                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   Cloud Scheduler (4 PM ET weekdays) ──► Cloud Run          │
│                                              │               │
│                                              ▼               │
│                                      ┌─────────────┐        │
│                                      │  Trading    │        │
│                                      │  Agent      │        │
│                                      │  - Update   │        │
│                                      │    yfinance │        │
│                                      │  - Run 36   │        │
│                                      │    strategies│        │
│                                      │  - Send     │        │
│                                      │    Email    │        │
│                                      └─────────────┘        │
│                                              │               │
│                                              ▼               │
│                                    Email to thrissurkaarantrader@gmail.com
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Prerequisites

1. Google Cloud account with billing enabled
2. Google Cloud SDK: `brew install google-cloud-sdk`
3. Docker: `brew install --cask docker`
4. Run `gcloud auth login` and `gcloud config set project YOUR_PROJECT_ID`

## Quick Deploy

```bash
# One-command deployment
./deploy.sh your-project-id

# Example:
./deploy.sh my-trading-agent-123 us-central1
```

The deploy script will:
1. Authenticate with GCP
2. Enable required APIs
3. Create secrets in Secret Manager
4. Build Docker image
5. Deploy to Cloud Run
6. Set up Cloud Scheduler for 4 PM ET weekdays

## Manual Deployment (if needed)

### 1. Enable APIs
```bash
gcloud services enable run.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com
```

### 2. Create Secrets
```bash
echo -n "thrissurkaarantrader@gmail.com" | gcloud secrets create smtp-email --data-file=-
echo -n "rrezbfamajxetskn" | gcloud secrets create smtp-password --data-file=-
```

### 3. Build and Deploy
```bash
gcloud builds submit --tag gcr.io/PROJECT_ID/trading-agent
gcloud run deploy trading-agent \
    --image gcr.io/PROJECT_ID/trading-agent \
    --platform managed \
    --region us-central1 \
    --no-allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --timeout 600s \
    --max-instances 1 \
    --set-secrets SMTP_EMAIL=smtp-email:latest,SMTP_PASSWORD=smtp-password:latest
```

### 4. Set Up Scheduler
```bash
SERVICE_URL=$(gcloud run services describe trading-agent --region us-central1 --format 'value(status.url)')

gcloud scheduler jobs create http daily-scan \
    --schedule="0 21 * * 1-5" \
    --uri="${SERVICE_URL}/scan" \
    --http-method=POST \
    --time-zone="America/New_York"
```

## Usage

### Test Scan Manually
```bash
curl -X POST $(gcloud run services describe trading-agent --region us-central1 --format 'value(status.url)')/scan
```

### Check Scheduler
```bash
gcloud scheduler jobs describe daily-scan
gcloud scheduler jobs run daily-scan  # Run now
```

### View Logs
```bash
gcloud run services logs read trading-agent --region us-central1 --limit 50
```

### Update Deployment
```bash
./deploy.sh your-project-id
```

## Cost

| Resource | Monthly Usage | Est. Cost |
|----------|--------------|-----------|
| Cloud Run | ~20 min/day × 20 days | ~$0.50 |
| Cloud Build | ~1 min deploys | ~$0.10 |
| Cloud Scheduler | 20 jobs | Free |
| Secret Manager | 2 secrets | ~$0.12 |
| **Total** | | **~$0.72/month** |

## Troubleshooting

### "Permission denied" errors
```bash
gcloud auth login
gcloud auth application-default login
```

### Scan didn't run
```bash
# Check scheduler is enabled
gcloud scheduler jobs describe daily-scan

# Run manually
gcloud scheduler jobs run daily-scan
```

### Check logs
```bash
gcloud run services logs read trading-agent --region us-central1 --limit 100
```

### Delete and redeploy
```bash
gcloud run services delete trading-agent --region us-central1 --quiet
gcloud scheduler jobs delete daily-scan --quiet
./deploy.sh your-project-id
```

## Local Testing

```bash
# Build locally
docker build -t trading-agent .

# Run scan
docker run --rm \
  -e SMTP_EMAIL=thrissurkaarantrader@gmail.com \
  -e SMTP_PASSWORD=rrezbfamajxetskn \
  trading-agent
```
