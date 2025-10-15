"""
Enhanced Tor .onion crawler
 - Uses Tor SOCKS5 proxy at 127.0.0.1:9050
 - Fetches .onion pages recursively (limited)
 - Extracts title, snippet, and discovered URLs
 - Saves all results to JSON file
"""

import time, random, json, socket
from urllib.parse import urljoin, urlparse
from typing import Optional
import requests
from bs4 import BeautifulSoup
from requests.exceptions import RequestException

# --- CONFIG ---
SOCKS_HOST = "127.0.0.1"
SOCKS_PORT = 9050
DB_PATH = "/app/data/crawler_data.json"

USER_AGENT = "Mozilla/5.0 (compatible; TorCrawler/0.3)"
REQUEST_TIMEOUT = 30
MAX_PAGES_PER_DOMAIN = 5
RATE_LIMIT_SECONDS = 5
JITTER_SECONDS = 3
MAX_RETRIES = 3

PROXIES = {
    "http": f"socks5h://{SOCKS_HOST}:{SOCKS_PORT}",
    "https": f"socks5h://{SOCKS_HOST}:{SOCKS_PORT}",
}


# --- UTILITIES ---
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
    delay = max(0.5, RATE_LIMIT_SECONDS + random.uniform(-JITTER_SECONDS, JITTER_SECONDS))
    print(f"⏱ Sleeping {delay:.1f}s before next request...")
    time.sleep(delay)


def session_with_headers():
    s = requests.Session()
    s.proxies.update(PROXIES)
    s.headers.update({"User-Agent": USER_AGENT})
    return s


def save_to_json(data, path=DB_PATH):
    """Append JSON record."""
    with open(path, "a", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
        f.write("\n")


# --- FETCH + PARSE ---
def fetch_url(session: requests.Session, url: str) -> Optional[str]:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"➡️ Fetching ({attempt}/{MAX_RETRIES}): {url}")
            resp = session.get(url, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200 and "text" in resp.headers.get("Content-Type", ""):
                return resp.text
        except RequestException as e:
            backoff = 2 ** attempt
            print(f"⚠️ Error: {e}. Retrying in {backoff}s...")
            time.sleep(backoff)
    print(f"❌ Failed after retries: {url}")
    return None


def parse_page(base_url: str, html: str):
    """Extract title, snippet, and links."""
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else "[No Title]"
    text_block = None
    for tag in soup.find_all(["p", "div", "article"]):
        snippet = tag.get_text(strip=True)
        if len(snippet) > 50:
            text_block = snippet[:400]
            break
    snippet = text_block or "[No visible text found]"

    # Extract internal links
    found_links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        abs_url = urljoin(base_url, href)
        if abs_url.endswith(".onion/") or ".onion/" in abs_url:
            found_links.add(abs_url.split("#")[0])
    return {"title": title, "passage": snippet, "links": list(found_links)}


# --- MAIN CRAWLER ---
def crawl(seed_urls):
    wait_for_socks()
    session = session_with_headers()
    visited = set()

    for seed in seed_urls:
        domain = urlparse(seed).hostname
        to_visit = {seed}

        while to_visit and len(visited) < MAX_PAGES_PER_DOMAIN:
            url = to_visit.pop()
            if url in visited:
                continue
            visited.add(url)

            html = fetch_url(session, url)
            if not html:
                continue

            parsed = parse_page(url, html)
            parsed["url"] = url
            save_to_json(parsed)
            print(f"✅ Saved: {url} | Title: {parsed['title']}")
            random_delay()

            # Add new links from same domain
            for link in parsed["links"]:
                if urlparse(link).hostname == domain and link not in visited:
                    to_visit.add(link)

    print("🎯 Crawl finished. Data saved to:", DB_PATH)


if __name__ == "__main__":
    seeds = [
        "http://duckduckgogg42xjoc72x3sjasowoarfbgcmvfimaftt6twagswzczad.onion",  # DuckDuckGo
        "http://sanityunhavm6aolhyye4h6kbdlxjmc7zw2y7nadbni6vd43agm7xvid.onion",  # Tor mirror
    ]
    crawl(seeds)
