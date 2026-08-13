# Production Dockerfile for Sentinel Risk Engine FastAPI Backend
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy python dependency specifications
COPY requirements.txt pyproject.toml ./

# Install python dependencies into wheel cache
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir uvicorn gunicorn

# Production runtime stage
FROM python:3.11-slim AS runner

WORKDIR /app

# Install runtime system libraries (including libgomp1 for ARM64 LightGBM execution)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*


# Copy installed python site-packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source code and model artifacts
COPY src/ /app/src/
COPY models/ /app/models/
COPY configs/ /app/configs/
COPY pyproject.toml /app/

# Set PYTHONPATH environment variable
ENV PYTHONPATH=/app:/app/src
ENV PYTHONUNBUFFERED=1

# Create non-root system user for security
RUN adduser --system --group --no-create-home sentinel && \
    chown -R sentinel:sentinel /app

USER sentinel

# Container healthcheck using lightweight GET /health endpoint
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Production server entrypoint with dynamic PORT support for cloud hosts (Render/Northflank/Koyeb)
CMD ["sh", "-c", "exec uvicorn src.fraud_detection.api.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
