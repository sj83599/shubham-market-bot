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

    content_div = article_soup.find("div", {"class": "content_wrapper"})
    if not content_div:
        content_div = article_soup

    stock_lines = []

    for strong_tag in content_div.find_all("strong"):
        stock_name = strong_tag.get_text(strip=True)

        # Get next paragraph after stock name
        parent = strong_tag.parent
        next_p = parent.find_next("p")

        if next_p:
            reason = next_p.get_text(strip=True)
            formatted = f"• {stock_name} → {reason}"
            stock_lines.append(formatted)

    if not stock_lines:
        return "⚠ Could not extract stock-wise format."

    today = datetime.now().strftime("%d %b %Y")

    message = f"📊 Stocks to Watch – {today}\n\n"
    message += "\n\n".join(stock_lines)

    return message
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    chunk_size = 4000  # safety margin below 4096

    for i in range(0, len(message), chunk_size):
        chunk = message[i:i+chunk_size]

        payload = {
            "chat_id": CHAT_ID,
            "text": chunk
        }

        response = requests.post(url, data=payload)
        print(response.text)

if __name__ == "__main__":
    message = get_stocks_to_watch()
    print("Sending message...")
    send_telegram_message(message)
