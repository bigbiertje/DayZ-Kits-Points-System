@echo off
cd /d "%~dp0"

echo Installing requirements...
py -m pip install -r requirements.txt

echo.
echo Starting DayZ Kits ^& Points Python Website...
echo Open: http://localhost:8080
echo.
echo IMPORTANT: Change these secrets before public use.
echo.

set DZKP_PORT=8080
set DZKP_SECRET_KEY=CHANGE_THIS_SITE_SECRET
set DZKP_API_SECRET=CHANGE_THIS_API_SECRET
set DZKP_API_READ_SECRET=CHANGE_THIS_API_SECRET
set DZKP_API_WRITE_SECRET=CHANGE_THIS_API_SECRET
set DZKP_ADMIN_USERNAME=admin
set DZKP_ADMIN_PASSWORD=change-this-admin-password

set DZKP_PUBLIC_BASE_URL=http://localhost:8080
set DZKP_DISCORD_CLIENT_ID=CHANGE_DISCORD_CLIENT_ID
set DZKP_DISCORD_CLIENT_SECRET=CHANGE_DISCORD_CLIENT_SECRET
set DZKP_DISCORD_REDIRECT_URI=http://localhost:8080/auth/discord/callback

py app.py
pause
