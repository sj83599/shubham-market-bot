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

    # Find first article link on tag page
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
    text = "\n".join([p.text.strip() for p in paragraphs if p.text.strip()])

    today = datetime.now().strftime("%d %b %Y")

    message = f"📊 Stocks to Watch – {today}\n\n{text[:3500]}"
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
