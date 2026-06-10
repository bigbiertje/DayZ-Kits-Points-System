# Steam + Discord Connect Setup

This version adds proper account linking.

## Why it matters

Typing Steam64 manually works, but it is easy to fake or mistype.

This version lets players:

- Login/link with Steam through Steam OpenID
- Login/link with Discord through Discord OAuth2
- Use Discord bot commands tied to their website account
- Buy point kits from Discord using their linked account

## Website routes

```text
/auth/steam
/auth/steam/callback

/auth/discord
/auth/discord/callback

/account/links
```

## Steam setup

Steam OpenID does not need a client secret.

Set this:

```text
DZKP_PUBLIC_BASE_URL=http://localhost:8080
```

For public use:

```text
DZKP_PUBLIC_BASE_URL=https://yourdomain.com
```

Players can click:

```text
Login with Steam
```

or open:

```text
/account/links
```

and link Steam.

## Discord OAuth setup

1. Go to Discord Developer Portal.
2. Create an application.
3. Open OAuth2.
4. Add redirect URL:

```text
http://localhost:8080/auth/discord/callback
```

For public use:

```text
https://yourdomain.com/auth/discord/callback
```

5. Copy Client ID and Client Secret.
6. Put them in website environment/run file:

```text
DZKP_DISCORD_CLIENT_ID=YOUR_CLIENT_ID
DZKP_DISCORD_CLIENT_SECRET=YOUR_CLIENT_SECRET
DZKP_DISCORD_REDIRECT_URI=http://localhost:8080/auth/discord/callback
```

## Discord bot setup

Go to:

```text
05_DISCORD_BOT_CONNECTED_TO_WEBSITE_API
```

Edit:

```text
discord_bot_config.json
```

Set:

```json
{
  "discord_bot_token": "YOUR_BOT_TOKEN",
  "website_base_url": "http://127.0.0.1:8080",
  "api_secret": "YOUR_API_SECRET"
}
```

Run:

```text
RUN_DISCORD_BOT_WINDOWS.bat
```

## Discord bot commands

```text
/link
```

Gives the player the website account link page.

```text
/points
```

Shows their website points by Discord ID.

```text
/pointkits server:server1
```

Shows available point kits.

```text
/buypointkit server:server1 kit:special_blackmarket
```

Buys a point kit through the website API.

## Important

For `/points` and `/buypointkit` to work:

1. Player must login/link Discord on website.
2. Player must link Steam on website.
3. Steam64 must exist because the DayZ queue needs Steam64 to deliver the kit.
