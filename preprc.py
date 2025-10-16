import json
from pathlib import Path
import re

# === Input file ===
input_path = Path("data\crawler_data.json")  # your crawler output file

# Load JSON data (each line is a separate JSON object)
with open(input_path, "r", encoding="utf-8") as f:
    data = [json.loads(line) for line in f if line.strip()]

# === Threat-related keywords ===
threat_keywords = [
    "hack", "exploit", "malware", "ransomware", "ddos", "botnet", "breach",
    "leak", "passwords", "credentials", "carding", "drugs", "weapons",
    "counterfeit", "fraud", "scam", "phishing", "illegal", "darkmarket",
    "spyware", "keylogger", "zero-day", "attack", "exploit", "porn", "child",
    "terror", "murder", "assassination", "sell data", "buy data"
]

# Compile regex for efficient search
pattern = re.compile(r"\b(" + "|".join(threat_keywords) + r")\b", re.IGNORECASE)

# === Identify entries containing threat keywords ===
threat_entries = []
for entry in data:
    combined_text = " ".join([
        entry.get("title", ""),
        entry.get("passage", ""),
        " ".join(entry.get("links", []))
    ])
    if pattern.search(combined_text):
        threat_entries.append(entry)

# === Write results to output text file ===
output_text = "Potential Threat Indicators Extracted from Dark Web Crawler\n"
output_text += "------------------------------------------------------------\n\n"

if threat_entries:
    for i, item in enumerate(threat_entries, 1):
        output_text += f"Result {i}:\n"
        output_text += f"Title: {item.get('title', '[No Title]')}\n"
        output_text += f"URL: {item.get('url', '')}\n"
        output_text += f"Passage: {item.get('passage', '')}\n"
        output_text += f"Links: {', '.join(item.get('links', []))}\n\n"
else:
    output_text += "No threat-related keywords detected in the dataset.\n"

# Save output file
output_path = Path("threat_keywords_detected.txt")
with open(output_path, "w", encoding="utf-8") as f:
    f.write(output_text)

print(f"✅ Threat detection completed. Output saved to: {output_path.resolve()}")
