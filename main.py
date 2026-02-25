import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def get_stocks_to_watch():
    base_url = "https://www.moneycontrol.com"
    search_url = base_url + "/news/tags/stocks-to-watch.html"
    headers = {"User-Agent": "Mozilla/5.0"}

    response = requests.get(search_url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    article_link = None
    for link in soup.find_all("a", href=True):
        if "/news/business/markets/stocks-to-watch" in link["href"]:
            article_link = link["href"]
            break

    if not article_link:
        return "⚠ Stocks to Watch article not found."

    if article_link.startswith("/"):
        article_link = base_url + article_link

    article = requests.get(article_link, headers=headers)
    article_soup = BeautifulSoup(article.text, "html.parser")

    paragraphs = article_soup.find_all("p")

    stock_lines = []

    for p in paragraphs:
        text = p.text.strip()

        # Detect bullet-style stock lines (usually contain colon or dash)
        if ":" in text and len(text) < 200:
            parts = text.split(":", 1)
            stock = parts[0].strip()
            reason = parts[1].strip()
            formatted = f"• {stock} → {reason}"
            stock_lines.append(formatted)

    if not stock_lines:
        return "⚠ Could not extract stock-wise format."

    today = datetime.now().strftime("%d %b %Y")

    message = f"📊 Stocks to Watch – {today}\n\n"
    message += "\n".join(stock_lines[:15])

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
