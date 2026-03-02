import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def get_stocks_to_watch():
    base_url = "https://www.moneycontrol.com"
    markets_url = base_url + "/news/business/markets/"
    headers = {"User-Agent": "Mozilla/5.0"}

    # fetch markets page
    response = requests.get(markets_url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    article_link = None

    # look for the first link containing 'stocks-to-watch'
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if "stocks-to-watch" in href and "/news/business/markets/" in href:
            article_link = href
            break

    if not article_link:
        return "⚠ Stocks to Watch article not found on Markets page."

    # build full link if relative
    if article_link.startswith("/"):
        article_link = base_url + article_link

    # fetch article page
    article = requests.get(article_link, headers=headers)
    article_soup = BeautifulSoup(article.text, "html.parser")

    # extract all paragraphs
    content_div = article_soup.find("div", {"class": "content_wrapper"})
    if not content_div:
        content_div = article_soup

    paragraphs = content_div.find_all("p")
    if not paragraphs:
        return "⚠ Article fetched but no content found."

    # combine text
    full_text = "\n\n".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])

    today = datetime.now().strftime("%d %b %Y")
    message = f"📊 Stocks to Watch – {today}\n\n{full_text}"

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
