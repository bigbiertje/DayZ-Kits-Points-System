
import os
import re
import json
import sqlite3
import secrets
import urllib.parse
import urllib.request
from datetime import datetime
from functools import wraps

from flask import Flask, request, redirect, render_template, session, flash, jsonify, url_for
from werkzeug.security import generate_password_hash, check_password_hash

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_DIR, "data")
DB_PATH = os.environ.get("DZKP_DB_PATH", os.path.join(DATA_DIR, "site.db"))

DEFAULT_PORT = int(os.environ.get("DZKP_PORT", "8080"))
SECRET_KEY = os.environ.get("DZKP_SECRET_KEY", "CHANGE_ME_RUN_GENERATE_SECRET")
API_SECRET = os.environ.get("DZKP_API_SECRET", "CHANGE_ME_API_SECRET")

API_READ_SECRET = os.environ.get("DZKP_API_READ_SECRET", API_SECRET)
API_WRITE_SECRET = os.environ.get("DZKP_API_WRITE_SECRET", API_SECRET)


def api_payload():
    if request.method == "GET":
        return dict(request.args)
    return request.get_json(force=True, silent=True) or {}


def api_auth(payload=None, mode="write"):
    payload = payload or api_payload()
    sent = (
        payload.get("api_secret")
        or request.headers.get("X-API-Secret")
        or request.headers.get("Authorization", "").replace("Bearer ", "")
    )

    if mode == "read":
        return sent in (API_READ_SECRET, API_WRITE_SECRET, API_SECRET)
    return sent in (API_WRITE_SECRET, API_SECRET)


def api_fail(message, code=400):
    return jsonify({"ok": False, "error": message}), code


def row_to_dict(row):
    return dict(row) if row else None


def rows_to_dicts(rows):
    return [dict(row) for row in rows]


def get_points_by_user_id(conn, user_id):
    account = get_or_create_points_account(conn, user_id)
    return {
        "points": account["points"],
        "total_earned": account["total_earned"],
        "total_spent": account["total_spent"],
        "updated_at": account["updated_at"],
    }

ADMIN_USERNAME = os.environ.get("DZKP_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("DZKP_ADMIN_PASSWORD", "change-this-admin-password")

PUBLIC_BASE_URL = os.environ.get("DZKP_PUBLIC_BASE_URL", f"http://127.0.0.1:{DEFAULT_PORT}").rstrip("/")

# Steam OpenID
STEAM_OPENID_URL = "https://steamcommunity.com/openid/login"

# Discord OAuth2
DISCORD_CLIENT_ID = os.environ.get("DZKP_DISCORD_CLIENT_ID", "")
DISCORD_CLIENT_SECRET = os.environ.get("DZKP_DISCORD_CLIENT_SECRET", "")
DISCORD_REDIRECT_URI = os.environ.get("DZKP_DISCORD_REDIRECT_URI", PUBLIC_BASE_URL + "/auth/discord/callback")
DISCORD_AUTHORIZE_URL = "https://discord.com/oauth2/authorize"
DISCORD_TOKEN_URL = "https://discord.com/api/oauth2/token"
DISCORD_USER_URL = "https://discord.com/api/users/@me"


def add_column_if_missing(conn, table, column, definition):
    cols = [row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def http_post_form(url, data, headers=None):
    encoded = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(url, data=encoded, headers=headers or {})
    with urllib.request.urlopen(req, timeout=20) as response:
        return response.read().decode("utf-8")


def http_get_json(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def http_post_jsonish_form(url, data, headers=None):
    raw = http_post_form(url, data, headers or {})
    return json.loads(raw)


def make_state(name):
    state = secrets.token_urlsafe(24)
    session[name] = state
    return state


def check_state(name, value):
    expected = session.pop(name, None)
    return expected and value and expected == value

app = Flask(__name__)
app.secret_key = SECRET_KEY


def db():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def now():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def init_db():
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT,
                steam64 TEXT UNIQUE,
                password_hash TEXT NOT NULL,
                is_admin INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS points_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                points INTEGER NOT NULL DEFAULT 0,
                total_earned INTEGER NOT NULL DEFAULT 0,
                total_spent INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS points_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                change_amount INTEGER NOT NULL,
                reason TEXT NOT NULL,
                reference TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS special_kits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kit_name TEXT NOT NULL,
                display_name TEXT NOT NULL,
                description TEXT,
                cost INTEGER NOT NULL,
                server_key TEXT NOT NULL DEFAULT 'server1',
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS special_kit_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                steam64 TEXT NOT NULL,
                kit_name TEXT NOT NULL,
                display_name TEXT NOT NULL,
                server_key TEXT NOT NULL,
                cost INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                delivered_at TEXT,
                worker_message TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
            """
        )

        add_column_if_missing(conn, "users", "steam_name", "TEXT")
        add_column_if_missing(conn, "users", "steam_avatar", "TEXT")
        add_column_if_missing(conn, "users", "discord_id", "TEXT")
        add_column_if_missing(conn, "users", "discord_username", "TEXT")
        add_column_if_missing(conn, "users", "discord_global_name", "TEXT")
        add_column_if_missing(conn, "users", "discord_avatar", "TEXT")

        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_discord_id_unique ON users(discord_id) WHERE discord_id IS NOT NULL")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_steam64_unique ON users(steam64) WHERE steam64 IS NOT NULL")

        admin = conn.execute("SELECT id FROM users WHERE username = ?", (ADMIN_USERNAME,)).fetchone()
        if not admin:
            conn.execute(
                "INSERT INTO users (username, email, steam64, password_hash, is_admin, created_at) VALUES (?, ?, ?, ?, 1, ?)",
                (
                    ADMIN_USERNAME,
                    "admin@example.com",
                    None,
                    generate_password_hash(ADMIN_PASSWORD),
                    now(),
                ),
            )
            user_id = conn.execute("SELECT id FROM users WHERE username = ?", (ADMIN_USERNAME,)).fetchone()["id"]
            conn.execute(
                "INSERT INTO points_accounts (user_id, points, total_earned, total_spent, updated_at) VALUES (?, 0, 0, 0, ?)",
                (user_id, now()),
            )

        count = conn.execute("SELECT COUNT(*) AS c FROM special_kits").fetchone()["c"]
        if count == 0:
            demo_kits = [
                ("special_medical", "Medical Point Kit", "Medical supplies bought with points.", 250, "server1"),
                ("special_ammo", "Ammo Point Kit", "Ammo supplies bought with points.", 500, "server1"),
                ("special_builder", "Builder Point Kit", "Building supplies bought with points.", 1000, "server1"),
                ("special_blackmarket", "Black Market Kit", "High value reward kit bought with points.", 2500, "server1"),
            ]
            for kit_name, display_name, desc, cost, server_key in demo_kits:
                conn.execute(
                    "INSERT INTO special_kits (kit_name, display_name, description, cost, server_key, enabled, created_at) VALUES (?, ?, ?, ?, ?, 1, ?)",
                    (kit_name, display_name, desc, cost, server_key, now()),
                )


def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    with db() as conn:
        return conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user or not user["is_admin"]:
            flash("Admin access required.", "error")
            return redirect(url_for("dashboard"))
        return fn(*args, **kwargs)
    return wrapper


def get_or_create_points_account(conn, user_id):
    row = conn.execute("SELECT * FROM points_accounts WHERE user_id = ?", (user_id,)).fetchone()
    if not row:
        conn.execute(
            "INSERT INTO points_accounts (user_id, points, total_earned, total_spent, updated_at) VALUES (?, 0, 0, 0, ?)",
            (user_id, now()),
        )
        row = conn.execute("SELECT * FROM points_accounts WHERE user_id = ?", (user_id,)).fetchone()
    return row


def add_points_by_user_id(conn, user_id, amount, reason, reference=None):
    account = get_or_create_points_account(conn, user_id)
    new_points = account["points"] + amount
    if new_points < 0:
        raise ValueError("Not enough points.")

    total_earned = account["total_earned"] + max(amount, 0)
    total_spent = account["total_spent"] + abs(min(amount, 0))

    conn.execute(
        "UPDATE points_accounts SET points = ?, total_earned = ?, total_spent = ?, updated_at = ? WHERE user_id = ?",
        (new_points, total_earned, total_spent, now(), user_id),
    )
    conn.execute(
        "INSERT INTO points_history (user_id, change_amount, reason, reference, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, reason, reference, now()),
    )


@app.context_processor
def inject_user():
    return {"current_user": current_user()}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        steam64 = request.form.get("steam64", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Username and password are required. Steam can be linked after login.", "error")
            return redirect(url_for("register"))

        try:
            with db() as conn:
                conn.execute(
                    "INSERT INTO users (username, email, steam64, password_hash, is_admin, created_at) VALUES (?, ?, ?, ?, 0, ?)",
                    (username, email, steam64 or None, generate_password_hash(password), now()),
                )
                user_id = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()["id"]
                get_or_create_points_account(conn, user_id)
            flash("Account created. You can log in now.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username or Steam64 already exists.", "error")
            return redirect(url_for("register"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        with db() as conn:
            user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            flash("Logged in.", "success")
            return redirect(url_for("dashboard"))
        flash("Wrong login.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "success")
    return redirect(url_for("index"))



# ============================================================
# STEAM + DISCORD ACCOUNT LINKING
# ============================================================

@app.route("/auth/steam")
def auth_steam():
    state = make_state("steam_state")
    return_to = PUBLIC_BASE_URL + url_for("auth_steam_callback")
    params = {
        "openid.ns": "http://specs.openid.net/auth/2.0",
        "openid.mode": "checkid_setup",
        "openid.return_to": return_to + "?state=" + urllib.parse.quote(state),
        "openid.realm": PUBLIC_BASE_URL + "/",
        "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
        "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select",
    }
    return redirect(STEAM_OPENID_URL + "?" + urllib.parse.urlencode(params))


@app.route("/auth/steam/callback")
def auth_steam_callback():
    if not check_state("steam_state", request.args.get("state")):
        flash("Steam login failed: bad state.", "error")
        return redirect(url_for("login"))

    args = dict(request.args)
    claimed_id = args.get("openid.claimed_id", "")

    verify_payload = {k: v for k, v in args.items() if k.startswith("openid.")}
    verify_payload["openid.mode"] = "check_authentication"

    try:
        verify_response = http_post_form(STEAM_OPENID_URL, verify_payload)
    except Exception as e:
        flash(f"Steam verification failed: {e}", "error")
        return redirect(url_for("login"))

    if "is_valid:true" not in verify_response:
        flash("Steam verification failed.", "error")
        return redirect(url_for("login"))

    match = re.search(r"/openid/id/(\d+)", claimed_id)
    if not match:
        flash("Could not read Steam64 ID from Steam response.", "error")
        return redirect(url_for("login"))

    steam64 = match.group(1)

    with db() as conn:
        existing = conn.execute("SELECT * FROM users WHERE steam64 = ?", (steam64,)).fetchone()
        user = current_user()

        if user:
            if existing and existing["id"] != user["id"]:
                flash("That Steam account is already linked to another website account.", "error")
                return redirect(url_for("dashboard"))
            conn.execute("UPDATE users SET steam64 = ? WHERE id = ?", (steam64, user["id"]))
            flash("Steam account linked.", "success")
            return redirect(url_for("dashboard"))

        if existing:
            session["user_id"] = existing["id"]
            flash("Logged in with Steam.", "success")
            return redirect(url_for("dashboard"))

        username = "Player_" + steam64[-8:]
        password_hash = generate_password_hash(secrets.token_urlsafe(32))
        conn.execute(
            "INSERT INTO users (username, email, steam64, password_hash, is_admin, created_at) VALUES (?, ?, ?, ?, 0, ?)",
            (username, None, steam64, password_hash, now()),
        )
        new_user = conn.execute("SELECT * FROM users WHERE steam64 = ?", (steam64,)).fetchone()
        get_or_create_points_account(conn, new_user["id"])
        session["user_id"] = new_user["id"]
        flash("Account created and logged in with Steam.", "success")
        return redirect(url_for("dashboard"))


@app.route("/auth/discord")
def auth_discord():
    if not DISCORD_CLIENT_ID or not DISCORD_CLIENT_SECRET:
        flash("Discord OAuth is not configured yet.", "error")
        return redirect(url_for("dashboard") if current_user() else url_for("login"))

    state = make_state("discord_state")
    params = {
        "client_id": DISCORD_CLIENT_ID,
        "redirect_uri": DISCORD_REDIRECT_URI,
        "response_type": "code",
        "scope": "identify",
        "state": state,
        "prompt": "consent",
    }
    return redirect(DISCORD_AUTHORIZE_URL + "?" + urllib.parse.urlencode(params))


@app.route("/auth/discord/callback")
def auth_discord_callback():
    if not check_state("discord_state", request.args.get("state")):
        flash("Discord login failed: bad state.", "error")
        return redirect(url_for("login"))

    code = request.args.get("code")
    if not code:
        flash("Discord login failed: no code returned.", "error")
        return redirect(url_for("login"))

    try:
        token = http_post_jsonish_form(
            DISCORD_TOKEN_URL,
            {
                "client_id": DISCORD_CLIENT_ID,
                "client_secret": DISCORD_CLIENT_SECRET,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": DISCORD_REDIRECT_URI,
            },
            {"Content-Type": "application/x-www-form-urlencoded"},
        )
        access_token = token["access_token"]
        discord_user = http_get_json(DISCORD_USER_URL, {"Authorization": "Bearer " + access_token})
    except Exception as e:
        flash(f"Discord login failed: {e}", "error")
        return redirect(url_for("login"))

    discord_id = str(discord_user.get("id", ""))
    discord_username = str(discord_user.get("username", ""))
    discord_global_name = discord_user.get("global_name") or discord_username
    discord_avatar = discord_user.get("avatar")

    if not discord_id:
        flash("Discord login failed: missing Discord ID.", "error")
        return redirect(url_for("login"))

    with db() as conn:
        existing = conn.execute("SELECT * FROM users WHERE discord_id = ?", (discord_id,)).fetchone()
        user = current_user()

        if user:
            if existing and existing["id"] != user["id"]:
                flash("That Discord account is already linked to another website account.", "error")
                return redirect(url_for("dashboard"))
            conn.execute(
                """
                UPDATE users
                SET discord_id = ?, discord_username = ?, discord_global_name = ?, discord_avatar = ?
                WHERE id = ?
                """,
                (discord_id, discord_username, discord_global_name, discord_avatar, user["id"]),
            )
            flash("Discord account linked.", "success")
            return redirect(url_for("dashboard"))

        if existing:
            session["user_id"] = existing["id"]
            flash("Logged in with Discord.", "success")
            return redirect(url_for("dashboard"))

        username = (discord_global_name or discord_username or "Player_" + discord_id[-8:]).strip()[:32]
        if not username:
            username = "Player_" + discord_id[-8:]
        base_username = re.sub(r"[^A-Za-z0-9_.-]", "_", username)[:32] or ("Player_" + discord_id[-8:])
        username = base_username
        n = 1
        while conn.execute("SELECT id FROM users WHERE lower(username) = lower(?)", (username,)).fetchone():
            suffix = "_" + str(n)
            username = (base_username[:32-len(suffix)] + suffix)
            n += 1
        password_hash = generate_password_hash(secrets.token_urlsafe(32))
        conn.execute(
            """
            INSERT INTO users
            (username, email, steam64, password_hash, is_admin, created_at, discord_id, discord_username, discord_global_name, discord_avatar)
            VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?, ?)
            """,
            (username, None, None, password_hash, now(), discord_id, discord_username, discord_global_name, discord_avatar),
        )
        new_user = conn.execute("SELECT * FROM users WHERE discord_id = ?", (discord_id,)).fetchone()
        get_or_create_points_account(conn, new_user["id"])
        session["user_id"] = new_user["id"]
        flash("Account created and logged in with Discord. Link Steam next for in-game delivery.", "success")
        return redirect(url_for("dashboard"))



@app.route("/account/profile", methods=["GET", "POST"])
@login_required
def account_profile():
    user = current_user()

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()

        if not username:
            flash("Username cannot be empty.", "error")
            return redirect(url_for("account_profile"))

        if len(username) < 3 or len(username) > 32:
            flash("Username must be between 3 and 32 characters.", "error")
            return redirect(url_for("account_profile"))

        if not re.match(r"^[A-Za-z0-9_.-]+$", username):
            flash("Username can only use letters, numbers, dots, underscores, and dashes.", "error")
            return redirect(url_for("account_profile"))

        with db() as conn:
            existing = conn.execute(
                "SELECT id FROM users WHERE lower(username) = lower(?) AND id != ?",
                (username, user["id"]),
            ).fetchone()

            if existing:
                flash("That username is already taken.", "error")
                return redirect(url_for("account_profile"))

            conn.execute(
                "UPDATE users SET username = ?, email = ? WHERE id = ?",
                (username, email or None, user["id"]),
            )

        flash("Profile updated.", "success")
        return redirect(url_for("account_profile"))

    return render_template("account_profile.html")

@app.route("/account/links")
@login_required
def account_links():
    return render_template("account_links.html")

@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    with db() as conn:
        account = get_or_create_points_account(conn, user["id"])
        orders = conn.execute(
            "SELECT * FROM special_kit_orders WHERE user_id = ? ORDER BY id DESC LIMIT 10",
            (user["id"],),
        ).fetchall()
        history = conn.execute(
            "SELECT * FROM points_history WHERE user_id = ? ORDER BY id DESC LIMIT 10",
            (user["id"],),
        ).fetchall()
    return render_template("dashboard.html", account=account, orders=orders, history=history)


@app.route("/points")
@login_required
def points():
    user = current_user()
    with db() as conn:
        account = get_or_create_points_account(conn, user["id"])
        kits = conn.execute("SELECT * FROM special_kits WHERE enabled = 1 ORDER BY cost ASC").fetchall()
    return render_template("points.html", account=account, kits=kits)


@app.route("/buy-kit/<int:kit_id>", methods=["POST"])
@login_required
def buy_kit(kit_id):
    user = current_user()
    with db() as conn:
        kit = conn.execute("SELECT * FROM special_kits WHERE id = ? AND enabled = 1", (kit_id,)).fetchone()
        if not kit:
            flash("Kit not found.", "error")
            return redirect(url_for("points"))

        account = get_or_create_points_account(conn, user["id"])
        if account["points"] < kit["cost"]:
            flash("Not enough points.", "error")
            return redirect(url_for("points"))

        try:
            add_points_by_user_id(conn, user["id"], -kit["cost"], "buy_special_kit", kit["kit_name"])
            conn.execute(
                """
                INSERT INTO special_kit_orders
                (user_id, steam64, kit_name, display_name, server_key, cost, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
                """,
                (user["id"], user["steam64"], kit["kit_name"], kit["display_name"], kit["server_key"], kit["cost"], now()),
            )
            flash("Kit bought. It will be delivered by the worker.", "success")
        except ValueError as e:
            flash(str(e), "error")
    return redirect(url_for("dashboard"))


@app.route("/admin")
@admin_required
def admin_home():
    with db() as conn:
        users = conn.execute(
            """
            SELECT users.*, COALESCE(points_accounts.points, 0) AS points
            FROM users
            LEFT JOIN points_accounts ON points_accounts.user_id = users.id
            ORDER BY users.id DESC
            """
        ).fetchall()
        kits = conn.execute("SELECT * FROM special_kits ORDER BY id DESC").fetchall()
        orders = conn.execute("SELECT * FROM special_kit_orders ORDER BY id DESC LIMIT 50").fetchall()
    return render_template("admin/home.html", users=users, kits=kits, orders=orders)


@app.route("/admin/add-points", methods=["POST"])
@admin_required
def admin_add_points():
    user_id = int(request.form["user_id"])
    amount = int(request.form["amount"])
    reason = request.form.get("reason", "admin_adjustment")
    with db() as conn:
        try:
            add_points_by_user_id(conn, user_id, amount, reason, "admin")
            flash("Points updated.", "success")
        except ValueError as e:
            flash(str(e), "error")
    return redirect(url_for("admin_home"))


@app.route("/admin/kits/add", methods=["POST"])
@admin_required
def admin_add_kit():
    with db() as conn:
        conn.execute(
            """
            INSERT INTO special_kits
            (kit_name, display_name, description, cost, server_key, enabled, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request.form["kit_name"].strip(),
                request.form["display_name"].strip(),
                request.form.get("description", "").strip(),
                int(request.form["cost"]),
                request.form["server_key"].strip(),
                1 if request.form.get("enabled") == "on" else 0,
                now(),
            ),
        )
    flash("Kit added.", "success")
    return redirect(url_for("admin_home"))


@app.route("/admin/kits/<int:kit_id>/toggle", methods=["POST"])
@admin_required
def admin_toggle_kit(kit_id):
    with db() as conn:
        kit = conn.execute("SELECT enabled FROM special_kits WHERE id = ?", (kit_id,)).fetchone()
        if kit:
            conn.execute("UPDATE special_kits SET enabled = ? WHERE id = ?", (0 if kit["enabled"] else 1, kit_id))
    return redirect(url_for("admin_home"))


@app.route("/admin/orders/<int:order_id>/<status>", methods=["POST"])
@admin_required
def admin_order_status(order_id, status):
    if status not in ("pending", "delivered", "cancelled"):
        status = "pending"
    with db() as conn:
        conn.execute(
            "UPDATE special_kit_orders SET status = ?, delivered_at = CASE WHEN ? = 'delivered' THEN ? ELSE delivered_at END WHERE id = ?",
            (status, status, now(), order_id),
        )
    return redirect(url_for("admin_home"))


@app.route("/api/points/add", methods=["POST"])
def api_add_points():
    payload = api_payload()
    if not api_auth(payload, "write"):
        return api_fail("bad api_secret", 403)

    steam64 = str(payload.get("steam64", "")).strip()
    amount = int(payload.get("points", 0))
    reason = str(payload.get("reason", "api_points"))
    reference = str(payload.get("reference", ""))

    if not steam64 or amount == 0:
        return jsonify({"ok": False, "error": "steam64 and non-zero points are required"}), 400

    with db() as conn:
        user = conn.execute("SELECT * FROM users WHERE steam64 = ?", (steam64,)).fetchone()
        if not user:
            return jsonify({"ok": False, "error": "unknown steam64"}), 404
        add_points_by_user_id(conn, user["id"], amount, reason, reference)

    return jsonify({"ok": True})


@app.route("/api/orders/pending", methods=["POST"])
def api_pending_orders():
    payload = api_payload()
    if not api_auth(payload, "read"):
        return api_fail("bad api_secret", 403)

    server_key = str(payload.get("server_key", "")).strip()
    with db() as conn:
        if server_key:
            orders = conn.execute(
                "SELECT * FROM special_kit_orders WHERE status = 'pending' AND server_key = ? ORDER BY id ASC LIMIT 50",
                (server_key,),
            ).fetchall()
        else:
            orders = conn.execute(
                "SELECT * FROM special_kit_orders WHERE status = 'pending' ORDER BY id ASC LIMIT 50"
            ).fetchall()

    return jsonify({"ok": True, "orders": [dict(row) for row in orders]})


@app.route("/api/orders/mark-delivered", methods=["POST"])
def api_mark_delivered():
    payload = api_payload()
    if not api_auth(payload, "write"):
        return api_fail("bad api_secret", 403)

    order_id = int(payload.get("order_id", 0))
    message = str(payload.get("message", "delivered by worker"))
    with db() as conn:
        conn.execute(
            "UPDATE special_kit_orders SET status = 'delivered', delivered_at = ?, worker_message = ? WHERE id = ?",
            (now(), message, order_id),
        )
    return jsonify({"ok": True})


# ============================================================
# PUBLIC API v1
# ============================================================

@app.route("/api/health", methods=["GET"])
def api_health():
    return jsonify({
        "ok": True,
        "name": "DayZ Kits & Points API",
        "version": "1.5",
        "time": now(),
    })


@app.route("/api/v1/config", methods=["GET", "POST"])
def api_v1_config():
    payload = api_payload()
    if not api_auth(payload, "read"):
        return api_fail("bad api_secret", 403)

    return jsonify({
        "ok": True,
        "version": "1.5",
        "endpoints": {
            "health": "/api/health",
            "kits": "/api/v1/kits",
            "users": "/api/v1/users",
            "user_by_steam": "/api/v1/user/by-steam/<steam64>",
            "user_by_discord": "/api/v1/user/by-discord/<discord_id>",
            "points_by_steam": "/api/v1/points/<steam64>",
            "points_by_discord": "/api/v1/points/discord/<discord_id>",
            "add_points": "/api/v1/points/add",
            "set_points": "/api/v1/points/set",
            "orders": "/api/v1/orders",
            "pending_orders": "/api/v1/orders/pending",
            "create_order": "/api/v1/orders/create",
            "create_order_by_discord": "/api/v1/orders/create-by-discord",
            "mark_delivered": "/api/v1/orders/mark-delivered",
        }
    })


@app.route("/api/v1/kits", methods=["GET", "POST"])
def api_v1_kits():
    payload = api_payload()
    if not api_auth(payload, "read"):
        return api_fail("bad api_secret", 403)

    enabled_only = str(payload.get("enabled_only", "1")).lower() not in ("0", "false", "no")
    server_key = str(payload.get("server_key", "")).strip()

    query = "SELECT * FROM special_kits WHERE 1=1"
    params = []
    if enabled_only:
        query += " AND enabled = 1"
    if server_key:
        query += " AND server_key = ?"
        params.append(server_key)
    query += " ORDER BY cost ASC"

    with db() as conn:
        kits = conn.execute(query, params).fetchall()
    return jsonify({"ok": True, "kits": rows_to_dicts(kits)})


@app.route("/api/v1/kits/create", methods=["POST"])
def api_v1_kits_create():
    payload = api_payload()
    if not api_auth(payload, "write"):
        return api_fail("bad api_secret", 403)

    required = ["kit_name", "display_name", "cost", "server_key"]
    for key in required:
        if payload.get(key) in (None, ""):
            return api_fail(f"missing {key}", 400)

    with db() as conn:
        conn.execute(
            """
            INSERT INTO special_kits
            (kit_name, display_name, description, cost, server_key, enabled, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(payload["kit_name"]).strip(),
                str(payload["display_name"]).strip(),
                str(payload.get("description", "")).strip(),
                int(payload["cost"]),
                str(payload["server_key"]).strip(),
                1 if bool(payload.get("enabled", True)) else 0,
                now(),
            ),
        )
    return jsonify({"ok": True})


@app.route("/api/v1/users", methods=["GET", "POST"])
def api_v1_users():
    payload = api_payload()
    if not api_auth(payload, "read"):
        return api_fail("bad api_secret", 403)

    limit = min(int(payload.get("limit", 100)), 500)
    search = str(payload.get("search", "")).strip()

    with db() as conn:
        if search:
            users = conn.execute(
                """
                SELECT users.id, users.username, users.email, users.steam64, users.discord_id, users.discord_username, users.discord_global_name, users.is_admin, users.created_at,
                       COALESCE(points_accounts.points, 0) AS points
                FROM users
                LEFT JOIN points_accounts ON points_accounts.user_id = users.id
                WHERE users.username LIKE ? OR users.steam64 LIKE ? OR users.email LIKE ?
                ORDER BY users.id DESC
                LIMIT ?
                """,
                (f"%{search}%", f"%{search}%", f"%{search}%", limit),
            ).fetchall()
        else:
            users = conn.execute(
                """
                SELECT users.id, users.username, users.email, users.steam64, users.discord_id, users.discord_username, users.discord_global_name, users.is_admin, users.created_at,
                       COALESCE(points_accounts.points, 0) AS points
                FROM users
                LEFT JOIN points_accounts ON points_accounts.user_id = users.id
                ORDER BY users.id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

    return jsonify({"ok": True, "users": rows_to_dicts(users)})


@app.route("/api/v1/user/by-steam/<steam64>", methods=["GET", "POST"])
def api_v1_user_by_steam(steam64):
    payload = api_payload()
    if not api_auth(payload, "read"):
        return api_fail("bad api_secret", 403)

    with db() as conn:
        user = conn.execute(
            """
            SELECT users.id, users.username, users.email, users.steam64, users.discord_id, users.discord_username, users.discord_global_name, users.is_admin, users.created_at,
                   COALESCE(points_accounts.points, 0) AS points
            FROM users
            LEFT JOIN points_accounts ON points_accounts.user_id = users.id
            WHERE users.steam64 = ?
            """,
            (steam64,),
        ).fetchone()

    if not user:
        return api_fail("unknown steam64", 404)
    return jsonify({"ok": True, "user": row_to_dict(user)})


@app.route("/api/v1/points/<steam64>", methods=["GET", "POST"])
def api_v1_points_by_steam(steam64):
    payload = api_payload()
    if not api_auth(payload, "read"):
        return api_fail("bad api_secret", 403)

    with db() as conn:
        user = conn.execute("SELECT * FROM users WHERE steam64 = ?", (steam64,)).fetchone()
        if not user:
            return api_fail("unknown steam64", 404)
        points = get_points_by_user_id(conn, user["id"])
        history = conn.execute(
            "SELECT change_amount, reason, reference, created_at FROM points_history WHERE user_id = ? ORDER BY id DESC LIMIT 50",
            (user["id"],),
        ).fetchall()

    return jsonify({
        "ok": True,
        "steam64": steam64,
        "username": user["username"],
        "points": points,
        "history": rows_to_dicts(history),
    })


@app.route("/api/v1/points/add", methods=["POST"])
def api_v1_points_add():
    payload = api_payload()
    if not api_auth(payload, "write"):
        return api_fail("bad api_secret", 403)

    steam64 = str(payload.get("steam64", "")).strip()
    amount = int(payload.get("points", payload.get("amount", 0)))
    reason = str(payload.get("reason", "api_points"))
    reference = str(payload.get("reference", ""))

    if not steam64 or amount == 0:
        return api_fail("steam64 and non-zero points are required", 400)

    with db() as conn:
        user = conn.execute("SELECT * FROM users WHERE steam64 = ?", (steam64,)).fetchone()
        if not user:
            return api_fail("unknown steam64", 404)
        try:
            add_points_by_user_id(conn, user["id"], amount, reason, reference)
        except ValueError as e:
            return api_fail(str(e), 400)
        account = get_or_create_points_account(conn, user["id"])

    return jsonify({"ok": True, "steam64": steam64, "new_balance": account["points"]})


@app.route("/api/v1/points/set", methods=["POST"])
def api_v1_points_set():
    payload = api_payload()
    if not api_auth(payload, "write"):
        return api_fail("bad api_secret", 403)

    steam64 = str(payload.get("steam64", "")).strip()
    new_points = int(payload.get("points", -1))
    reason = str(payload.get("reason", "api_set_points"))

    if not steam64 or new_points < 0:
        return api_fail("steam64 and points >= 0 are required", 400)

    with db() as conn:
        user = conn.execute("SELECT * FROM users WHERE steam64 = ?", (steam64,)).fetchone()
        if not user:
            return api_fail("unknown steam64", 404)
        account = get_or_create_points_account(conn, user["id"])
        delta = new_points - account["points"]
        add_points_by_user_id(conn, user["id"], delta, reason, "api_set_points")
        account = get_or_create_points_account(conn, user["id"])

    return jsonify({"ok": True, "steam64": steam64, "new_balance": account["points"]})


@app.route("/api/v1/orders", methods=["GET", "POST"])
def api_v1_orders():
    payload = api_payload()
    if not api_auth(payload, "read"):
        return api_fail("bad api_secret", 403)

    status = str(payload.get("status", "")).strip()
    server_key = str(payload.get("server_key", "")).strip()
    steam64 = str(payload.get("steam64", "")).strip()
    limit = min(int(payload.get("limit", 100)), 500)

    query = "SELECT * FROM special_kit_orders WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if server_key:
        query += " AND server_key = ?"
        params.append(server_key)
    if steam64:
        query += " AND steam64 = ?"
        params.append(steam64)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    with db() as conn:
        orders = conn.execute(query, params).fetchall()
    return jsonify({"ok": True, "orders": rows_to_dicts(orders)})


@app.route("/api/v1/orders/pending", methods=["GET", "POST"])
def api_v1_orders_pending():
    payload = api_payload()
    if not api_auth(payload, "read"):
        return api_fail("bad api_secret", 403)

    server_key = str(payload.get("server_key", "")).strip()
    limit = min(int(payload.get("limit", 50)), 200)

    with db() as conn:
        if server_key:
            orders = conn.execute(
                "SELECT * FROM special_kit_orders WHERE status = 'pending' AND server_key = ? ORDER BY id ASC LIMIT ?",
                (server_key, limit),
            ).fetchall()
        else:
            orders = conn.execute(
                "SELECT * FROM special_kit_orders WHERE status = 'pending' ORDER BY id ASC LIMIT ?",
                (limit,),
            ).fetchall()

    return jsonify({"ok": True, "orders": rows_to_dicts(orders)})


@app.route("/api/v1/orders/create", methods=["POST"])
def api_v1_orders_create():
    payload = api_payload()
    if not api_auth(payload, "write"):
        return api_fail("bad api_secret", 403)

    steam64 = str(payload.get("steam64", "")).strip()
    kit_name = str(payload.get("kit_name", "")).strip()
    server_key = str(payload.get("server_key", "")).strip()
    charge_points = bool(payload.get("charge_points", True))

    if not steam64 or not kit_name or not server_key:
        return api_fail("steam64, kit_name, and server_key are required", 400)

    with db() as conn:
        user = conn.execute("SELECT * FROM users WHERE steam64 = ?", (steam64,)).fetchone()
        if not user:
            return api_fail("unknown steam64", 404)

        kit = conn.execute(
            "SELECT * FROM special_kits WHERE kit_name = ? AND server_key = ? AND enabled = 1",
            (kit_name, server_key),
        ).fetchone()
        if not kit:
            return api_fail("unknown or disabled kit for this server_key", 404)

        account = get_or_create_points_account(conn, user["id"])
        if charge_points and account["points"] < kit["cost"]:
            return api_fail("not enough points", 400)

        if charge_points:
            try:
                add_points_by_user_id(conn, user["id"], -kit["cost"], "api_buy_special_kit", kit_name)
            except ValueError as e:
                return api_fail(str(e), 400)

        cur = conn.execute(
            """
            INSERT INTO special_kit_orders
            (user_id, steam64, kit_name, display_name, server_key, cost, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
            """,
            (user["id"], steam64, kit["kit_name"], kit["display_name"], kit["server_key"], kit["cost"], now()),
        )
        order_id = cur.lastrowid

    return jsonify({"ok": True, "order_id": order_id})


@app.route("/api/v1/orders/mark-delivered", methods=["POST"])
def api_v1_orders_mark_delivered():
    payload = api_payload()
    if not api_auth(payload, "write"):
        return api_fail("bad api_secret", 403)

    order_id = int(payload.get("order_id", 0))
    message = str(payload.get("message", "delivered"))
    if order_id <= 0:
        return api_fail("valid order_id is required", 400)

    with db() as conn:
        conn.execute(
            "UPDATE special_kit_orders SET status = 'delivered', delivered_at = ?, worker_message = ? WHERE id = ?",
            (now(), message, order_id),
        )

    return jsonify({"ok": True})


@app.route("/api/v1/orders/mark-failed", methods=["POST"])
def api_v1_orders_mark_failed():
    payload = api_payload()
    if not api_auth(payload, "write"):
        return api_fail("bad api_secret", 403)

    order_id = int(payload.get("order_id", 0))
    message = str(payload.get("message", "failed"))
    if order_id <= 0:
        return api_fail("valid order_id is required", 400)

    with db() as conn:
        conn.execute(
            "UPDATE special_kit_orders SET status = 'failed', worker_message = ? WHERE id = ?",
            (message, order_id),
        )

    return jsonify({"ok": True})


@app.route("/api/v1/user/by-discord/<discord_id>", methods=["GET", "POST"])
def api_v1_user_by_discord(discord_id):
    payload = api_payload()
    if not api_auth(payload, "read"):
        return api_fail("bad api_secret", 403)

    with db() as conn:
        user = conn.execute(
            """
            SELECT users.id, users.username, users.email, users.steam64,
                   users.discord_id, users.discord_username, users.discord_global_name,
                   users.is_admin, users.created_at,
                   COALESCE(points_accounts.points, 0) AS points
            FROM users
            LEFT JOIN points_accounts ON points_accounts.user_id = users.id
            WHERE users.discord_id = ?
            """,
            (discord_id,),
        ).fetchone()

    if not user:
        return api_fail("unknown discord_id", 404)
    return jsonify({"ok": True, "user": row_to_dict(user)})


@app.route("/api/v1/points/discord/<discord_id>", methods=["GET", "POST"])
def api_v1_points_by_discord(discord_id):
    payload = api_payload()
    if not api_auth(payload, "read"):
        return api_fail("bad api_secret", 403)

    with db() as conn:
        user = conn.execute("SELECT * FROM users WHERE discord_id = ?", (discord_id,)).fetchone()
        if not user:
            return api_fail("unknown discord_id", 404)
        points = get_points_by_user_id(conn, user["id"])
        history = conn.execute(
            "SELECT change_amount, reason, reference, created_at FROM points_history WHERE user_id = ? ORDER BY id DESC LIMIT 50",
            (user["id"],),
        ).fetchall()

    return jsonify({
        "ok": True,
        "discord_id": discord_id,
        "steam64": user["steam64"],
        "username": user["username"],
        "points": points,
        "history": rows_to_dicts(history),
    })


@app.route("/api/v1/orders/create-by-discord", methods=["POST"])
def api_v1_orders_create_by_discord():
    payload = api_payload()
    if not api_auth(payload, "write"):
        return api_fail("bad api_secret", 403)

    discord_id = str(payload.get("discord_id", "")).strip()
    kit_name = str(payload.get("kit_name", "")).strip()
    server_key = str(payload.get("server_key", "")).strip()
    charge_points = bool(payload.get("charge_points", True))

    if not discord_id or not kit_name or not server_key:
        return api_fail("discord_id, kit_name, and server_key are required", 400)

    with db() as conn:
        user = conn.execute("SELECT * FROM users WHERE discord_id = ?", (discord_id,)).fetchone()
        if not user:
            return api_fail("unknown discord_id. User must link Discord on the website.", 404)
        if not user["steam64"]:
            return api_fail("user has no Steam account linked. Link Steam on the website first.", 400)

        kit = conn.execute(
            "SELECT * FROM special_kits WHERE kit_name = ? AND server_key = ? AND enabled = 1",
            (kit_name, server_key),
        ).fetchone()
        if not kit:
            return api_fail("unknown or disabled kit for this server_key", 404)

        account = get_or_create_points_account(conn, user["id"])
        if charge_points and account["points"] < kit["cost"]:
            return api_fail("not enough points", 400)

        if charge_points:
            try:
                add_points_by_user_id(conn, user["id"], -kit["cost"], "discord_buy_special_kit", kit_name)
            except ValueError as e:
                return api_fail(str(e), 400)

        cur = conn.execute(
            """
            INSERT INTO special_kit_orders
            (user_id, steam64, kit_name, display_name, server_key, cost, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
            """,
            (user["id"], user["steam64"], kit["kit_name"], kit["display_name"], kit["server_key"], kit["cost"], now()),
        )
        order_id = cur.lastrowid

    return jsonify({"ok": True, "order_id": order_id})


if __name__ == "__main__":
    init_db()
    print("")
    print("==============================================")
    print(" DayZ Kits & Points Python Website")
    print(f" Running on: http://0.0.0.0:{DEFAULT_PORT}")
    print(" Default admin:")
    print(f"   username: {ADMIN_USERNAME}")
    print("   password: set DZKP_ADMIN_PASSWORD")
    print("==============================================")
    print("")
    app.run(host="0.0.0.0", port=DEFAULT_PORT)
