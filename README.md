# Discord Wordle Leaderboard Bot

A Discord bot that automatically processes WordleBot messages and maintains leaderboards for weekly, monthly, and all-time periods.

## Features

- **Automatic Processing**: Monitors channels for WordleBot messages and extracts game results
- **Leaderboards**: Weekly, monthly, and all-time leaderboards with rankings
- **Personal Statistics**: Individual user statistics and performance tracking
- **Score Calculation**: Based on number of guesses + 1 (X = 1, no attempt = 0)
- **Slash Commands**: Modern Discord slash command interface

## Setup

### 1. Prerequisites

- Python 3.8 or higher
- Discord Bot Token
- Discord Server with WordleBot installed

### 2. Installation

1. Clone or download this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file with your Discord bot token (and Postgres URL if using Supabase):
   ```
   DISCORD_TOKEN=your_discord_bot_token_here
  # For Supabase/Postgres
  # DATABASE_URL=postgres://USER:PASSWORD@HOST:PORT/DB
   ```

### 3. Discord Bot Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to "Bot" section and create a bot
4. Copy the bot token and add it to your `.env` file
5. Enable the following bot permissions:
   - Send Messages
   - Use Slash Commands
   - Read Message History
   - Read Messages

### 4. Invite Bot to Server

Use this URL (replace YOUR_CLIENT_ID with your bot's client ID):
```
https://discord.com/api/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=2048&scope=bot%20applications.commands
```

## Usage

### Commands

- `/leaderboard [period]` - View leaderboards (weekly, monthly, alltime)
- `/mystats [period]` - View your personal statistics
- `/help` - Show available commands

### Automatic Processing

The bot automatically:
- Monitors channels for WordleBot messages
- Extracts game results and player scores
- Updates the database with new game data
- Maintains leaderboards in real-time

## Scoring System

- **Successful Games**: Number of guesses + 1
- **Failed Games (X/6)**: 1 point
- **No Attempt**: 0 points

## Database

The bot supports both SQLite (local) and PostgreSQL (Supabase) via `DATABASE_URL`.

- If `DATABASE_URL` is set, Postgres is used.
- Otherwise, it falls back to the local `wordle_leaderboard.db` SQLite file.

The database stores:
- User information
- Game results and scores
- Leaderboard cache for performance

## Configuration

Edit `config.py` to customize:
- Database path
- Score calculations
- Message patterns
- Bot settings

## Troubleshooting

### Common Issues

1. **Bot not responding**: Check bot permissions and token
2. **No leaderboard data**: Ensure WordleBot is posting in monitored channels
3. **Database errors**: Check file permissions for database file

### Logs

The bot logs important events and errors. Check console output for debugging information.

## Development

### Project Structure

```
├── bot.py              # Main bot file
├── database.py         # Database operations (SQLite + Postgres via env)
├── migrations/         # SQL migrations for Postgres
├── message_parser.py   # WordleBot message parsing
├── config.py          # Configuration
├── requirements.txt    # Dependencies
└── README.md          # This file
```

### Adding Features

1. **New Commands**: Add to `bot.py` in the `setup_hook` method
2. **Database Changes**: Modify `database.py` and run database migrations
3. **Message Parsing**: Update `message_parser.py` for new message formats

## License

This project is open source and available under the MIT License.
