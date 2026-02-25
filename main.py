import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def get_stocks_to_watch():
    url = "https://www.moneycontrol.com/news/business/markets/"
    headers = {"User-Agent": "Mozilla/5.0"}

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    article_link = None
    for link in soup.find_all("a", href=True):
        if "stocks-to-watch" in link["href"]:
            article_link = link["href"]
            break

    if not article_link:
        return "No Stocks to Watch article found today."

    if article_link.startswith("/"):
        article_link = "https://www.moneycontrol.com" + article_link

    article = requests.get(article_link, headers=headers)
    article_soup = BeautifulSoup(article.text, "html.parser")

    paragraphs = article_soup.find_all("p")
    text = "\n".join([p.text for p in paragraphs[:25]])

    today = datetime.now().strftime("%d %b %Y")

    message = f"📊 Stocks to Watch – {today}\n\n{text}"
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
