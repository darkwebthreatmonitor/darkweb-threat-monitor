import time
import random
import sqlite3
import socket
from typing import Optional
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from stem.control import Controller
from requests.exceptions import RequestException

# CONFIGURATION
SOCKS_HOST = "127.0.0.1"
SOCKS_PORT = 9050
CONTROL_PORT = 9051
USER_AGENT = "Mozilla/5.0 (compatible; OnionCrawler/0.1; +https://example.org)"
REQUEST_TIMEOUT = 30  # seconds
MAX_CONTENT_BYTES = 200 * 1024  # 200 KB max read
RATE_LIMIT_SECONDS = 5  # base delay between requests
JITTER_SECONDS = 3      # add up to +/- jitter
MAX_RETRIES = 3
RENEW_AFTER_REQUESTS = 50  # send NEWNYM after this many requests (optional)
MAX_PAGES_PER_DOMAIN = 20  # conservative per-domain limit

# Whitelist (start with known safe targets or onion check site)
WHITELIST = {
    "check.torproject.org",
    "expyuzz4wqqyqhjn.onion",  # example onion check service
}

PROXIES = {
    "http": f"socks5h://{SOCKS_HOST}:{SOCKS_PORT}",
    "https": f"socks5h://{SOCKS_HOST}:{SOCKS_PORT}"
}

DB_PATH = "/app/data/crawler_data.sqlite"  # persisted in container if you mount a volume

# Utilities

def wait_for_socks(host=SOCKS_HOST, port=SOCKS_PORT, timeout=90):
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
    base = RATE_LIMIT_SECONDS
    jitter = random.uniform(-JITTER_SECONDS, JITTER_SECONDS)
    delay = max(0.5, base + jitter)
    print(f"⏱ sleeping {delay:.1f}s before next request")
    time.sleep(delay)

def session_with_headers():
    s = requests.Session()
    s.proxies.update(PROXIES)
    s.headers.update({"User-Agent": USER_AGENT})
    s.timeout = REQUEST_TIMEOUT
    return s

# Storage (SQLite, simple)

def init_db(path=DB_PATH):
    conn = sqlite3.connect(path, check_same_thread=False)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pages (
            id INTEGER PRIMARY KEY,
            url TEXT UNIQUE,
            domain TEXT,
            status INTEGER,
            title TEXT,
            snippet TEXT,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    return conn

def save_page(conn, url, domain, status, title, snippet):
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT OR IGNORE INTO pages (url, domain, status, title, snippet) VALUES (?, ?, ?, ?, ?)",
            (url, domain, status, title, snippet)
        )
        conn.commit()
    except Exception as e:
        print("DB save error:", e)

# Tor control (optional IP rotate)

def renew_tor_identity():
    try:
        with Controller.from_port(port=CONTROL_PORT) as controller:
            controller.authenticate()  # assumes no password; adjust if you set one
            controller.signal("NEWNYM")
            print("🔄 Tor NEWNYM requested.")
    except Exception as e:
        print("⚠️ Could not signal NEWNYM:", e)

# Fetch logic with retries & safeguards

def fetch_url(session: requests.Session, url: str) -> Optional[requests.Response]:
    # safety: check whitelist
    parsed = urlparse(url)
    host = parsed.hostname
    # if host is None or host not in WHITELIST:
    #     print(f"❌ Host not in whitelist: {host}")
    #     return None

    # Prevent accidental large downloads via stream + content-length check
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"➡️ fetching ({attempt}/{MAX_RETRIES}): {url}")
            resp = session.get(url, timeout=REQUEST_TIMEOUT, stream=True)
            # respect content-length if present
            cl = resp.headers.get("Content-Length")
            if cl and int(cl) > MAX_CONTENT_BYTES:
                print("⚠️ Content-Length too large; skipping")
                resp.close()
                return None
            # read up to MAX_CONTENT_BYTES
            content = resp.raw.read(MAX_CONTENT_BYTES)
            # create a Response-like object with limited content for parsing
            resp._content = content
            return resp
        except RequestException as e:
            backoff = 2 ** attempt
            print(f"Request error: {e}. Backing off {backoff}s")
            time.sleep(backoff)
    print("❌ Failed after retries:", url)
    return None

# Basic parse (HTML title + snippet)

def parse_and_store(conn, url, resp):
    status = resp.status_code
    text = resp.text[:1000] if resp.text else ""
    title = None
    snippet = None
    if resp.status_code == 200 and 'text' in resp.headers.get('Content-Type', ''):
        soup = BeautifulSoup(resp.text, "html.parser")
        title = (soup.title.string.strip() if soup.title and soup.title.string else None)
        # snippet: first visible paragraph-like text
        p = soup.find(["p", "h1", "h2"])
        snippet = (p.get_text(strip=True)[:400] if p else (text[:200] or None))
    save_page(conn, url, urlparse(url).hostname or "", status, title, snippet)
    print(f"Saved: {url} status={status} title={title!r}")

# Main orchestrator

def crawl(seed_urls):
    # Wait for Tor socks
    wait_for_socks()

    session = session_with_headers()
    conn = init_db()

    fetched_count = 0
    domain_counts = {}

    for url in seed_urls:
        parsed = urlparse(url)
        domain = parsed.hostname or ""
        domain_counts.setdefault(domain, 0)
        if domain_counts[domain] >= MAX_PAGES_PER_DOMAIN:
            print(f"Reached per-domain limit for {domain}")
            continue

        resp = fetch_url(session, url)
        if resp:
            parse_and_store(conn, url, resp)
            fetched_count += 1
            domain_counts[domain] += 1

        # optional IP rotation
        if RENEW_AFTER_REQUESTS and fetched_count and (fetched_count % RENEW_AFTER_REQUESTS == 0):
            renew_tor_identity()
            # allow new identity to propagate
            time.sleep(10)

        random_delay()

    conn.close()
    print("Crawl finished.")

# Example usage (safe seeds)
if __name__ == "__main__":
    seeds = [
        "http://juhanurmihxlp77nkq76byazcldy2hlmovfu2epvl5ankdibsot4csyd.onion",  # Ahmia search engine
        "http://haystak5njsmn2hqkewecpaxetahtwhsbsa64jom2k22z5afxhnpxfid.onion",  # Haystak search engine
    ]
    crawl(seeds)
