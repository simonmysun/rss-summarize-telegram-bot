# rss-summarize-telegram-bot

This is a telegram bot that summarizes the content of an RSS feed and sends it to a telegram channel.

### Configuration

Please add the RSS feeds to `state.json` and set environment variables in `.env`. `state.json.example` and `.env.example` are provided as examples.

For outputs with other languages, please edit prompts under `./prompts`.

## Usage

```bash
docker compose up -d rss-summarize-telegram-bot
```