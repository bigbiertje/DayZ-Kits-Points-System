CONNECTED DISCORD BOT

This bot connects to the Python website API.

Commands:

/link
Shows users the website account linking page.

/points
Reads the user's points from the website by Discord ID.

/pointkits server:server1
Shows available point kits from the website.

/buypointkit server:server1 kit:special_blackmarket
Creates a website kit order by Discord ID and charges points.

Important:
Players must link Discord and Steam on the website first.

Website account links page:

/account/links

Discord OAuth redirect URL in Discord Developer Portal:

http://localhost:8080/auth/discord/callback

For public hosting, replace localhost with your domain.
