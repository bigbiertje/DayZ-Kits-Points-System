PYTHON WEBSITE

This folder is the complete public Python web panel.

Run on Windows:

run_windows.bat

Default local URL:

http://localhost:8080

Default admin:

username: admin
password: change-this-admin-password

Before public use:
1. Run GENERATE_SECRETS_WINDOWS.bat
2. Put the generated values in run_windows.bat or environment variables
3. Change DZKP_ADMIN_PASSWORD
4. Use HTTPS/reverse proxy if public internet facing
5. Backup data/site.db

The website uses SQLite and creates the database automatically on first run.
