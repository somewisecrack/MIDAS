FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for yfinance
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and data
COPY agent/ ./agent/
COPY data/ ./data/

# Set environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Run as Cloud Run service (listens on PORT env var)
CMD ["python", "-m", "agent.main", "--cloud-run"]
