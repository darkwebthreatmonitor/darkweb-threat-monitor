import requests

# Tor proxy configuration
proxies = {
    "http": "socks5h://127.0.0.1:9150",
    "https": "socks5h://127.0.0.1:9150"
}

def test_tor():
    try:
        # Get IP info (this should return Tor exit node IP, not your real one)
        response = requests.get("http://httpbin.org/ip", proxies=proxies, timeout=15)
        print("Tor connection successful:", response.text)
    except Exception as e:
        print("Tor connection failed:", e)

if __name__ == "__main__":
    test_tor()
