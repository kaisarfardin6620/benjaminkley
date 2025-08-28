# Dockerfile (FINAL CORRECTED VERSION)

# --- Stage 1: Builder ---
FROM python:3.12-slim AS builder

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

# --- THIS IS THE CRITICAL FIX ---
# Replaced the obsolete 'libgl1-mesa-glx' with the modern 'libgl1' package.
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

# --- We also need to install the library here for the runtime ---
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 && rm -rf /var/lib/apt/lists/*

RUN addgroup --system app && adduser --system --group app

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY . .

RUN chown -R app:app /app
USER app

COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]