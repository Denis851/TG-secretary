# Build stage
FROM python:3.11.7-slim as builder

WORKDIR /app

# Install build dependencies with updated configuration
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    python3-dev \
    gcc \
    libc6-dev \
    libffi-dev \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Upgrade pip and install build tools
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir wheel setuptools

# Install dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.11.7-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p data logs && \
    chown -R appuser:appuser data logs

# Switch to non-root user
USER appuser

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:$PORT/health || exit 1

# Run the application
CMD ["python", "main.py"] 