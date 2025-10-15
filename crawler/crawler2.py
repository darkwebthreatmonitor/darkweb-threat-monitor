"""
Minimal Tor .onion crawler
 - Uses Tor SOCKS5 proxy at 127.0.0.1:9050
 - Fetches only .onion sites
 - Extracts <title> and one passage/snippet
 - Saves all results to a JSON file instead of SQLite
"""

import time
import random
import json
import socket
from urllib.parse import urlparse
from typing import Optional

import requests
from bs4 import BeautifulSoup
from requests.exceptions import RequestException

# CONFIG
SOCKS_HOST = "127.0.0.1"
SOCKS_PORT = 9050
CONTROL_PORT = 9051

USER_AGENT = "Mozilla/5.0 (compatible; TorCrawler/0.2; +https://example.org)"
REQUEST_TIMEOUT = 30
MAX_CONTENT_BYTES = 200 * 1024  # 200 KB max read
RATE_LIMIT_SECONDS = 5
JITTER_SECONDS = 3
MAX_RETRIES = 3
MAX_PAGES_PER_DOMAIN = 5

DB_PATH = "/app/data/crawler_data.json"

PROXIES = {
    "http": f"socks5h://{SOCKS_HOST}:{SOCKS_PORT}",
    "https": f"socks5h://{SOCKS_HOST}:{SOCKS_PORT}",
}


### Utilities ###

def wait_for_socks(host=SOCKS_HOST, port=SOCKS_PORT, timeout=90):
    """Wait until Tor SOCKS proxy is available."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=3):
                print("✅ SOCKS proxy available.")
                return True
        except OSError:
            print("⏳ Waiting for SOCKS proxy...")
            time.sleep(2)
    raise RuntimeError("Tor SOCKS proxy not available in time.")


def random_delay():
    """Polite crawling: delay between requests."""
    delay = max(0.5, RATE_LIMIT_SECONDS + random.uniform(-JITTER_SECONDS, JITTER_SECONDS))
    print(f"⏱ Sleeping {delay:.1f}s before next request...")
    time.sleep(delay)


def session_with_headers():
    """Create a requests session with Tor proxy and headers."""
    s = requests.Session()
    s.proxies.update(PROXIES)
    s.headers.update({"User-Agent": USER_AGENT})
    return s


### JSON storage ###

def save_to_json(data, path=DB_PATH):
    """Append crawled data to JSON file."""
    try:
        with open(path, "a", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
            f.write("\n")  # newline per record for readability
    except Exception as e:
        print("⚠️ Error saving JSON:", e)


### Fetch and parse ###

def fetch_url(session: requests.Session, url: str) -> Optional[requests.Response]:
    """Fetch a URL safely via Tor."""
    parsed = urlparse(url)
    host = parsed.hostname or ""
    if not host.endswith(".onion"):
        print(f"❌ Skipping non-onion URL: {url}")
        return None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"➡️ Fetching ({attempt}/{MAX_RETRIES}): {url}")
            resp = session.get(url, timeout=REQUEST_TIMEOUT, stream=True)
            if resp.status_code != 200:
                print(f"⚠️ Non-200 status: {resp.status_code}")
            return resp
        except RequestException as e:
            backoff = 2 ** attempt
            print(f"Request error: {e}. Retrying in {backoff}s...")
            time.sleep(backoff)
    print(f"❌ Failed after retries: {url}")
    return None


def parse_page(url: str, resp) -> dict:
    """Extract title and one visible passage/snippet."""
    data = {"url": url, "status": resp.status_code, "title": None, "passage": None}

    if resp.status_code == 200 and "text" in resp.headers.get("Content-Type", ""):
        soup = BeautifulSoup(resp.text, "html.parser")
        # Title extraction
        title = soup.title.string.strip() if soup.title and soup.title.string else "[No Title]"
        data["title"] = title

        # Snippet extraction
        p = soup.find(["p", "div", "span"])
        if p:
            snippet = p.get_text(strip=True)
            data["passage"] = snippet[:400]
        else:
            data["passage"] = "[No visible text found]"
    return data


### Main crawler ###

def crawl(seed_urls):
    wait_for_socks()
    session = session_with_headers()

    for url in seed_urls:
        resp = fetch_url(session, url)
        if not resp:
            continue

        page_data = parse_page(url, resp)
        save_to_json(page_data)
        print(f"✅ Saved: {url} | Title: {page_data['title']}")
        random_delay()

    print("🎯 Crawl finished. Data saved to:", DB_PATH)


### Example run (safe onions)
if __name__ == "__main__":
    seeds = [
        "http://juhanurmihxlp77nkq76byazcldy2hlmovfu2epvl5ankdibsot4csyd.onion",  # Tor Project mirror
        "http://duckduckgogg42xjoc72x3sjasowoarfbgcmvfimaftt6twagswzczad.onion"  # DuckDuckGo onion
    ]
    crawl(seeds)
