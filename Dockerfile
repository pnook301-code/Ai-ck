FROM python:3.12-slim AS base

WORKDIR /app

# Security: non-root user
RUN groupadd -r ck && useradd -r -g ck -d /app -s /sbin/nologin ck

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libsm6 libxext6 libgl1-mesa-glx git curl && \
    rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[prod]" 2>/dev/null || \
    pip install --no-cache-dir numpy opencv-python-headless \
    fastapi uvicorn pydantic httpx python-jose[cryptography] \
    passlib[bcrypt] python-multipart

# Copy application
COPY kernel/ kernel/
COPY knowledge/ knowledge/
COPY deploy/ deploy/

# Security: no root
USER ck

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

EXPOSE 8080

CMD ["python", "-m", "uvicorn", "kernel.api:app", "--host", "0.0.0.0", "--port", "8080"]
