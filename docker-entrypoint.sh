#!/bin/sh
# docker-entrypoint.sh - Simple entrypoint

# Exit immediately if a command exits with a non-zero status.
set -e

# Set timezone
export TZ=UTC

# Create matplotlib cache directory
mkdir -p /tmp/matplotlib
export MPLCONFIGDIR=/tmp/matplotlib
export HOME=/tmp

# Activate the virtual environment
. /opt/venv/bin/activate

# Execute the command passed to the container
exec "$@"