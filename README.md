# rss-summarize-telegram-bot

This is a telegram bot that summarizes the content of an RSS feed and sends it to a telegram channel. In my case, I use it to forward RSS feeds from https://hnrss.org/ to telegram channel [@HNTrending](https://t.me/hntrending) to get a fast preview of what is happening on Hacker news.

## Configuration

Please add the RSS feeds to `state.json` and set environment variables in `.env`. `state.json.example` and `.env.example` are provided as examples.

For outputs with other languages, please edit prompts under `./prompts`.


### Browserless Configuration

If you are using browserless to scrape the web pages, you need to set the `BROWSERLESS_API_TOKEN` and `BROWSERLESS_API_URL` in the `.env` file.

The `BROWSERLESS_API_URL` should be the REST API base URL of the browserless instance, e.g. `https://localhost:3000`, without the trailing slash.


## Usage

```bash
docker compose up -d rss-summarize-telegram-bot
```