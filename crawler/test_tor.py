import socket
import time
import requests
from stem import Signal
from stem.control import Controller

# Tor proxy config
proxies = {
    "http": "socks5h://127.0.0.1:9050",
    "https": "socks5h://127.0.0.1:9050"
}

def wait_for_tor(host="127.0.0.1", port=9050, timeout=90):
    """Wait for Tor SOCKS port to become available."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=3):
                print("✅ Tor SOCKS port is open.")
                return True
        except OSError:
            print("⏳ Waiting for Tor to open SOCKS port...")
            time.sleep(3)
    print("❌ Tor SOCKS port did not open in time.")
    return False


def test_tor_connection():
    """Test connection through Tor exit node."""
    try:
        response = requests.get("http://httpbin.org/ip", proxies=proxies, timeout=20)
        print("✅ Tor connection successful:", response.text)
    except Exception as e:
        print("❌ Tor connection failed:", e)


def check_bootstrap():
    """Check if Tor has finished bootstrapping via Stem."""
    try:
        with Controller.from_port(port=9051) as controller:
            controller.authenticate()  # no password needed since CookieAuth is disabled
            status = controller.get_info("status/bootstrap-phase")
            print("📡 Tor bootstrap status:\n", status)
    except Exception as e:
        print("⚠️ Could not check Tor bootstrap:", e)


if __name__ == "__main__":
    if wait_for_tor():
        check_bootstrap()
        test_tor_connection()
