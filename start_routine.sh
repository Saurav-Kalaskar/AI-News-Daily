#!/bin/bash
# Start-up script for AI News Daily async bot.
# Ensures environment is loaded and starts the bot.

set -e

echo "Loading environment variables..."
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

echo "Starting services..."
# Start PostgreSQL and Redis (assumes Docker Compose is running)
# docker-compose up -d postgres redis

echo "Running the bot..."
python -m bot.main "$@"
