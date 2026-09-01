import json
import os
import re
import requests
import subprocess
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_URL = "https://www.mestoborohradek.cz"
RADIO_URL = f"{BASE_URL}/zivot-ve-meste/aktuality-a-hlaseni/hlaseni-rozhlasu/"

PROCESSED_FILE = "processed.json"

DOWNLOAD_DIR = "downloads"
OUTPUT_DIR = "output"
IMAGE_FILE = "images/borohradek.jpg"


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

    for link in soup.find_all("a", href=True):
        href = link["href"]

        if ".mp3" in href.lower():
            return urljoin(page_url, href)

    for audio in soup.find_all("audio"):

        if audio.get("src"):
            return urljoin(page_url, audio["src"])

        source = audio.find("source")

        if source and source.get("src"):
            return urljoin(page_url, source["src"])

    return None


def safe_filename(text):
    text = re.sub(r'[<>:"/\\|?*]', "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def download_mp3(url, filename):

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    path = os.path.join(DOWNLOAD_DIR, filename)

    print("Stahuji MP3:")
    print(url)

    response = requests.get(
        url,
        timeout=60,
        headers={
            "User-Agent": "Mozilla/5.0 (Borohradek-Rozhlas)"
        },
        stream=True,
    )

    response.raise_for_status()

    with open(path, "wb") as f:

        for chunk in response.iter_content(chunk_size=1024 * 64):

            if chunk:
                f.write(chunk)

    print("Staženo:", path)

    return path


def create_mp4(mp3_file, output_file):

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Vytvářím MP4:")
    print(output_file)

    command = [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-i",
        IMAGE_FILE,
        "-i",
        mp3_file,
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-tune",
        "stillimage",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-pix_fmt",
        "yuv420p",
        "-shortest",
        "-vf",
        "scale=1080:1080:force_original_aspect_ratio=decrease,"
        "pad=1080:1080:(ow-iw)/2:(oh-ih)/2",
        output_file,
    ]

    subprocess.run(command, check=True)

    print("MP4 vytvořeno.")


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
        print("=" * 60)
        print("NOVÉ HLÁŠENÍ")
        print("Název:", item["title"])
        print("URL:", item["url"])

        mp3_url = get_mp3(item["url"])

        if not mp3_url:
            print("MP3: NENALEZENA")
            continue

        print("MP3:", mp3_url)

        base_name = safe_filename(item["title"])

        mp3_file = download_mp3(
            mp3_url,
            base_name + ".mp3"
        )

        mp4_file = os.path.join(
            OUTPUT_DIR,
            base_name + ".mp4"
        )

        create_mp4(
            mp3_file,
            mp4_file
        )

        processed.add(item["url"])

        print("Hlášení úspěšně zpracováno.")

    save_processed(processed)


if __name__ == "__main__":
    main()
