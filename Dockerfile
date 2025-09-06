# --- Stage 1: Builder ---
FROM python:3.12-slim AS builder
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Stage 2: Final Image ---
FROM python:3.12-slim
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
RUN addgroup --system app && adduser --system --group app
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY . .

# Copy and make the script executable BEFORE changing user
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# Create directories and set correct ownership before switching user
RUN mkdir -p /app/media /app/staticfiles && chown -R app:app /app/media /app/staticfiles

# Change ownership of the application code
RUN chown -R app:app /app

# Switch to the non-root user for security
USER app

EXPOSE 8000
CMD ["/app/docker-entrypoint.sh", "web"]