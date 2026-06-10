import json
from pathlib import Path

import requests

cfg_path = Path(__file__).resolve().parent / "website_link_bot_config.json"
if not cfg_path.exists():
    raise SystemExit("Missing website_link_bot_config.json. Copy website_link_bot_config.example.json first.")

cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
url = cfg.get("website_api_url")
secret = cfg.get("website_api_secret")
if not url or not secret or secret.startswith("CHANGE_THIS"):
    raise SystemExit("Set website_api_url and website_api_secret first.")

resp = requests.post(url, json={"action": "health", "secret": secret}, timeout=15)
print("HTTP", resp.status_code)
print(resp.text)
resp.raise_for_status()
data = resp.json()
if data.get("ok"):
    print("OK: Website Discord kit API is reachable.")
else:
    raise SystemExit("API returned ok=false")
