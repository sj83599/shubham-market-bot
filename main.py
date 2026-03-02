"""
Telegram Bot - MoneyControl "Stocks to Watch" Daily Alert
Sends a message every weekday at 7:00 AM with stocks to watch scraped from MoneyControl.

Requirements:
    pip install python-telegram-bot schedule requests beautifulsoup4

Setup:
    1. Create a bot via @BotFather on Telegram → get BOT_TOKEN
    2. Get your CHAT_ID by messaging @userinfobot on Telegram
    3. Set BOT_TOKEN and CHAT_ID below
    4. Run the script: python telegram_stock_bot.py
    5. (Optional) Deploy on a server / use systemd or cron to keep it running 24/7
"""

import logging
import time
import schedule
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from telegram import Bot
from telegram.constants import ParseMode
import asyncio

# ─────────────────────────────────────────────
# CONFIGURATION — fill these in
# ─────────────────────────────────────────────
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"   # from @BotFather
CHAT_ID   = "YOUR_CHAT_ID_HERE"     # your Telegram chat/user ID

SEND_TIME = "07:00"  # 24-hour format, local time of the machine running the script
# ─────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

MONEYCONTROL_URL = "https://www.moneycontrol.com/news/tags/stocks-to-watch.html"


def scrape_stocks_to_watch() -> str:
    """Scrape the latest 'Stocks to Watch' articles from MoneyControl."""
    try:
        resp = requests.get(MONEYCONTROL_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        articles = []

        # MoneyControl news list items
        for li in soup.select("ul.list_title li")[:8]:
            a_tag = li.find("a")
            if a_tag:
                title = a_tag.get_text(strip=True)
                link  = a_tag.get("href", "")
                if title and link:
                    articles.append((title, link))

        # Fallback selector
        if not articles:
            for a in soup.select("a[href*='stocks-to-watch']")[:8]:
                title = a.get_text(strip=True)
                link  = a.get("href", "")
                if title and len(title) > 15 and link:
                    articles.append((title, link))

        if not articles:
            return "⚠️ Could not fetch stocks-to-watch data today. Please visit MoneyControl manually."

        today = datetime.now().strftime("%A, %d %B %Y")
        lines = [f"📈 *Stocks to Watch — {today}*\n"]
        for i, (title, link) in enumerate(articles, 1):
            # Escape markdown special chars
            safe_title = title.replace("*", "").replace("_", "").replace("[", "").replace("]", "")
            lines.append(f"{i}\\. [{safe_title}]({link})")

        lines.append(f"\n🔗 [View all on MoneyControl]({MONEYCONTROL_URL})")
        return "\n".join(lines)

    except Exception as e:
        logger.error(f"Scraping error: {e}")
        return f"⚠️ Error fetching stocks to watch: {e}"


async def send_message_async(text: str):
    bot = Bot(token=BOT_TOKEN)
    await bot.send_message(
        chat_id=CHAT_ID,
        text=text,
        parse_mode=ParseMode.MARKDOWN_V2,
        disable_web_page_preview=False
    )
    logger.info("Message sent successfully.")


def job():
    """Job that runs every weekday at the scheduled time."""
    now = datetime.now()
    if now.weekday() >= 5:          # 5 = Saturday, 6 = Sunday
        logger.info("Weekend — skipping.")
        return

    logger.info("Fetching stocks to watch...")
    message = scrape_stocks_to_watch()
    asyncio.run(send_message_async(message))


def main():
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE" or CHAT_ID == "YOUR_CHAT_ID_HERE":
        print("❌  Please set BOT_TOKEN and CHAT_ID in the script before running.")
        return

    logger.info(f"Bot started. Will send messages every weekday at {SEND_TIME}.")

    schedule.every().day.at(SEND_TIME).do(job)

    # Optional: send a test message immediately on startup
    # job()

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
