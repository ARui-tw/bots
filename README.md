# Automation Hub

A centralized, Dockerized environment for running Python-based bots, webhooks, and scheduled automation tasks. It uses `uv` with PEP 723 inline script metadata to manage dependencies dynamically without `requirements.txt` or `pyproject.toml`.

Designed to be deployed on a Proxmox LXC container using pre-built images from GitHub Container Registry (GHCR).

## Included Services

*   **LINE Translate Bot** (`src/line-translate-bot.py`): A 24/7 webhook server that auto-translates LINE messages between English/Chinese and Indonesian using DeepL.
*   **Weather Bot** (`src/weather-bot.py`): A scheduled cron job that fetches Taiwan CWA API data and sends daily temperature reports via Telegram.
*   **Kimai Report Bot** (`src/kimai-report.py`): A scheduled cron job that fetches timesheet data from Kimai and sends daily/weekly summaries via Telegram.
*   **Podsync**: Pre-built container for podcast syncing.
*   **DMARC Report Viewer**: Pre-built container for parsing DMARC emails.

## Directory Structure

```text
.
├── .github/workflows/   # CI/CD image build pipeline
├── src/                 # Python script source code
├── crontab              # Scheduled cron jobs definition
├── docker-compose.yml   # Multi-container orchestration
├── Dockerfile           # uv-based Python 3.12 image setup
├── start.sh             # Container entrypoint script
└── .env.example         # Environment variable template

```

## CI/CD Pipeline (Build Phase)

This repository is configured with a GitHub Action (`deploy.yml`). Pushing to the `master` branch automatically triggers a cloud build. GitHub will compile the Docker image, cache the Python dependencies, and push the final image to `ghcr.io`.

## Setup & Deployment (Proxmox Server)

Since GitHub handles the build process, your Proxmox server only needs to pull and run the compiled image.

1. **Configure Environment:**
Copy the example environment file and fill in your API keys.

```bash
   cp .env.example .env
   # Edit .env with your favorite editor

```

2. **Authenticate with GitHub (If repository is private):**
Generate a Classic Personal Access Token (PAT) with `read:packages` permissions on GitHub, then log in on your Proxmox server:

```bash
   docker login ghcr.io -u your-github-username

```

3. **Deploy or Update:**
Whenever a new build finishes on GitHub, pull the latest image and recreate the container:

```bash
   docker compose pull automation-hub
   docker compose up -d

```

## Adding New Scripts

Dependencies are managed using inline metadata. Add the `/// script` block to the top of any new `.py` file. Remember to include a `--help` catch at the bottom of the script so the GitHub Action can cache the dependencies without triggering the actual code during the build phase.

```python
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "requests",
# ]
# ///
import sys
import requests

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("My new bot description.")
        sys.exit(0)
    
    print("Running script...")

```

* **For 24/7 background scripts (Bots/Webhooks):** Add the execution command to `start.sh` (e.g., `uv run src/my-bot.py &`) and update the `Dockerfile` pre-cache list.
* **For scheduled scripts:** Add the cron timing to the `crontab` file (e.g., `0 9 * * * cd /app && uv run src/my-script.py > /proc/1/fd/1 2>&1`) and update the `Dockerfile` pre-cache list. Make sure `crontab` always ends with an empty line.
