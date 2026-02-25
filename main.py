import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def get_stocks_to_watch():
    import re

    base_url = "https://www.moneycontrol.com"
    markets_url = base_url + "/news/business/markets/"
    headers = {"User-Agent": "Mozilla/5.0"}

    response = requests.get(markets_url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    article_link = None

    for link in soup.find_all("a", href=True):
        href = link["href"]
        if "stocks-to-watch" in href:
            article_link = href
            break

    if not article_link:
        return "⚠ Stocks to Watch article not found."

    if article_link.startswith("/"):
        article_link = base_url + article_link

    article = requests.get(article_link, headers=headers)
    article_soup = BeautifulSoup(article.text, "html.parser")

    content_div = article_soup.find("div", {"class": "content_wrapper"})
    if not content_div:
        content_div = article_soup

    stock_lines = []

    for strong_tag in content_div.find_all("strong"):
        stock_name = strong_tag.get_text(strip=True)

        # Skip unwanted headings
        skip_words = ["Stocks to Watch", "Quarterly Earnings", "Results Today"]
        if any(word in stock_name for word in skip_words):
            continue

        # Fix missing spacing like IndiaQ4-2025
        stock_name = re.sub(r'([a-zA-Z])Q', r'\1 - Q', stock_name)

        parent = strong_tag.parent
        next_p = parent.find_next("p")

        if next_p:
            reason = next_p.get_text(strip=True)

            if len(reason) > 350:
                reason = reason[:350] + "..."

            formatted = f"• {stock_name} → {reason}"
            stock_lines.append(formatted)

    if not stock_lines:
        return "⚠ Could not extract stock-wise format."

    today = datetime.now().strftime("%d %b %Y")

    message = f"📊 Stocks to Watch – {today}\n\n"
    message += "\n\n".join(stock_lines[:15])

    return message

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }

    response = requests.post(url, data=payload)
    print(response.text)

if __name__ == "__main__":
    message = get_stocks_to_watch()
    print("Sending message...")
    send_telegram_message(message)
