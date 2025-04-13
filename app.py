import os
import time
import feedparser
import requests
from bs4 import BeautifulSoup
import random
from telegram import Bot, InputMediaPhoto
from telegram.error import TelegramError
from googletrans import Translator
from datetime import datetime
import pytrends
from pytrends.request import TrendReq

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '7896793670:AAGILbEyLmVLuYfBFKFR5aMof2PaLNtGIC4')
CHANNEL_ID = os.getenv('CHANNEL_ID', '@AiSamacharExpress')
PROXY_LIST = [
    'http://103.149.162.195:80',
    'http://45.7.64.34:80',
    'http://103.156.19.214:80'
    # Add more proxies as needed
]
TRANSLATOR = Translator()

# RSS Feeds (Hindi priority)
RSS_FEEDS = [
    # Hindi sources
    'https://www.bbc.com/hindi/india/index.xml',
    'https://feeds.feedburner.com/ndtvkhabar',
    'https://www.aajtak.in/rssfeeds/news.xml',
    
    # English sources (will be translated)
    'https://timesofindia.indiatimes.com/rssfeedstopstories.cms',
    'https://www.thehindu.com/news/national/feeder/default.rss',
    'http://rss.cnn.com/rss/edition.rss'
]

def get_random_proxy():
    return {'http': random.choice(PROXY_LIST)}

def translate_to_hindi(text):
    try:
        translated = TRANSLATOR.translate(text, src='en', dest='hi')
        return translated.text
    except:
        return text

def fetch_google_trends():
    try:
        pytrends = TrendReq(hl='en-IN', tz=330)
        trends = pytrends.trending_searches(pn='india')
        return "ट्रेंडिंग टॉपिक्स:\n" + "\n".join([f"• {trend}" for trend in trends[:5]])
    except Exception as e:
        print(f"Google Trends error: {e}")
        return None

def get_news_image(url):
    try:
        proxy = get_random_proxy()
        response = requests.get(url, proxies=proxy, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Try to find image in meta tags
        meta_image = soup.find('meta', property='og:image') or soup.find('meta', attrs={'name': 'og:image'})
        if meta_image and meta_image.get('content'):
            return meta_image.get('content')
        
        # Try to find first large image in content
        images = [img for img in soup.find_all('img') if img.get('src')]
        if images:
            return images[0].get('src')
            
        return None
    except:
        return None

def format_news_post(entry, is_translated=False):
    title = entry.get('title', 'कोई शीर्षक नहीं')
    summary = entry.get('summary', '')[:200] + '...' if entry.get('summary') else ''
    link = entry.get('link', '#')
    
    if is_translated:
        title = translate_to_hindi(title)
        summary = translate_to_hindi(summary)
    
    # Format with proper Hindi styling
    post = f"📰 <b>{title}</b>\n\n"
    if summary:
        post += f"ℹ️ {summary}\n\n"
    post += f"🔗 पूरी खबर पढ़ें: <a href='{link}'>यहां क्लिक करें</a>"
    
    return post

def post_to_telegram(bot, message, image_url=None):
    try:
        if image_url:
            # Download image first to check quality
            proxy = get_random_proxy()
            image_data = requests.get(image_url, proxies=proxy, timeout=10).content
            
            # Post with image
            bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=image_data,
                caption=message,
                parse_mode='HTML'
            )
        else:
            bot.send_message(
                chat_id=CHANNEL_ID,
                text=message,
                parse_mode='HTML'
            )
        return True
    except TelegramError as e:
        print(f"Telegram error: {e}")
        return False
    except Exception as e:
        print(f"Error posting: {e}")
        return False

def main():
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    posted_urls = set()
    
    while True:
        try:
            # Post Google Trends
            trends = fetch_google_trends()
            if trends:
                post_to_telegram(bot, trends)
            
            # Process RSS feeds
            for feed_url in RSS_FEEDS:
                try:
                    proxy = get_random_proxy()
                    feed = feedparser.parse(feed_url, handlers=[requests])
                    
                    for entry in feed.entries[:3]:  # Get latest 3 entries
                        if entry.link not in posted_urls:
                            # Check if feed is in Hindi
                            is_hindi_feed = 'hindi' in feed_url or 'aajtak' in feed_url or 'ndtvkhabar' in feed_url
                            
                            message = format_news_post(entry, is_translated=not is_hindi_feed)
                            image_url = get_news_image(entry.link)
                            
                            if post_to_telegram(bot, message, image_url):
                                posted_urls.add(entry.link)
                                print(f"Posted: {entry.link}")
                                time.sleep(300)  # 5 minutes between posts
                except Exception as e:
                    print(f"Error processing {feed_url}: {e}")
                    continue
            
            # Sleep for 15-20 minutes before next cycle
            time.sleep(random.randint(900, 1200))
            
        except Exception as e:
            print(f"Main loop error: {e}")
            time.sleep(60)

if __name__ == '__main__':
    main()
