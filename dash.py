import streamlit as st
import pandas as pd
import json
from pathlib import Path

# --- CONFIG ---
DB_PATH = Path("data") / "crawler_data.json"  # relative path to repo root

# --- Page Setup ---
st.set_page_config(page_title="Dark Web Threat Monitor", layout="wide")
st.markdown("<h1 style='text-align: center; color: #E63946;'>🕵️‍♂️ Dark Web Threat Monitor</h1>", unsafe_allow_html=True)
st.markdown("---")

# --- Load Data ---
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

    # --- Summary Metrics ---
    total_pages = len(df)
    total_links = sum(len(row.get("links", [])) for row in data)

    col1, col2 = st.columns(2)
    col1.metric("📄 Total Pages Crawled", total_pages)
    col2.metric("🔗 Total .onion Links Found", total_links)

    st.markdown("---")

    # --- Crawled Pages Table ---
    with st.expander("📊 View Crawled Pages Table", expanded=True):
        st.dataframe(df[["url", "title", "passage"]], use_container_width=True)

    st.markdown("---")

    # --- Display Discovered Links per Page ---
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
    st.warning(
        f"""
        ⚠️ No crawler data found at `{DB_PATH}`.

        Please make sure:
        1. The crawler has run successfully.
        2. The `crawler_data.json` file exists in the `data/` folder.
        """
    )
