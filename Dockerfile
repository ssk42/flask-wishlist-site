# Multi-stage build for optimized production image

# Stage 1: Builder
FROM python:3.11-slim-bookworm as builder

WORKDIR /app

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    python3-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt .
# High retry/timeout values: the deploy box's PyPI link is slow and flaky and
# pip's 15s default times out mid-download, aborting builds.
RUN pip install --no-cache-dir --retries 20 --timeout 120 -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim-bookworm

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install Playwright browsers and dependencies BEFORE copying application
# code, so a source-only change doesn't invalidate the browser layer (a
# ~170MB re-download on every deploy).
# Ensure we have the necessary system dependencies for chromium.
# PLAYWRIGHT_BROWSERS_PATH pins a fixed, HOME-independent location: the build
# installs as root (HOME=/root) but the runtime runs as appuser, so the default
# ~/.cache/ms-playwright would resolve to a different directory at runtime and
# every browser launch would fail with 'Executable doesn't exist'.
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN playwright install --with-deps chromium

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/', timeout=2)" || exit 1

# Default command (can be overridden)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "60", "app:app"]
