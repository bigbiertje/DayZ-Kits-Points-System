import asyncio
import json
import os
import re
import secrets
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

import discord
import requests
from discord import app_commands
from discord.ext import commands

APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "website_link_bot_config.json"
STEAM64_RE = re.compile(r"^\d{15,32}$")


def atomic_write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=4), encoding="utf-8")
    os.replace(tmp, path)


def read_json(path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
    try:
        if not path.exists():
            return default
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return default
        data = json.loads(raw)
        return data if isinstance(data, dict) else default
    except Exception as exc:
        print(f"[WARN] Could not read JSON {path}: {exc}")
        return default


def resolve_path(raw: str, base: Path) -> Path:
    path = Path(str(raw))
    if not path.is_absolute():
        path = base / path
    return path


def load_config() -> Dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise RuntimeError("Missing website_link_bot_config.json. Copy website_link_bot_config.example.json first.")
    cfg = read_json(CONFIG_PATH, {})
    if not cfg.get("discord_token") or cfg.get("discord_token") == "PUT_YOUR_DISCORD_BOT_TOKEN_HERE":
        raise RuntimeError("Put your Discord bot token inside website_link_bot_config.json.")
    if not cfg.get("servers"):
        raise RuntimeError("Add server profile paths inside website_link_bot_config.json -> servers.")
    if not cfg.get("website_connect_url"):
        raise RuntimeError("website_connect_url is missing. Example: https://example.com/user/discord")

    cfg["use_remote_website_api"] = bool(cfg.get("use_remote_website_api", True))
    if cfg["use_remote_website_api"]:
        if not cfg.get("website_api_url"):
            raise RuntimeError("website_api_url is missing. Example: https://example.com/api/discord_kit_link.php")
        if not cfg.get("website_api_secret") or cfg.get("website_api_secret") == "CHANGE_THIS_SECRET_AND_MATCH_WEBSITE_CONFIG":
            raise RuntimeError("Set website_api_secret in website_link_bot_config.json and match it in includes/discord_kit_config.php on the website.")
    else:
        data_dir = resolve_path(str(cfg.get("link_data_dir", "./data")), APP_DIR)
        data_dir.mkdir(parents=True, exist_ok=True)
        cfg["link_data_dir"] = str(data_dir)
    return cfg


config = load_config()


def now_utc() -> int:
    return int(time.time())


# -------------------------
# Remote website API helpers
# -------------------------

def website_api_request(action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(payload)
    data["action"] = action
    data["secret"] = str(config.get("website_api_secret", ""))
    timeout = int(config.get("website_api_timeout_seconds", 12) or 12)
    try:
        response = requests.post(
            str(config["website_api_url"]),
            json=data,
            timeout=timeout,
            headers={"User-Agent": "DayZKitBot/1.9.3"},
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"Website API connection failed: {exc}") from exc

    try:
        body = response.json()
    except Exception as exc:
        preview = response.text[:300].replace("\n", " ")
        raise RuntimeError(f"Website API did not return JSON. HTTP {response.status_code}: {preview}") from exc

    if response.status_code >= 400 or not body.get("ok"):
        message = body.get("error") or body.get("message") or f"HTTP {response.status_code}"
        raise RuntimeError(f"Website API error: {message}")
    return body


# -------------------------
# Local shared-folder fallback
# -------------------------

def link_data_dir() -> Path:
    return Path(config.get("link_data_dir", APP_DIR / "data"))


def pending_links_path() -> Path:
    return link_data_dir() / str(config.get("pending_file", "discord_kit_pending_links.json"))


def links_path() -> Path:
    return link_data_dir() / str(config.get("links_file", "discord_kit_links.json"))


def cleanup_pending(data: Dict[str, Any]) -> Dict[str, Any]:
    now = now_utc()
    pending = data.setdefault("pending", {})
    dead = []
    for token, row in list(pending.items()):
        try:
            expired = int(row.get("expires_utc", 0) or 0) < now
            used = row.get("used") is True
            recently_used = used and int(row.get("used_utc", 0) or 0) and now - int(row.get("used_utc", 0)) < 3600
            if expired or (used and not recently_used):
                dead.append(token)
        except Exception:
            dead.append(token)
    for token in dead:
        pending.pop(token, None)
    return data


def load_pending() -> Dict[str, Any]:
    data = cleanup_pending(read_json(pending_links_path(), {"pending": {}}))
    atomic_write_json(pending_links_path(), data)
    return data


def create_pending_link(discord_user: discord.abc.User) -> Tuple[str, int]:
    lifetime_minutes = int(config.get("link_token_lifetime_minutes", 30) or 30)
    now = now_utc()
    token = secrets.token_urlsafe(32)
    row = {
        "discord_user_id": str(discord_user.id),
        "discord_user_name": str(discord_user),
        "created_utc": now,
        "expires_utc": now + lifetime_minutes * 60,
        "used": False,
    }

    if config.get("use_remote_website_api", True):
        website_api_request("create_pending", {"token": token, "row": row})
    else:
        data = load_pending()
        data.setdefault("pending", {})[token] = row
        atomic_write_json(pending_links_path(), data)
    return token, lifetime_minutes


def load_links() -> Dict[str, str]:
    if config.get("use_remote_website_api", True):
        # Remote mode does not bulk-load all links. Use get_link_for_discord_id instead.
        return {}
    data = read_json(links_path(), {"links": {}})
    links = data.setdefault("links", {})
    return {str(k): str(v) for k, v in links.items() if v and STEAM64_RE.match(str(v))}


def save_links(links: Dict[str, str]) -> None:
    data = read_json(links_path(), {"links": {}, "meta": {}})
    data["links"] = links
    atomic_write_json(links_path(), data)


def get_link_for_discord_id(discord_id: str) -> Optional[str]:
    if config.get("use_remote_website_api", True):
        body = website_api_request("get_link", {"discord_user_id": str(discord_id)})
        steam64 = str(body.get("steam64") or "")
        return steam64 if body.get("linked") and STEAM64_RE.match(steam64) else None
    return load_links().get(str(discord_id))


def unlink_discord_id(discord_id: str) -> None:
    if config.get("use_remote_website_api", True):
        website_api_request("unlink", {"discord_user_id": str(discord_id)})
    else:
        links = load_links()
        links.pop(str(discord_id), None)
        save_links(links)


# -------------------------
# DayZ queue helpers
# -------------------------

def get_server_path(server: str) -> Path:
    servers = config.get("servers", {})
    if server not in servers:
        raise ValueError(f"Unknown server `{server}`.")
    return Path(servers[server])


def queue_path(profile_kit_dir: Path) -> Path:
    return profile_kit_dir / "DiscordQueue.json"


def responses_path(profile_kit_dir: Path) -> Path:
    return profile_kit_dir / "DiscordResponses.json"


def kit_config_path(profile_kit_dir: Path) -> Path:
    return profile_kit_dir / "KitConfig.json"


def cooldown_path(profile_kit_dir: Path, steam64: str) -> Path:
    return profile_kit_dir / "Cooldowns" / f"{steam64}.json"


def is_discord_visible_kit(kit: Dict[str, Any]) -> bool:
    """Hide website/points kits from Discord while keeping them usable by the website worker/game."""
    name = str(kit.get("Name", "")).strip()

    # Easy fix: all points/special kits use special_ names.
    if name.lower().startswith("special_"):
        return False

    # Optional future-proof switch if you add it to KitConfig.json.
    if kit.get("ShowInDiscord") is False:
        return False

    return True


def load_kits(profile_kit_dir: Path) -> List[Dict[str, Any]]:
    cfg = read_json(kit_config_path(profile_kit_dir), {"Kits": []})
    return [
        kit for kit in cfg.get("Kits", [])
        if kit.get("Enabled", True) and is_discord_visible_kit(kit)
    ]


def find_kit(profile_kit_dir: Path, kit_name: str) -> Optional[Dict[str, Any]]:
    wanted = kit_name.lower()
    for kit in load_kits(profile_kit_dir):
        if str(kit.get("Name", "")).lower() == wanted:
            return kit
    return None


def format_remaining(seconds: int) -> str:
    if seconds <= 0:
        return "ready now"
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, _ = divmod(seconds, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    return " ".join(parts) if parts else "less than 1m"


def get_cooldown_text(profile_kit_dir: Path, steam64: str, kit_name: str) -> str:
    kit = find_kit(profile_kit_dir, kit_name)
    if not kit:
        return "unknown kit"
    data = read_json(cooldown_path(profile_kit_dir, steam64), {"Cooldowns": []})
    last = 0
    for row in data.get("Cooldowns", []):
        if str(row.get("KitName", "")).lower() == kit_name.lower():
            last = int(row.get("LastClaimUTC", 0) or 0)
            break
    cooldown = int(kit.get("CooldownSeconds", 0) or 0)
    return format_remaining((last + cooldown) - now_utc())


def add_request(profile_kit_dir: Path, kit_request: Dict[str, Any]) -> None:
    path = queue_path(profile_kit_dir)
    data = read_json(path, {"Requests": []})
    data.setdefault("Requests", [])
    data["Requests"].append(kit_request)
    atomic_write_json(path, data)


def find_response(profile_kit_dir: Path, request_id: str) -> Optional[Dict[str, Any]]:
    data = read_json(responses_path(profile_kit_dir), {"Responses": []})
    for response in reversed(data.get("Responses", [])):
        if response.get("RequestId") == request_id:
            return response
    return None


class KitBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        super().__init__(command_prefix="!unused", intents=intents)

    async def setup_hook(self) -> None:
        guild_id = int(config.get("guild_id", 0) or 0)
        if guild_id:
            guild = discord.Object(id=guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print(f"[DISCORD] Synced slash commands to guild {guild_id}.")
        else:
            await self.tree.sync()
            print("[DISCORD] Synced global slash commands. Global commands can take longer to show up.")


bot = KitBot()


def allowed_channel(interaction: discord.Interaction) -> bool:
    allowed_id = int(config.get("allowed_channel_id", 0) or 0)
    return allowed_id == 0 or interaction.channel_id == allowed_id


def reply_ephemeral() -> bool:
    return bool(config.get("ephemeral_replies", True))


def build_website_connect_link(token: str) -> str:
    base = str(config["website_connect_url"]).rstrip("/")
    return base + "?" + urlencode({"token": token})


async def send_connect_message(interaction: discord.Interaction, reason: str = "") -> None:
    try:
        token, lifetime = create_pending_link(interaction.user)
        url = build_website_connect_link(token)
    except Exception as exc:
        if interaction.response.is_done():
            await interaction.followup.send(f"Discord linking is not configured correctly: {exc}", ephemeral=True)
        else:
            await interaction.response.send_message(f"Discord linking is not configured correctly: {exc}", ephemeral=True)
        return

    text = reason or "Connect your Discord account to your website account before redeeming kits."
    text += (
        f"\n\nClick the button below, log into the Your Server website if needed, "
        f"confirm the link, then come back and use `/kit`. This link expires in {lifetime} minutes."
    )
    view = discord.ui.View(timeout=None)
    view.add_item(discord.ui.Button(label="Connect on website", url=url))
    if interaction.response.is_done():
        await interaction.followup.send(text, view=view, ephemeral=True)
    else:
        await interaction.response.send_message(text, view=view, ephemeral=True)


async def server_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    names = list(config.get("servers", {}).keys())
    current = current.lower()
    return [app_commands.Choice(name=name, value=name) for name in names if current in name.lower()][:25]


async def kit_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    server = getattr(interaction.namespace, "server", None) or config.get("default_server")
    try:
        profile_dir = get_server_path(server)
        kits = load_kits(profile_dir)
    except Exception:
        kits = []
    current = current.lower()
    choices = []
    for kit_row in kits:
        name = str(kit_row.get("Name", ""))
        display = str(kit_row.get("DisplayName", name))
        if current in name.lower() or current in display.lower():
            choices.append(app_commands.Choice(name=f"{display} [{name}]", value=name))
    return choices[:25]


@bot.event
async def on_ready() -> None:
    print(f"[DISCORD] Logged in as {bot.user}.")
    if config.get("use_remote_website_api", True):
        print(f"[LINK] Remote website API: {config['website_api_url']}")
    else:
        print(f"[LINK] Shared link folder: {link_data_dir()}")
    print(f"[LINK] Website connect URL: {config['website_connect_url']}")


@bot.tree.command(name="connect", description="Connect your Discord account to your Your Server website/Steam account.")
async def connect_command(interaction: discord.Interaction) -> None:
    if not allowed_channel(interaction):
        await interaction.response.send_message("Use the kit channel for this command.", ephemeral=True)
        return
    await send_connect_message(interaction)


@bot.tree.command(name="unlinksteam", description="Remove your Discord kit link.")
async def unlinksteam_command(interaction: discord.Interaction) -> None:
    try:
        unlink_discord_id(str(interaction.user.id))
    except Exception as exc:
        await interaction.response.send_message(f"Could not unlink: {exc}", ephemeral=True)
        return
    await interaction.response.send_message("Your Discord kit link was removed. Your website Steam link was not changed.", ephemeral=True)


@bot.tree.command(name="kit", description="Redeem a DayZ kit through Discord.")
@app_commands.describe(server="Server/map", kit="Kit to redeem")
@app_commands.autocomplete(server=server_autocomplete, kit=kit_autocomplete)
async def kit_command(interaction: discord.Interaction, server: str, kit: str) -> None:
    if not allowed_channel(interaction):
        await interaction.response.send_message("Use the kit channel for this command.", ephemeral=True)
        return

    try:
        steam64 = get_link_for_discord_id(str(interaction.user.id))
    except Exception as exc:
        await interaction.response.send_message(f"Could not check your website Steam link: {exc}", ephemeral=True)
        return

    if not steam64:
        await send_connect_message(
            interaction,
            "Your Discord is not connected to your Your Server website account yet, so I do not know which SteamID gets the kit.",
        )
        return

    try:
        profile_dir = get_server_path(server)
    except ValueError as exc:
        await interaction.response.send_message(str(exc), ephemeral=True)
        return

    selected_kit = find_kit(profile_dir, kit)
    if not selected_kit:
        await interaction.response.send_message(
            f"Unknown kit `{kit}` for `{server}`. Check KitConfig.json or use autocomplete.", ephemeral=True
        )
        return

    request_id = uuid.uuid4().hex
    kit_request = {
        "RequestId": request_id,
        "DiscordUserId": str(interaction.user.id),
        "DiscordUserName": str(interaction.user),
        "Steam64": steam64,
        "KitName": selected_kit.get("Name", kit),
        "CreatedUTC": now_utc(),
        "Status": "pending",
        "Message": "",
    }
    add_request(profile_dir, kit_request)
    await interaction.response.defer(ephemeral=reply_ephemeral(), thinking=True)

    wait_seconds = int(config.get("response_wait_seconds", 25) or 25)
    poll_seconds = int(config.get("response_poll_seconds", 2) or 2)
    deadline = time.time() + wait_seconds
    response = None
    while time.time() < deadline:
        await asyncio.sleep(poll_seconds)
        response = find_response(profile_dir, request_id)
        if response:
            break

    display = selected_kit.get("DisplayName", kit)
    if not response:
        await interaction.followup.send(
            f"Queued `{display}` for `{server}`, but the DayZ server did not answer yet. "
            "Make sure the mod is loaded and you are online in-game.",
            ephemeral=reply_ephemeral(),
        )
        return

    if response.get("Success"):
        await interaction.followup.send(
            f"✅ Redeemed `{display}` on `{server}`. It should be in your inventory now.",
            ephemeral=reply_ephemeral(),
        )
    else:
        await interaction.followup.send(
            f"❌ Could not redeem `{display}` on `{server}`: {response.get('Message', 'Unknown error')}",
            ephemeral=reply_ephemeral(),
        )


@bot.tree.command(name="kitstatus", description="Check your linked Steam and kit cooldowns.")
@app_commands.describe(server="Server/map")
@app_commands.autocomplete(server=server_autocomplete)
async def kitstatus_command(interaction: discord.Interaction, server: str) -> None:
    try:
        steam64 = get_link_for_discord_id(str(interaction.user.id))
    except Exception as exc:
        await interaction.response.send_message(f"Could not check your website Steam link: {exc}", ephemeral=True)
        return

    if not steam64:
        await send_connect_message(interaction, "Your Discord is not connected to your Your Server website account yet.")
        return

    try:
        profile_dir = get_server_path(server)
    except ValueError as exc:
        await interaction.response.send_message(str(exc), ephemeral=True)
        return

    kits = load_kits(profile_dir)
    if not kits:
        await interaction.response.send_message(
            f"No kits found for `{server}`. Check KitConfig.json and the profile path in the bot config.", ephemeral=True
        )
        return

    lines = [f"Steam64 from website link: `{steam64}`", f"Server: `{server}`", ""]
    for row in kits:
        name = str(row.get("Name", ""))
        display = str(row.get("DisplayName", name))
        lines.append(f"**{display}**: {get_cooldown_text(profile_dir, steam64, name)}")
    await interaction.response.send_message("\n".join(lines), ephemeral=True)


@bot.tree.command(name="kitservers", description="Show configured DayZ kit servers.")
async def kitservers_command(interaction: discord.Interaction) -> None:
    names = list(config.get("servers", {}).keys())
    default = config.get("default_server", "")
    text = "Configured servers: " + ", ".join(f"`{name}`" for name in names)
    if default:
        text += f"\nDefault server: `{default}`"
    await interaction.response.send_message(text, ephemeral=True)


def main() -> None:
    print("[APP] Starting Your Server Website Integrated Kit Bot")
    bot.run(config["discord_token"])


if __name__ == "__main__":
    main()
