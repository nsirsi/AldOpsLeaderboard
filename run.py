#!/usr/bin/env python3
"""
Wordle Leaderboard Bot - Main Entry Point
Run this file to start the bot
"""

import os
import sys
import logging
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Import and run the bot
from bot import bot

if __name__ == "__main__":
    # Check for required environment variables
    if not os.getenv('DISCORD_TOKEN'):
        print("❌ Error: DISCORD_TOKEN not found in environment variables!")
        print("Please create a .env file with your Discord bot token.")
        print("Example: DISCORD_TOKEN=your_bot_token_here")
        sys.exit(1)
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('bot.log')
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("🚀 Starting Wordle Leaderboard Bot...")
    
    try:
        # Run the bot
        bot.run(os.getenv('DISCORD_TOKEN'))
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"💥 Bot crashed: {e}")
        sys.exit(1)
