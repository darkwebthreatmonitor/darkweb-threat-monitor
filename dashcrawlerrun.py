import streamlit as st
import pandas as pd
import json
from pathlib import Path
import time, random, socket
from urllib.parse import urljoin, urlparse
from typing import Optional
import requests
from bs4 import BeautifulSoup
from requests.exceptions import RequestException

# --- CONFIG ---
DB_PATH = Path("data") / "crawler_data.json"
SEED_URLS = [
    "http://duckduckgogg42xjoc72x3sjasowoarfbgcmvfimaftt6twagswzczad.onion",
    "http://sanityunhavm6aolhyye4h6kbdlxjmc7zw2y7nadbni6vd43agm7xvid.onion",
]
SOCKS_HOST = "127.0.0.1"
SOCKS_PORT = 9050
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

# --- UTILS ---
def wait_for_socks(host=SOCKS_HOST, port=SOCKS_PORT, timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=3):
                return True
        except OSError:
            time.sleep(2)
    raise RuntimeError("Tor SOCKS proxy not available in time.")

def random_delay():
    delay = max(0.5, RATE_LIMIT_SECONDS + random.uniform(-JITTER_SECONDS, JITTER_SECONDS))
    time.sleep(delay)

def session_with_headers():
    s = requests.Session()
    s.proxies.update(PROXIES)
    s.headers.update({"User-Agent": USER_AGENT})
    return s

def save_to_json(data, path=DB_PATH):
    with open(path, "a", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
        f.write("\n")

def fetch_url(session: requests.Session, url: str) -> Optional[str]:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(url, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200 and "text" in resp.headers.get("Content-Type", ""):
                return resp.text
        except RequestException:
            time.sleep(2 ** attempt)
    return None

def parse_page(base_url: str, html: str):
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else "[No Title]"
    text_block = None
    for tag in soup.find_all(["p", "div", "article"]):
        snippet = tag.get_text(strip=True)
        if len(snippet) > 50:
            text_block = snippet[:400]
            break
    snippet = text_block or "[No visible text found]"
    found_links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        abs_url = urljoin(base_url, href)
        if abs_url.endswith(".onion/") or ".onion/" in abs_url:
            found_links.add(abs_url.split("#")[0])
    return {"title": title, "passage": snippet, "links": list(found_links)}

# --- CRAWLER FUNCTION ---
def crawl(seed_urls, status_bar):
    wait_for_socks()
    session = session_with_headers()
    visited = set()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)  # ensure folder exists
    # Clear previous data
    DB_PATH.write_text("")

    for seed in seed_urls:
        domain = urlparse(seed).hostname
        to_visit = {seed}
        while to_visit and len(visited) < MAX_PAGES_PER_DOMAIN:
            url = to_visit.pop()
            if url in visited:
                continue
            visited.add(url)

            status_bar.text(f"Fetching: {url}")
            html = fetch_url(session, url)
            if not html:
                continue

            parsed = parse_page(url, html)
            parsed["url"] = url
            save_to_json(parsed)
            random_delay()

            for link in parsed["links"]:
                if urlparse(link).hostname == domain and link not in visited:
                    to_visit.add(link)
    status_bar.text("✅ Crawl finished!")

# --- DASHBOARD ---
st.set_page_config(page_title="Dark Web Threat Monitor", layout="wide")
st.markdown("<h1 style='text-align: center; color: #E63946;'>🕵️‍♂️ Dark Web Threat Monitor</h1>", unsafe_allow_html=True)
st.markdown("---")

# Show seed URLs
st.markdown("### 🚀 Seed URLs used for crawling")
for url in SEED_URLS:
    st.markdown(f"- [{url}]({url})")

# Button to run crawler
if st.button("Run Crawler"):
    status = st.empty()
    crawl(SEED_URLS, status)
    st.success("Crawler finished! Data saved to data/crawler_data.json")

# Load and display crawler results
def load_crawler_data(path):
    data = []
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return data

data = load_crawler_data(DB_PATH)

if data:
    df = pd.DataFrame(data)
    total_pages = len(df)
    total_links = sum(len(row.get("links", [])) for row in data)
    col1, col2 = st.columns(2)
    col1.metric("📄 Total Pages Crawled", total_pages)
    col2.metric("🔗 Total .onion Links Found", total_links)
    
    st.markdown("---")
    with st.expander("📊 View Crawled Pages Table", expanded=True):
        st.dataframe(df[["url", "title", "passage"]], use_container_width=True)

    st.markdown("### 🔗 Discovered .onion Links by Page")
    for idx, row in df.iterrows():
        with st.expander(f"**{row['title']}** - {row['url']}", expanded=False):
            links = row.get("links", [])
            if links:
                for link in links:
                    st.markdown(f"- [{link}]({link})")
            else:
                st.info("No additional .onion links found for this page.")
else:
    st.info("No crawler data found. Click 'Run Crawler' to start crawling.")
