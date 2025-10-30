## GCP VM + Supabase Postgres Deployment Guide

This guide sets up the Discord Wordle Leaderboard Bot to run 24/7 for $0 using:
- Compute: Google Cloud Platform Always Free e2-micro VM
- Database: Supabase (Postgres) Free tier

Prereqs:
- GCP account with Always Free eligible project
- Supabase account and organization
- Discord Bot with token and permissions

---

### 1) Create Supabase Postgres
1. In Supabase, create a new project (Free tier).
2. In Project Settings → Database, find the connection details:
   - Host, Port, Database, User, Password
   - Full connection string (e.g., `postgres://USER:PASSWORD@HOST:PORT/DB`)
3. Create schema tables (match current SQLite schema) using SQL editor:

```sql
-- users table
CREATE TABLE IF NOT EXISTS users (
  user_id BIGINT PRIMARY KEY,
  username TEXT NOT NULL,
  display_name TEXT,
  first_seen TIMESTAMPTZ DEFAULT NOW()
);

-- games table
CREATE TABLE IF NOT EXISTS games (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(user_id),
  wordle_number INTEGER NOT NULL,
  game_date DATE NOT NULL,
  guesses INTEGER NOT NULL,
  score INTEGER NOT NULL,
  success BOOLEAN NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, wordle_number, game_date)
);

-- indexes
CREATE INDEX IF NOT EXISTS idx_games_user_date ON games(user_id, game_date);
CREATE INDEX IF NOT EXISTS idx_games_date ON games(game_date);
```

Keep the database URL safe; you’ll use it as `DATABASE_URL` on the VM.

---

### 2) Create GCP e2-micro VM (Always Free)
1. In Google Cloud Console → Compute Engine → VM instances → Create instance.
2. Machine: e2-micro; Region/Zone eligible for Always Free (e.g., us-west1, us-central1; check current policy).
3. Boot disk: Ubuntu LTS (e.g., 22.04) minimal is fine.
4. Firewall: no public ports required (the bot uses outbound only). You can leave HTTP/HTTPS unchecked.
5. Create and SSH into the VM.

---

### 3) Prepare the VM
Run the following inside the VM:

```bash
sudo apt update && sudo apt install -y python3-pip python3-venv git

# Create app directory
mkdir -p ~/apps/wordle-bot && cd ~/apps/wordle-bot

# Clone repo
git clone https://github.com/<your-username>/<your-repo>.git .

# Python env
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

### 4) Configure environment
Create a `.env` file in the project root with:

```env
DISCORD_TOKEN=your_discord_bot_token

# Postgres (Supabase)
DATABASE_URL=postgres://USER:PASSWORD@HOST:PORT/DB

# Optional: override defaults
# AUTO_POST_ENABLED=True
```

Note: The code will be adapted to read `DATABASE_URL` and use Postgres. Until that change lands, it uses SQLite; do not run the bot before the code update.

---

### 5) Run as a systemd service
Create a service so the bot runs on boot and restarts on failure.

```bash
sudo tee /etc/systemd/system/wordle-bot.service >/dev/null << 'EOF'
[Unit]
Description=Wordle Leaderboard Discord Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=%i
WorkingDirectory=/home/%i/apps/wordle-bot
Environment=PYTHONUNBUFFERED=1
EnvironmentFile=/home/%i/apps/wordle-bot/.env
ExecStart=/home/%i/apps/wordle-bot/.venv/bin/python run.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Replace %i with your username
sudo sed -i "s/%i/$USER/g" /etc/systemd/system/wordle-bot.service

sudo systemctl daemon-reload
sudo systemctl enable wordle-bot
sudo systemctl start wordle-bot
```

Check logs:

```bash
journalctl -u wordle-bot -f
```

---

### 6) Backfill (history import)
Once the code is updated to support a backfill command, you’ll be able to run:

- Slash command (preferred): `/backfill days:<N>` per channel where WordleBot posts
- Or an admin-only CLI/script triggered on the VM

Ensure the bot has “Read Message History” in target channels. Backfill will:
- Scan recent messages for WordleBot posts
- Parse results and add to Postgres (skipping duplicates via unique constraint)

Rate limits: large backfills should be bounded (e.g., 7–30 days at a time).

---

### 7) Operations
- Update code: `cd ~/apps/wordle-bot && git pull && source .venv/bin/activate && pip install -r requirements.txt && sudo systemctl restart wordle-bot`
- Restart: `sudo systemctl restart wordle-bot`
- Status: `systemctl status wordle-bot`
- Logs: `journalctl -u wordle-bot -f`
- Backups: Supabase handles automated backups on paid tiers; export manually on Free if needed.

---

### 8) Security notes
- Keep `.env` readable only by your user: `chmod 600 .env`
- Rotate `DISCORD_TOKEN` and DB password if leaked.
- The VM doesn’t need inbound ports for this bot; keep it closed to the internet.

---

### 9) Next steps in this repo
- Replace SQLite with Postgres (read `DATABASE_URL`) in the code
- Add `/backfill` command to ingest recent history
- Update README and docs to reflect new deployment path



