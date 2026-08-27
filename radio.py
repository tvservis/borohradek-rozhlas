import json
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_URL = "https://www.mestoborohradek.cz"
RADIO_URL = f"{BASE_URL}/zivot-ve-meste/aktuality-a-hlaseni/hlaseni-rozhlasu/"
PROCESSED_FILE = "processed.json"


def load_processed():
    if not os.path.exists(PROCESSED_FILE):
        return set()

    with open(PROCESSED_FILE, "r", encoding="utf-8") as f:
        return set(json.load(f))


def save_processed(processed):
    with open(PROCESSED_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(processed), f, ensure_ascii=False, indent=2)


def get_mp3(page_url):
    response = requests.get(
        page_url,
        timeout=30,
        headers={
            "User-Agent": "Mozilla/5.0 (Borohradek-Rozhlas)"
        },
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Hledáme odkazy na MP3
    for link in soup.find_all("a", href=True):
        href = link["href"]

        if ".mp3" in href.lower():
            return urljoin(page_url, href)

    # Zkusíme ještě audio element
    for audio in soup.find_all("audio"):
        if audio.get("src"):
            return urljoin(page_url, audio["src"])

        source = audio.find("source")
        if source and source.get("src"):
            return urljoin(page_url, source["src"])

    return None


def main():
    processed = load_processed()

    response = requests.get(
        RADIO_URL,
        timeout=30,
        headers={
            "User-Agent": "Mozilla/5.0 (Borohradek-Rozhlas)"
        },
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    found = 0
    new_items = []

    for link in soup.find_all("a", href=True):

        href = urljoin(BASE_URL, link["href"])

        if "/hlaseni-rozhlasu/" not in href:
            continue

        if href.rstrip("/") == RADIO_URL.rstrip("/"):
            continue

        title = link.get_text(" ", strip=True)

        if not title:
            continue

        found += 1

        if href not in processed:
            new_items.append({
                "url": href,
                "title": title,
            })

    print(f"Nalezeno hlášení: {found}")
    print(f"Nových hlášení: {len(new_items)}")

    for item in new_items:

        print()
        print("NOVÉ HLÁŠENÍ")
        print("Název:", item["title"])
        print("URL:", item["url"])

        mp3_url = get_mp3(item["url"])

        if mp3_url:
            print("MP3:", mp3_url)
        else:
            print("MP3: NENALEZENA")

        processed.add(item["url"])

    save_processed(processed)


if __name__ == "__main__":
    main()
