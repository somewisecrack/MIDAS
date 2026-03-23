#!/bin/bash
# Deploy MIDAS to Google Cloud Run
# Usage: ./deploy.sh <project-id> [region]

set -e

PROJECT_ID="${1:-}"
REGION="${2:-us-central1}"

if [ -z "$PROJECT_ID" ]; then
    echo "Usage: ./deploy.sh <project-id> [region]"
    echo "Example: ./deploy.sh my-project-123 us-central1"
    exit 1
fi

SERVICE_NAME="midas"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "=========================================="
echo "  MIDAS - GCP Deployment"
echo "=========================================="
echo "  Project: ${PROJECT_ID}"
echo "  Region:  ${REGION}"
echo "=========================================="

# Authenticate
echo ""
echo "[1/5] Checking GCP authentication..."
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "Error: Not authenticated to GCP"
    echo "Run: gcloud auth login"
    exit 1
fi
gcloud config set project $PROJECT_ID

# Enable APIs
echo ""
echo "[2/5] Enabling GCP APIs..."
gcloud services enable run.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com --quiet

# Create secrets (set your own values)
echo ""
echo "[3/5] Creating secrets in Secret Manager..."
echo "  Note: Set SMTP_EMAIL and SMTP_PASSWORD secrets in Secret Manager:"
echo "  gcloud secrets create smtp-email --data-file=-"
echo "  gcloud secrets create smtp-password --data-file=-"
read -p "  Press Enter after you've created the secrets..."
echo "  (Or set them via Cloud Console: https://console.cloud.google.com/security/secret-manager)"

# Build the image
echo ""
echo "[4/5] Building Docker image..."
gcloud builds submit --tag ${IMAGE_NAME} --timeout=10m --quiet

# Deploy to Cloud Run
echo ""
echo "[5/5] Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME} \
    --platform managed \
    --region ${REGION} \
    --no-allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --timeout 600s \
    --max-instances 1 \
    --set-env-vars USE_TLS=true \
    --set-secrets SMTP_EMAIL=smtp-email:latest,SMTP_PASSWORD=smtp-password:latest \
    --quiet

# Ensure manual curl and Cloud Scheduler can invoke the service
gcloud run services add-iam-policy-binding ${SERVICE_NAME} \
    --region ${REGION} \
    --member="allUsers" \
    --role="roles/run.invoker" \
    --quiet

# Get service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --platform managed --region ${REGION} --format 'value(status.url)' 2>/dev/null)

echo ""
echo "=========================================="
echo "  Deployment Complete!"
echo "=========================================="
echo ""
echo "Service URL: ${SERVICE_URL}"
echo ""

# Set up Cloud Scheduler
echo "Setting up Cloud Scheduler for 4 PM ET on weekdays..."
if gcloud scheduler jobs describe daily-scan --location ${REGION} >/dev/null 2>&1; then
    gcloud scheduler jobs update http daily-scan \
        --location=${REGION} \
        --schedule="0 21 * * 1-5" \
        --uri="${SERVICE_URL}/scan" \
        --http-method=POST \
        --time-zone="America/New_York" \
        --quiet
else
    gcloud scheduler jobs create http daily-scan \
        --location=${REGION} \
        --schedule="0 21 * * 1-5" \
        --uri="${SERVICE_URL}/scan" \
        --http-method=POST \
        --time-zone="America/New_York" \
        --quiet
fi

echo ""
echo "=========================================="
echo "  Next Steps"
echo "=========================================="
echo ""
echo "1. Test the scan manually:"
echo "   curl -X POST ${SERVICE_URL}/scan"
echo ""
echo "2. Check scheduler status:"
echo "   gcloud scheduler jobs describe daily-scan"
echo ""
echo "3. View logs:"
echo "   gcloud run services logs read ${SERVICE_NAME} --region ${REGION}"
echo ""
