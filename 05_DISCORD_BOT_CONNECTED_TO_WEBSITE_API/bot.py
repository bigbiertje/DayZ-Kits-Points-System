import json
import urllib.request

import discord
from discord import app_commands
from discord.ext import commands

CONFIG_FILE = "discord_bot_config.json"


def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


class API:
    def __init__(self, base_url, secret):
        self.base_url = base_url.rstrip("/")
        self.secret = secret

    def post(self, path, payload=None):
        payload = payload or {}
        payload["api_secret"] = self.secret
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.base_url + path,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))

    def points_by_discord(self, discord_id):
        return self.post(f"/api/v1/points/discord/{discord_id}", {})

    def kits(self, server_key):
        return self.post("/api/v1/kits", {"server_key": server_key, "enabled_only": True})

    def buy_by_discord(self, discord_id, kit_name, server_key):
        return self.post("/api/v1/orders/create-by-discord", {
            "discord_id": discord_id,
            "kit_name": kit_name,
            "server_key": server_key,
            "charge_points": True,
        })


cfg = load_config()
api = API(cfg["website_base_url"], cfg["api_secret"])

intents = discord.Intents.default()
bot = commands.Bot(command_prefix=cfg.get("prefix", "!"), intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands.")
    except Exception as e:
        print("Slash sync failed:", e)


@bot.tree.command(name="link", description="Get the website link to connect Steam and Discord.")
async def link(interaction: discord.Interaction):
    url = cfg["website_base_url"].rstrip("/") + "/account/links"
    await interaction.response.send_message(
        f"Link your Steam + Discord here: {url}\nLogin with Discord first, then link Steam.",
        ephemeral=True,
    )


@bot.tree.command(name="points", description="Show your linked website points.")
async def points(interaction: discord.Interaction):
    try:
        result = api.points_by_discord(str(interaction.user.id))
        if not result.get("ok"):
            await interaction.response.send_message("Your Discord is not linked yet. Use /link.", ephemeral=True)
            return
        p = result["points"]["points"]
        steam = result.get("steam64") or "No Steam linked"
        await interaction.response.send_message(f"You have **{p}** points.\nSteam: `{steam}`", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Could not read points. Use /link first or tell staff.\n`{e}`", ephemeral=True)


@bot.tree.command(name="pointkits", description="Show available website point kits.")
@app_commands.describe(server="Server key, example: server1")
async def pointkits(interaction: discord.Interaction, server: str = "server1"):
    try:
        result = api.kits(server)
        if not result.get("ok"):
            await interaction.response.send_message("Could not read kits from website.", ephemeral=True)
            return
        kits = result.get("kits", [])
        if not kits:
            await interaction.response.send_message(f"No point kits found for `{server}`.", ephemeral=True)
            return
        lines = [f"**{k['display_name']}** (`{k['kit_name']}`) - {k['cost']} points" for k in kits]
        await interaction.response.send_message("\n".join(lines), ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Could not read kits.\n`{e}`", ephemeral=True)


@bot.tree.command(name="buypointkit", description="Buy a point kit using your linked website account.")
@app_commands.describe(server="Server key, example: server1", kit="Internal kit name, example: special_blackmarket")
async def buypointkit(interaction: discord.Interaction, server: str, kit: str):
    await interaction.response.defer(ephemeral=True)
    try:
        result = api.buy_by_discord(str(interaction.user.id), kit, server)
        if result.get("ok"):
            await interaction.followup.send(f"Bought `{kit}` for `{server}`. Order ID: `{result['order_id']}`")
            return
        await interaction.followup.send(f"Could not buy kit: `{result.get('error', 'unknown error')}`")
    except Exception as e:
        await interaction.followup.send(f"Could not buy kit. Use /link first or tell staff.\n`{e}`")


bot.run(cfg["discord_bot_token"])
