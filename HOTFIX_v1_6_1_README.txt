HOTFIX v1.6.1

Fixed website startup crash:

sqlite3.OperationalError: Cannot add a UNIQUE column

Reason:
SQLite does not allow adding a new UNIQUE column with ALTER TABLE.

Fix:
discord_id is now added as TEXT, then uniqueness is enforced with:

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_discord_id_unique
ON users(discord_id) WHERE discord_id IS NOT NULL

Also added/verified import re for Steam OpenID callback parsing.

Install:
Replace your v1.6 package with this v1.6.1 package.
If you already created a broken data/site.db, you can delete it before first real use.
