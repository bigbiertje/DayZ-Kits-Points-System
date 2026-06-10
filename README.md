<<<<<<< HEAD
# DayZ Kits & Points - Complete Public Steam + Discord Edition v1.6.2

This is the complete public package.

It includes:

- Python website running on a port
- SQLite database, no MySQL needed
- Login/register system
- Player dashboard
- Points balance/history
- Point kit shop
- Admin panel
- DayZ mod source
- Profile configs
- Workers/API bridge
- Optional Discord bot for free kits only
- Docs and helper scripts

No old PHP website is included in this package.

---

## Folder overview

```text
01_PYTHON_WEBSITE
  Flask + SQLite website.
  Runs on a port, default 8080.

02_DAYZ_MOD_SOURCE
  DayZ mod source.
  Pack this into DayZ_KitsPoints.pbo.

03_PROFILE_EXAMPLES
  Copy DayZKitsPoints folder into each server profile.

04_WORKERS
  Python workers.
  One sends point events to website.
  One sends bought kits to the game queue.

05_OPTIONAL_DISCORD_BOT_FREE_KITS_ONLY
  Optional Discord bot for free cooldown kits only.
  It hides point kits that start with special_.

06_DOCS
  Extra guides.

07_TOOLS
  Secret generator, helper tools, and Python API client.

08_INSTALL_CHECKLIST
  Quick checklists.
```

---

## How the full system works

```text
Player kills zombies or earns points in-game
↓
DayZ mod writes events to PointEvents.json
↓
points_events_worker.py sends those points to the Python website
↓
Player logs in and buys a point kit
↓
special_kits_worker.py pulls pending orders
↓
Worker writes kit request into DiscordQueue.json
↓
DayZ mod gives the kit in-game
```

---

## Quick install

### 1. Start the website

Go to:

```text
01_PYTHON_WEBSITE
```

Run:

```text
run_windows.bat
```

Open:

```text
http://localhost:8080
```

Default admin:

```text
admin
change-this-admin-password
```

Change this before public use.

---

### 2. Generate secrets

Go to:

```text
01_PYTHON_WEBSITE
```

Run:

```text
GENERATE_SECRETS_WINDOWS.bat
```

Use the API secret in:

```text
01_PYTHON_WEBSITE/run_windows.bat
04_WORKERS/points_events_worker_config.json
04_WORKERS/special_kits_worker_config.json
```

The API secret must match everywhere.

---

### 3. Pack the DayZ PBO

Pack this folder only:

```text
02_DAYZ_MOD_SOURCE/@DayZKitsPoints/Addons/DayZ_KitsPoints
```

Output:

```text
DayZ_KitsPoints.pbo
```

Install it like:

```text
@DayZKitsPoints/Addons/DayZ_KitsPoints.pbo
```

Start it as either:

```text
-mod=@DayZKitsPoints
```

or server-side if your server setup supports it:

```text
-serverMod=@DayZKitsPoints
```

---

### 4. Copy the profile folder

Copy:

```text
03_PROFILE_EXAMPLES/DayZKitsPoints
```

to your server profile folder:

```text
profiles/DayZKitsPoints
```

Edit:

```text
PointsConfig.json
```

Make sure:

```json
"ServerKey": "server1"
```

matches the website kit server key and worker config.

---

### 5. Configure workers

Edit:

```text
04_WORKERS/points_events_worker_config.json
04_WORKERS/special_kits_worker_config.json
```

Set:

```json
"website_base_url": "http://127.0.0.1:8080"
```

or your public website URL.

Set:

```json
"api_secret": "YOUR_SECRET"
```

same as website.

Set the profile file paths.

Example:

```json
"point_event_paths": {
  "server1": "C:/Path/To/Your/Server/profiles/DayZKitsPoints/PointEvents.json"
}
```

Example:

```json
"servers": {
  "server1": "C:/Path/To/Your/Server/profiles/DayZKitsPoints/DiscordQueue.json"
}
```

Run:

```text
RUN_POINTS_WORKER_WINDOWS.bat
RUN_SPECIAL_KITS_WORKER_WINDOWS.bat
```

Keep both windows open.

---

## Important naming rule

Website point kit internal name must match DayZ KitConfig.json.

Example website kit:

```text
special_blackmarket
```

must exist in KitConfig.json as:

```json
"Name": "special_blackmarket"
```

---

## Free kits vs point kits

Free kits are normal cooldown kits:

```text
medical
food
weapon
building
```

Point kits start with:

```text
special_
```

Example:

```text
special_medical
special_ammo
special_builder
special_blackmarket
```

The optional Discord bot hides `special_` kits by default, so players cannot claim point kits through Discord.

---

## Public hosting warning

For public internet use, do not leave defaults.

Change:

- DZKP_SECRET_KEY
- DZKP_API_SECRET
- DZKP_ADMIN_PASSWORD

Use HTTPS through Nginx, Caddy, Cloudflare Tunnel, or another reverse proxy.

Backup:

```text
01_PYTHON_WEBSITE/data/site.db
```

That file contains users, points, kits, and orders.

---

## Support/debug checklist

If points do not show:

1. Check DayZ wrote to `PointEvents.json`.
2. Check `points_events_worker.py` is running.
3. Check API secret matches.
4. Check Steam64 exists on the website account.

If bought kits stay pending:

1. Check `special_kits_worker.py` is running.
2. Check `server_key` matches.
3. Check `DiscordQueue.json` path is correct.
4. Check kit name exists in `KitConfig.json`.

If the DayZ mod does not load:

1. Check server RPT for `DayZ_KitsPoints`.
2. Check PBO prefix/path.
3. Make sure `.c` files are inside the packed PBO.
4. Make sure config.cpp points to `DayZ_KitsPoints/scripts/...`.


---

## New in v1.5: full API system

This package now includes a proper `/api/v1` system.

Useful endpoints:

```text
GET  /api/health
POST /api/v1/kits
POST /api/v1/users
POST /api/v1/user/by-steam/<steam64>
POST /api/v1/points/<steam64>
POST /api/v1/points/add
POST /api/v1/points/set
POST /api/v1/orders
POST /api/v1/orders/pending
POST /api/v1/orders/create
POST /api/v1/orders/mark-delivered
POST /api/v1/orders/mark-failed
```

Docs:

```text
06_DOCS/API_SYSTEM_FULL_README.txt
06_DOCS/API_CURL_EXAMPLES_WINDOWS.txt
07_TOOLS/dayz_kits_points_api_client.py
```


---

## New in v1.6: Steam + Discord connect

Website now includes:

```text
/auth/steam
/auth/discord
/account/links
```

Discord bot now includes:

```text
/link
/points
/pointkits
/buypointkit
```

New API endpoints:

```text
/api/v1/user/by-discord/<discord_id>
/api/v1/points/discord/<discord_id>
/api/v1/orders/create-by-discord
```

Docs:

```text
06_DOCS/STEAM_DISCORD_CONNECT_FULL_README.txt
05_DISCORD_BOT_CONNECTED_TO_WEBSITE_API/README_DISCORD_BOT.txt
```


---

## New in v1.6.2: editable profile names

Players can now edit their website name after logging in with Steam or Discord.

Route:

```text
/account/profile
```

They can change:

```text
Website username
Email
```

Username is validated and must be unique.
=======
# DayZ-Kits-Points-System
# DayZ Kits & Points System

Standalone DayZ kit and points system with Python website, Steam/Discord linking, API, workers, and optional Discord bot.

Then click:
>>>>>>> ac63974c930750091fccc49dec14276ef0d851d4
