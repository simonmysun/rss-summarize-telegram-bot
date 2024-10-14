# !/usr/bin/env python
# -*- coding: utf-8 -*

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

import os
import time
import json
import asyncio

import requests
import feedparser

from dotenv import load_dotenv
os.environ.clear()
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
STATE_FILE = os.getenv('STATE_FILE')
MAX_INPUT_LENGTH = int(os.getenv('MAX_INPUT_LENGTH'))

from utils.fetch_content import fetch_content
from utils.llm_api import complete
from utils.process_url import process_url
from utils.render_html import render
from utils.throttle import Throttle
throttle = Throttle()

prompt_template_summarize_content = ''
with open('prompts/summarize_content.txt', 'r') as f_prompt_template_summarize_content:
  prompt_template_summarize_content = f_prompt_template_summarize_content.read()

prompt_template_summarize_discussion = ''
with open('prompts/summarize_discussion.txt', 'r') as f_prompt_template_summarize_discussion:
  prompt_template_summarize_discussion = f_prompt_template_summarize_discussion.read()

prompt_template_summarize_comment = ''
with open('prompts/summarize_comment.txt', 'r') as f_prompt_template_summarize_comment:
  prompt_template_summarize_comment = f_prompt_template_summarize_comment.read()

def send_message_to_telegram(message):
  logger.info(f'Sending message to Telegram: {message[:50]}...')
  url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
  payload = {
    'chat_id': TELEGRAM_CHANNEL_ID,
    'text': message,
    'parse_mode': 'HTML'
  }
  response = requests.post(url, data=payload)
  logger.debug(response.text)
  return response.json()

def load_state():
  logger.info(f'Loading state from {STATE_FILE}')
  if os.path.exists(STATE_FILE):
    logger.info(f'File {STATE_FILE} exists')
    with open(STATE_FILE, 'r') as file:
      return json.load(file)
  else:
    logger.error(f'STATE_FILE="{STATE_FILE}" not found')
    raise Exception(f'STATE_FILE="{STATE_FILE}" not found')

def save_state():
  logger.info(f'Saving state to {STATE_FILE}')
  with open(STATE_FILE, 'w') as file:
    json.dump(STATE, file, indent=2, ensure_ascii=False)

async def check_rss_feed():
  logger.info('Checking RSS feed...')
  for feed in STATE['feeds']:
    logger.info(f'Checking feed: {feed["name"]}')
    logger.debug(f'Feed URL: {feed['url']}')
    feeds = feedparser.parse(feed['url'])
    for entry in sorted(feeds.entries, key=lambda x: x['published_parsed']):
      logger.debug(f'Entry: {json.dumps(entry)}')
      if entry.id not in feed['last_published']:
        logger.info(f'New entry found: {entry.title}')
        published_since = int((time.time() - time.mktime(entry.published_parsed)) / 60)
        
        message = f''
        message += f'<b>{feed['name']}</b>\n<a href="{entry.link}">{entry.title}</a>'
        message += f' ({published_since} minutes ago)'
        message += f'<blockquote expandable>{render(entry.summary)}</blockquote>'
        
        (uri, discussion_uri) = process_url(entry.comments)
        
        (final_url, content) = await fetch_content(uri.geturl())
        message += f'<b><a href="{final_url}">Content</a></b>\n'
        if len([line for line in content.split('\n') if line.strip()]) == 0:
          logger.error(f'No content or discussion is fetched. Task aborted.')
          message += f'{render('**ERROR**: No content or discussion is fetched. Task aborted.')}\n'
          content = f'{final_url}'
        prompt = ''
        if uri.netloc in ['news.ycombinator.com'] and not discussion_uri:
          logger.info('This is a comment on HN')
          prompt = prompt_template_summarize_comment.format(**{
            'content': content
          })
        else:
          prompt = prompt_template_summarize_content.format(**{
            'content': content
          })
        if len(prompt) > MAX_INPUT_LENGTH:
          message += f'{render('_content is truncated_')}\n'
          logger.info(f'Prompt length is ({len(prompt)} characters). Truncating to {MAX_INPUT_LENGTH} characters.')
          prompt = prompt[:MAX_INPUT_LENGTH]
          prompt += '\nTRUNCATED\n'
        # logger.info(f'Messages: {prompt}')
        result = []
        try:
          async for token in complete(prompt):
            result.append(token)
        except Exception as e:
          logger.error(f'ERROR: {repr(e)}')
          message += f'{''.join(result)}\n**ERROR**: LLM API request failed: {repr(e)}'
        if len(result) == 0:
          logger.error('No result returned.')
          message += f'{render('**ERROR**: No result returned.')}\n'
        else:
          message += f'<blockquote expandable>{render(''.join(result))}</blockquote>'

        discussion = ''
        if discussion_uri:
          message += f'<b><a href="{discussion_uri.geturl()}">Discussion</a></b>\n'
          (final_url, discussion) = await fetch_content(discussion_uri.geturl())
          if len([line for line in discussion.split('\n') if line.strip()]) == 0:
            logger.error(f'No discussion is fetched. Task aborted.')
            message += f'{render('**ERROR**: No discussion is fetched. Task aborted.')}\n'
            continue
          prompt = prompt_template_summarize_discussion.format(**{
            'content': ''.join(result),
            'discussion': discussion
          })
          if len(prompt) > MAX_INPUT_LENGTH:
            logger.info(f'Prompt length is ({len(prompt)} characters). Truncating to {MAX_INPUT_LENGTH} characters.')
            message += f'{render('_discussion is truncated_')}\n'
            prompt = prompt[:MAX_INPUT_LENGTH]
            prompt += '\nTRUNCATED\n'
          # logger.info(f'Messages: {prompt}')
          result = []
          try:
            async for token in complete(prompt):
              result.append(token)
          except Exception as e:
            logger.error(f'ERROR: {repr(e)}')
            message += f'{''.join(result)}\n**ERROR**: LLM API request failed: {repr(e)}'
          if len(result) == 0:
            logger.error('No result returned.')
            message += f'{render('**ERROR**: No result returned.')}\n'
          else:
            message += f'<blockquote expandable>{render(''.join(result))}</blockquote>'
        
        throttle.call()
        send_message_to_telegram(message)
        feed['last_published'].append(entry.id)
        feed['last_published'] = feed['last_published'][-100:]
        STATE['last_delivered'] = time.strftime('%Y-%m-%dT%H:%M:%SZ')
        save_state()
      else:
        logger.debug('skipping...')

if __name__ == '__main__':
  STATE = load_state()
  loop = asyncio.new_event_loop()
  while True:
    loop.run_until_complete(check_rss_feed())
    time.sleep(300)