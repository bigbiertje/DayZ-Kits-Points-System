# DayZ Kits & Points API System v1.5

This version includes a proper API system so workers, Discord bots, admin scripts, or other websites can connect to the Python panel and read/write data.

## Secrets

The website supports:

```text
DZKP_API_SECRET
DZKP_API_READ_SECRET
DZKP_API_WRITE_SECRET
```

For simple installs, use the same secret for all three.

For advanced installs:

- `DZKP_API_READ_SECRET` can read data.
- `DZKP_API_WRITE_SECRET` can write/change data.
- `DZKP_API_SECRET` is the fallback master secret.

You can send the secret in JSON:

```json
{
  "api_secret": "YOUR_SECRET"
}
```

Or as a header:

```text
X-API-Secret: YOUR_SECRET
```

Or:

```text
Authorization: Bearer YOUR_SECRET
```

## Health

```text
GET /api/health
```

No secret needed.

## API config/readme endpoint

```text
GET or POST /api/v1/config
```

Needs read secret.

## Kits

### Read kits

```text
GET or POST /api/v1/kits
```

JSON:

```json
{
  "api_secret": "YOUR_SECRET",
  "server_key": "server1",
  "enabled_only": true
}
```

### Create kit

```text
POST /api/v1/kits/create
```

JSON:

```json
{
  "api_secret": "YOUR_SECRET",
  "kit_name": "special_blackmarket",
  "display_name": "Black Market Kit",
  "description": "High value reward kit.",
  "cost": 2500,
  "server_key": "server1",
  "enabled": true
}
```

## Users

### List/search users

```text
GET or POST /api/v1/users
```

JSON:

```json
{
  "api_secret": "YOUR_SECRET",
  "search": "7656119",
  "limit": 100
}
```

### Get user by Steam64

```text
GET or POST /api/v1/user/by-steam/<steam64>
```

JSON:

```json
{
  "api_secret": "YOUR_SECRET"
}
```

## Points

### Read points by Steam64

```text
GET or POST /api/v1/points/<steam64>
```

Returns:

- username
- points
- total earned
- total spent
- recent history

### Add/remove points

```text
POST /api/v1/points/add
```

JSON:

```json
{
  "api_secret": "YOUR_SECRET",
  "steam64": "76561190000000000",
  "points": 10,
  "reason": "normal_zombie_kill",
  "reference": "server1"
}
```

Use negative points to remove points:

```json
{
  "points": -50
}
```

### Set exact points

```text
POST /api/v1/points/set
```

JSON:

```json
{
  "api_secret": "YOUR_SECRET",
  "steam64": "76561190000000000",
  "points": 1000,
  "reason": "admin_fix"
}
```

## Orders

### List orders

```text
GET or POST /api/v1/orders
```

Filters:

```json
{
  "api_secret": "YOUR_SECRET",
  "status": "pending",
  "server_key": "server1",
  "steam64": "76561190000000000",
  "limit": 100
}
```

### Read pending orders

```text
GET or POST /api/v1/orders/pending
```

JSON:

```json
{
  "api_secret": "YOUR_SECRET",
  "server_key": "server1"
}
```

This is what the special kits worker reads.

### Create order

```text
POST /api/v1/orders/create
```

JSON:

```json
{
  "api_secret": "YOUR_SECRET",
  "steam64": "76561190000000000",
  "kit_name": "special_blackmarket",
  "server_key": "server1",
  "charge_points": true
}
```

This lets Discord bots or external tools buy a point kit through the API.

If `charge_points` is true, the API checks balance and subtracts points.

If false, it creates a free/admin order.

### Mark delivered

```text
POST /api/v1/orders/mark-delivered
```

JSON:

```json
{
  "api_secret": "YOUR_SECRET",
  "order_id": 1,
  "message": "written to queue"
}
```

### Mark failed

```text
POST /api/v1/orders/mark-failed
```

JSON:

```json
{
  "api_secret": "YOUR_SECRET",
  "order_id": 1,
  "message": "queue path not found"
}
```

## Python API client

Included:

```text
07_TOOLS/dayz_kits_points_api_client.py
```

Example:

```python
from dayz_kits_points_api_client import DayZKitsPointsAPI

api = DayZKitsPointsAPI("http://127.0.0.1:8080", "YOUR_SECRET")

print(api.get_kits("server1"))
print(api.get_points("76561190000000000"))
api.add_points("76561190000000000", 10, "test", "server1")
api.create_order("76561190000000000", "special_blackmarket", "server1", True)
```

## Compatibility endpoints

The old basic endpoints still exist:

```text
/api/points/add
/api/orders/pending
/api/orders/mark-delivered
```

But new scripts should use:

```text
/api/v1/...
```


# Steam + Discord API additions v1.6

## User by Discord ID

```text
GET or POST /api/v1/user/by-discord/<discord_id>
```

## Points by Discord ID

```text
GET or POST /api/v1/points/discord/<discord_id>
```

## Create order by Discord ID

```text
POST /api/v1/orders/create-by-discord
```

JSON:

```json
{
  "api_secret": "YOUR_SECRET",
  "discord_id": "123456789012345678",
  "kit_name": "special_blackmarket",
  "server_key": "server1",
  "charge_points": true
}
```

The website finds the linked user by Discord ID, checks that Steam is linked, subtracts points, and creates a pending kit order.
