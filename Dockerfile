# Dockerfile (FINAL CORRECTED VERSION)

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
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 && rm -rf /var/lib/apt/lists/*
RUN addgroup --system app && adduser --system --group app
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY . .

# --- START OF THE FIX ---
# We will copy and make the script executable BEFORE changing user.
# As the 'root' user, we have permission to do this.
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh
# --- END OF THE FIX ---

# Now, change ownership of all files to the new user.
RUN chown -R app:app /app

# Finally, switch to the non-root user.
USER app

# Expose port 8000. Railway will map its public port to this.
EXPOSE 8000

# The ENTRYPOINT will run our script, which handles migrations and starts our services.
ENTRYPOINT ["/app/docker-entrypoint.sh"]