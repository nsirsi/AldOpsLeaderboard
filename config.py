import os
from dotenv import load_dotenv

load_dotenv()

# Discord Bot Configuration
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
BOT_PREFIX = '!'

# Database URL (Postgres)
DATABASE_URL = os.getenv('DATABASE_URL')  # e.g., postgres://USER:PASSWORD@HOST:PORT/DB

# Database Configuration (SQLite fallback path when DATABASE_URL is not set)
DATABASE_PATH = 'wordle_leaderboard.db'

# Leaderboard Configuration
SCORE_MULTIPLIER = 1  # Base score multiplier
MAX_GUESSES = 6  # Maximum guesses in Wordle
FAILURE_SCORE = 1  # Score for failed attempts (X/6)
NO_ATTEMPT_SCORE = 0  # Score for no attempt

# WordleBot Configuration
WORDBOT_USERNAME = 'Wordle'  # The username of the WordleBot
WORDBOT_APP_INDICATOR = 'APP'  # Indicator for verified apps

# Auto-post Configuration
AUTO_POST_ENABLED = True  # Enable/disable weekly auto-post
AUTO_POST_DAY = 0  # Monday (0=Monday, 1=Tuesday, etc.)
AUTO_POST_HOUR = 7  # 12:01 AM PT = 7:01 AM UTC (during PST)
AUTO_POST_MINUTE = 1  # 1 minute past the hour

# Message Patterns
RESULTS_HEADER_PATTERN = r"Here are yesterday's results:"
WORDLE_NUMBER_PATTERN = r"Wordle No\. (\d+)"
SCORE_PATTERN = r"(\d+)/6"
USER_MENTION_PATTERN = r"<@!?(\d+)>"
