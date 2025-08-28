# Dockerfile (FINAL CORRECTED VERSION v2)

# --- Stage 1: Builder ---
# This stage correctly installs all dependencies. It does not need to change.
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

# --- START OF THE FIX ---
# We must install ALL required system libraries in the final runtime stage.
# The previous version was missing libglib2.0-0 here.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
# --- END OF THE FIX ---

RUN addgroup --system app && adduser --system --group app
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY . .

# Copy and make the script executable BEFORE changing user
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# Change ownership of all files to the new user
RUN chown -R app:app /app

# Switch to the non-root user
USER app

EXPOSE 8000
ENTRYPOINT ["/app/docker-entrypoint.sh"]