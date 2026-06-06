# Automation Hub

A centralized, Dockerized environment for running Python-based bots, webhooks, and scheduled automation tasks. It uses `uv` with PEP 723 inline script metadata to manage dependencies dynamically without `requirements.txt` or `pyproject.toml`.

Designed to be deployed on a Proxmox LXC container via GitHub Actions.

## Included Services

*   **LINE Translate Bot** (`src/line-translate-bot.py`): A 24/7 webhook server that auto-translates LINE messages between English/Chinese and Indonesian using DeepL.
*   **Weather Bot** (`src/weather-bot.py`): A scheduled cron job that fetches Taiwan CWA API data and sends daily temperature reports via Telegram.

## Directory Structure

```text
.
├── .github/workflows/   # CI/CD deployment pipeline
├── src/                 # Python script source code
├── crontab              # Scheduled cron jobs definition
├── docker-compose.yml   # Multi-container orchestration
├── Dockerfile           # uv-based Python 3.12 image setup
├── start.sh             # Container entrypoint script
└── .env.example         # Environment variable template

```

## Setup & Execution

1. **Configure Environment:**
Copy the example environment file and fill in your API keys.

```bash
   cp .env.example .env
   # Edit .env with your favorite editor

```

2. **Deploy via Docker Compose:**

```bash
   docker compose up -d --build

```

## CI/CD Pipeline

This repository is configured with a GitHub Action (`deploy.yml`). Pushing to the `main` branch automatically triggers a deployment to the Proxmox LXC container via SSH.

Required GitHub Repository Secrets:

* `SSH_HOST`: Target IP address
* `SSH_USER`: SSH username (e.g., `root`)
* `SSH_KEY`: Private SSH key
* `SSH_PORT`: SSH port (default 22)

## Adding New Scripts

Dependencies are managed using inline metadata. Add the `/// script` block to the top of any new `.py` file:

```python
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "requests",
# ]
# ///
import requests

```

* **For 24/7 background scripts (Bots/Webhooks):** Add the execution command to `start.sh` (e.g., `uv run src/my-bot.py &`).
* **For scheduled scripts:** Add the cron timing to the `crontab` file (e.g., `0 9 * * * cd /app && uv run src/my-script.py > /proc/1/fd/1 2>&1`). Make sure `crontab` always ends with an empty line.
