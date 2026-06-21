#!/bin/bash
# Trigger Cloud Run Trading Agent

SERVICE_URL="your-cloud-run-url"

echo "Triggering Trading Agent scan..."
curl -X POST ${SERVICE_URL}/scan

echo ""
echo "Scan triggered successfully!"
