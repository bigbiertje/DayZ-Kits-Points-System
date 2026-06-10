
import json
import os
import time
import urllib.request

CONFIG_FILE = "points_events_worker_config.json"


def post_json(url, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def load_json_file(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return default


def save_json_file(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def main():
    cfg = load_json_file(CONFIG_FILE, {})
    base_url = cfg["website_base_url"].rstrip("/")
    api_secret = cfg["api_secret"]
    poll_seconds = int(cfg.get("poll_seconds", 10))
    event_paths = cfg["point_event_paths"]

    print("Points events worker started.")
    while True:
        for server_key, path in event_paths.items():
            events = load_json_file(path, [])
            if not events:
                continue

            remaining = []
            for event in events:
                payload = {
                    "api_secret": api_secret,
                    "steam64": event.get("steam64"),
                    "points": int(event.get("points", 0)),
                    "reason": event.get("reason", "dayz_points"),
                    "reference": event.get("reference", server_key),
                }
                try:
                    result = post_json(base_url + "/api/v1/points/add", payload)
                    if result.get("ok"):
                        print(f"Sent {payload['points']} points to {payload['steam64']} from {server_key}")
                    else:
                        print("API rejected event:", result)
                        remaining.append(event)
                except Exception as e:
                    print("Failed to send event:", e)
                    remaining.append(event)
            save_json_file(path, remaining)

        time.sleep(poll_seconds)


if __name__ == "__main__":
    main()
