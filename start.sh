#!/bin/bash

# Export environment variables for cron
printenv > /etc/environment

# Launch continuous 24/7 scripts from the src directory
uv run src/line-translate-bot.py &

# Run cron in the foreground
exec cron -f
