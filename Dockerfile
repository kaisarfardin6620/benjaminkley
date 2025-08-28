# Dockerfile (FINAL VERSION)

# --- Stage 1: Builder ---
FROM python:3.12-slim AS builder
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libgl1-mesa-glx \
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
RUN addgroup --system app && adduser --system --group app
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY . .
RUN chown -R app:app /app
USER app

# --- THIS IS THE CORRECTED PART ---
# Copy the entrypoint script and make it executable
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# Expose port 8000. Railway will map its public port to this.
EXPOSE 8000

# The ENTRYPOINT will run our script, which handles migrations and starts our services.
ENTRYPOINT ["/app/docker-entrypoint.sh"]