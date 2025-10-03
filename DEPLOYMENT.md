# Discord WordleBot Leaderboard - Deployment Guide

This guide will walk you through setting up and deploying the Discord WordleBot leaderboard bot.

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Discord account
- Discord server with WordleBot installed

### 🐍 Virtual Environment Quick Reference
```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate

# Deactivate (when done)
deactivate
```

### 1. Discord Bot Setup

#### Step 1: Create Discord Application
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **"New Application"**
3. Enter a name (e.g., "Wordle Leaderboard Bot")
4. Click **"Create"**

#### Step 2: Create Bot
1. In your application, go to **"Bot"** section
2. Click **"Add Bot"**
3. Copy the **Bot Token** (keep this secret!)
4. Under **"Privileged Gateway Intents"**, enable:
   - ✅ **Message Content Intent**
   - ✅ **Server Members Intent**

#### Step 3: Set Bot Permissions
1. Go to **"OAuth2"** → **"URL Generator"**
2. Select scopes:
   - ✅ **bot**
   - ✅ **applications.commands**
3. Select permissions:
   - ✅ **Send Messages**
   - ✅ **Use Slash Commands**
   - ✅ **Read Message History**
   - ✅ **Read Messages**
   - ✅ **Embed Links**
   - ✅ **Attach Files**
4. Copy the generated URL and open it in your browser
5. Select your server and authorize the bot

### 2. Local Development Setup

#### Step 1: Create Virtual Environment (Recommended)
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Verify you're in the virtual environment
# Your prompt should show (venv) at the beginning
```

#### Step 2: Install Dependencies
```bash
# Install Python dependencies in virtual environment
pip install -r requirements.txt

# Verify installation
pip list
```

#### Step 3: Environment Configuration
1. Create a `.env` file in the project root:
```bash
# Copy the example file
cp env_example.txt .env
```

2. Edit `.env` and add your bot token:
```env
DISCORD_TOKEN=your_discord_token_here
DATABASE_PATH=wordle_leaderboard.db
```

#### Step 4: Test the Bot
```bash
# Run the bot (make sure virtual environment is activated)
python run.py
```

You should see:
```
INFO:__main__:Bot has connected to Discord!
INFO:__main__:Bot is in X guilds
INFO:__main__:Synced X slash commands
INFO:__main__:Started weekly leaderboard auto-post task
```

### 3. Production Deployment

#### Option A: VPS/Cloud Server (Recommended)

**Using a VPS (DigitalOcean, Linode, AWS EC2, etc.):**

1. **Set up server:**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and pip
sudo apt install python3 python3-pip python3-venv -y

# Create project directory
mkdir -p /opt/wordle-bot
cd /opt/wordle-bot
```

2. **Upload your code:**
```bash
# Upload files to server (use scp, rsync, or git)
scp -r . user@your-server:/opt/wordle-bot/
```

3. **Set up virtual environment:**
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

4. **Configure environment:**
```bash
# Create .env file
nano .env
# Add your DISCORD_TOKEN
```

5. **Set up systemd service:**
```bash
sudo nano /etc/systemd/system/wordle-bot.service
```

Add this content:
```ini
[Unit]
Description=Wordle Leaderboard Bot
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/opt/wordle-bot
Environment=PATH=/opt/wordle-bot/venv/bin
ExecStart=/opt/wordle-bot/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

6. **Start the service:**
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable auto-start
sudo systemctl enable wordle-bot

# Start the bot
sudo systemctl start wordle-bot

# Check status
sudo systemctl status wordle-bot

# View logs
sudo journalctl -u wordle-bot -f
```

#### Option B: Docker Deployment

1. **Create Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
```

2. **Create docker-compose.yml:**
```yaml
version: '3.8'
services:
  wordle-bot:
    build: .
    environment:
      - DISCORD_TOKEN=${DISCORD_TOKEN}
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

3. **Deploy:**
```bash
# Create .env file with your token
echo "DISCORD_TOKEN=your_token_here" > .env

# Run with docker-compose
docker-compose up -d

# View logs
docker-compose logs -f
```

#### Option C: Cloud Platforms

**Heroku:**
1. Create `Procfile`:
```
worker: python bot.py
```
2. Deploy via Heroku CLI or GitHub integration

**Railway:**
1. Connect GitHub repository
2. Set environment variables
3. Deploy automatically

**Replit:**
1. Import GitHub repository
2. Add environment variables in Secrets
3. Run the bot

### 4. Configuration

#### Environment Variables
```env
# Required
DISCORD_TOKEN=your_bot_token_here

# Optional
DATABASE_PATH=wordle_leaderboard.db
AUTO_POST_ENABLED=true
AUTO_POST_DAY=0
AUTO_POST_HOUR=7
AUTO_POST_MINUTE=1
```

#### Bot Permissions Required
- **Send Messages** - Post leaderboards
- **Use Slash Commands** - Interactive commands
- **Read Message History** - Process WordleBot messages
- **Read Messages** - Monitor channels
- **Embed Links** - Rich leaderboard displays
- **Attach Files** - Future features

### 5. Testing

#### Test Commands
1. **Invite bot to test server**
2. **Test slash commands:**
   - `/leaderboard` - Should show interactive leaderboard
   - `/mystats` - Should show your stats
   - `/help` - Should show help menu

3. **Test WordleBot integration:**
   - Post a WordleBot message in a channel
   - Bot should automatically process it
   - Check database for new entries

4. **Test auto-post:**
   - Use `/post` command to manually trigger
   - Check that interactive buttons work

#### Troubleshooting

**Common Issues:**

1. **Bot not responding:**
   - Check bot token in `.env`
   - Verify bot permissions
   - Check bot is online in Discord

2. **Slash commands not working:**
   - Wait 1 hour for global sync
   - Use `/sync` command in server
   - Check bot has `applications.commands` scope

3. **Database errors:**
   - Check file permissions
   - Ensure database directory exists
   - Verify SQLite is working

4. **Auto-post not working:**
   - Check timezone settings
   - Verify `AUTO_POST_ENABLED=true`
   - Check bot has channel permissions

### 6. Monitoring

#### Log Files
```bash
# View systemd logs
sudo journalctl -u wordle-bot -f

# View Docker logs
docker-compose logs -f wordle-bot
```

#### Health Checks
- Bot online status
- Database connectivity
- Message processing rate
- Error rates

### 7. Maintenance

#### Regular Tasks
- **Monitor logs** for errors
- **Backup database** regularly
- **Update dependencies** monthly
- **Check bot permissions** after server changes

#### Database Backup
```bash
# Backup SQLite database
cp wordle_leaderboard.db backup_$(date +%Y%m%d).db

# Or with compression
tar -czf backup_$(date +%Y%m%d).tar.gz wordle_leaderboard.db
```

#### Updates
```bash
# Pull latest code
git pull origin main

# Update dependencies
pip install -r requirements.txt

# Restart bot
sudo systemctl restart wordle-bot
```

## 🎯 Success Checklist

- [ ] Bot token configured
- [ ] Bot invited to server with proper permissions
- [ ] Slash commands working
- [ ] WordleBot message processing working
- [ ] Interactive leaderboard buttons working
- [ ] Auto-post scheduled correctly
- [ ] Database storing data
- [ ] Bot running 24/7

## 📞 Support

If you encounter issues:
1. Check the logs for error messages
2. Verify all permissions are correct
3. Test in a small server first
4. Check Discord API status

The bot should now be fully functional and ready to track Wordle leaderboards!
