FROM ghcr.io/astral-sh/uv:python3.12-trixie-slim

RUN apt-get update && apt-get install -y cron tzdata && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

RUN crontab crontab
RUN chmod +x start.sh

# Pre-cache environments using the src/ path
RUN uv run src/weather-bot.py --help || true
RUN uv run src/line-translate-bot.py --help || true

CMD ["./start.sh"]
