# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies with optimized settings
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    python3-dev \
    gcc \
    libc6-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install Python dependencies
COPY requirements.txt .

# Upgrade pip and install build tools
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir wheel setuptools

# Install dependencies in groups
RUN pip install --no-cache-dir \
    aiogram==3.2.0 \
    python-dotenv==1.0.0 \
    APScheduler==3.10.1 \
    pytz==2023.3 \
    python-dateutil==2.8.2 \
    aiohttp==3.8.5 \
    Pillow==9.5.0 \
    redis==4.6.0 \
    pydantic==1.10.13 \
    structlog==23.1.0 \
    aiohttp-cors==0.7.0 \
    python-json-logger==2.0.7 \
    typing-extensions==4.7.1 \
    asyncio==3.4.3

# Install reportlab separately with its dependencies
RUN pip install --no-cache-dir reportlab==3.6.12

# Install test dependencies separately
RUN pip install --no-cache-dir \
    pytest==7.4.3 \
    pytest-asyncio==0.21.1 \
    sphinx==7.1.2

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpq5 \
    libffi7 \
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