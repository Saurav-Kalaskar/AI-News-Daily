# AI News Daily

An automated daily briefing service that collects AI news from multiple sources, synthesizes it using a large language model (LLM), and delivers a concise digest to a Telegram channel.

## What It Does

1. **Collects** AI news from Hacker News, arXiv, TechCrunch, MIT Technology Review, and VentureBeat
2. **Deduplicates** stories against a running history to avoid repeats
3. **Synthesizes** the top 5 most impactful items into a structured briefing via LLM
4. **Delivers** the briefing directly to your Telegram channel

## Prerequisites

- Python 3.10 or higher
- A Telegram bot and bot token
- A Telegram channel (or group) ID to receive messages
- An NVIDIA API key (the system uses NVIDIA's hosted LLM API with the `meta/llama-3.1-70b-instruct` model)

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/ai-news-daily.git
cd ai-news-daily
```

### 2. Create a `.env` File

Create a `.env` file in the project root:

```bash
touch .env
```

Add the following variables:

```env
# NVIDIA LLM API key (required)
LLM_API_KEY=your_nvidia_api_key_here

# Optional: override the base URL (defaults to NVIDIA's integrate API)
# LLM_BASE_URL=https://integrate.api.nvidia.com/v1

# Optional: override the model (defaults to meta/llama-3.1-70b-instruct)
# MODEL_NAME=meta/llama-3.1-70b-instruct

# Telegram bot token from @BotFather
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Telegram channel ID (e.g., -1001234567890 for channels, or a chat ID for groups)
TELEGRAM_CHANNEL_ID=your_telegram_channel_id_here

# Optional: max retries on LLM API failure (default: 3)
# MAX_RETRIES=3
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up GitHub Secrets (for GitHub Actions)

If you plan to run this via GitHub Actions, add the following secrets to your repository:

1. Go to **Settings > Secrets and variables > Actions** in your GitHub repository
2. Add each secret:

| Secret Name | Description |
|------------|-------------|
| `LLM_API_KEY` | Your NVIDIA API key |
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token (from @BotFather) |
| `TELEGRAM_CHANNEL_ID` | Your Telegram channel ID |

## Running Locally

```bash
python main.py
```

On a successful run, you will see output like:

```
Collecting from HN Firebase API...
Collecting from arXiv...
Collecting from RSS feeds...
Found X new stories
Sending briefing to Telegram...
Done.
```

A copy of each briefing is saved to `data/briefs/YYYY-MM-DD.md`.

## Running via GitHub Actions

The workflow runs automatically twice daily (9 AM and 9 PM UTC). To trigger it manually:

1. Go to the **Actions** tab in your GitHub repository
2. Select the **Daily AI News Brief** workflow
3. Click **Run workflow** and select the branch

State is persisted between runs by committing `data/seen_stories.json` and the `data/briefs/` directory back to the repository.

## Output Format

The bot sends a Telegram message with the following structure:

```
# TL;DR
One paragraph summary of the most significant AI development.

## Key Releases
- Item 1
- Item 2
...

## Developer Takeaways
- Item 1
- Item 2
...

## Sources
1. [Title](URL)
2. [Title](URL)
```

The message is formatted in Telegram Markdown. Only bold, italic, code, and link syntax are supported.