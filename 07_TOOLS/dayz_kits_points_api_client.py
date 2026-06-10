"""
DayZ Kits & Points API client example.

Use this in Discord bots, admin tools, or external scripts.
"""

import json
import urllib.parse
import urllib.request


class DayZKitsPointsAPI:
    def __init__(self, base_url, api_secret):
        self.base_url = base_url.rstrip("/")
        self.api_secret = api_secret

    def _post(self, path, payload=None):
        payload = payload or {}
        payload["api_secret"] = self.api_secret
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.base_url + path,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))

    def health(self):
        with urllib.request.urlopen(self.base_url + "/api/health", timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))

    def get_kits(self, server_key=None):
        payload = {}
        if server_key:
            payload["server_key"] = server_key
        return self._post("/api/v1/kits", payload)

    def get_user_by_steam(self, steam64):
        return self._post(f"/api/v1/user/by-steam/{steam64}", {})

    def get_points(self, steam64):
        return self._post(f"/api/v1/points/{steam64}", {})

    def get_user_by_discord(self, discord_id):
        return self._post(f"/api/v1/user/by-discord/{discord_id}", {})

    def get_points_by_discord(self, discord_id):
        return self._post(f"/api/v1/points/discord/{discord_id}", {})

    def create_order_by_discord(self, discord_id, kit_name, server_key, charge_points=True):
        return self._post("/api/v1/orders/create-by-discord", {
            "discord_id": discord_id,
            "kit_name": kit_name,
            "server_key": server_key,
            "charge_points": charge_points,
        })

    def add_points(self, steam64, points, reason="external_api", reference=""):
        return self._post("/api/v1/points/add", {
            "steam64": steam64,
            "points": points,
            "reason": reason,
            "reference": reference,
        })

    def set_points(self, steam64, points, reason="external_api_set"):
        return self._post("/api/v1/points/set", {
            "steam64": steam64,
            "points": points,
            "reason": reason,
        })

    def create_order(self, steam64, kit_name, server_key, charge_points=True):
        return self._post("/api/v1/orders/create", {
            "steam64": steam64,
            "kit_name": kit_name,
            "server_key": server_key,
            "charge_points": charge_points,
        })

    def pending_orders(self, server_key):
        return self._post("/api/v1/orders/pending", {"server_key": server_key})

    def mark_delivered(self, order_id, message="delivered"):
        return self._post("/api/v1/orders/mark-delivered", {
            "order_id": order_id,
            "message": message,
        })


if __name__ == "__main__":
    api = DayZKitsPointsAPI("http://127.0.0.1:8080", "CHANGE_THIS_API_SECRET")
    print(api.health())
    print(api.get_kits("server1"))
