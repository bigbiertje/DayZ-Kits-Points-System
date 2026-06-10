
import json
import os
import time
import urllib.request

CONFIG_FILE = "special_kits_worker_config.json"


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
    servers = cfg["servers"]

    print("Special kits worker started.")
    while True:
        for server_key, queue_path in servers.items():
            try:
                result = post_json(base_url + "/api/v1/orders/pending", {
                    "api_secret": api_secret,
                    "server_key": server_key,
                })
            except Exception as e:
                print("Failed to fetch orders:", e)
                continue

            if not result.get("ok"):
                print("API error:", result)
                continue

            orders = result.get("orders", [])
            if not orders:
                continue

            queue = load_json_file(queue_path, [])
            for order in orders:
                queue.append({
                    "source": "website_points_shop",
                    "order_id": order["id"],
                    "steam64": order["steam64"],
                    "kit": order["kit_name"],
                    "server": order["server_key"],
                })

                try:
                    mark = post_json(base_url + "/api/v1/orders/mark-delivered", {
                        "api_secret": api_secret,
                        "order_id": order["id"],
                        "message": "written to DayZ queue by worker",
                    })
                    if mark.get("ok"):
                        print(f"Queued order {order['id']} kit={order['kit_name']} steam64={order['steam64']}")
                    else:
                        print("Failed to mark delivered:", mark)
                except Exception as e:
                    print("Failed to mark delivered:", e)

            save_json_file(queue_path, queue)

        time.sleep(poll_seconds)


if __name__ == "__main__":
    main()
