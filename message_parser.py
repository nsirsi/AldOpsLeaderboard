import re
import logging
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple
from discord import Message, User, Member

logger = logging.getLogger(__name__)

class WordleMessageParser:
    def __init__(self):
        # Patterns based on the WordleBot message format
        self.results_header_pattern = re.compile(r"Here are yesterday's results:", re.IGNORECASE)
        self.wordle_number_pattern = re.compile(r"Wordle No\. (\d+)", re.IGNORECASE)
        self.score_pattern = re.compile(r"(\d+)/6")
        self.user_mention_pattern = re.compile(r"<@!?(\d+)>")
        
    def is_wordlebot_message(self, message: Message) -> bool:
        """Check if message is from WordleBot and contains results"""
        # Check if message is from WordleBot (verified app)
        if not (message.author.name == 'Wordle' and hasattr(message.author, 'verified') and message.author.verified):
            return False
        
        # Check if message contains results header
        return self.results_header_pattern.search(message.content) is not None
    
    def extract_wordle_number(self, content: str) -> Optional[int]:
        """Extract Wordle number from message content"""
        match = self.wordle_number_pattern.search(content)
        if match:
            return int(match.group(1))
        return None
    
    def parse_player_results(self, message: Message) -> List[Dict]:
        """Parse individual player results from WordleBot message"""
        results = []
        content = message.content
        
        # Split content into lines and process each line
        lines = content.split('\n')
        
        for line in lines:
            # Look for user mentions in the line
            user_mentions = self.user_mention_pattern.findall(line)
            
            if user_mentions:
                # Extract score from the line
                score_match = self.score_pattern.search(line)
                if score_match:
                    guesses = int(score_match.group(1))
                    user_id = int(user_mentions[0])  # Take first mention
                    
                    # Determine if it's a successful game (guesses <= 6)
                    success = guesses <= 6
                    
                    results.append({
                        'user_id': user_id,
                        'guesses': guesses,
                        'success': success,
                        'raw_line': line.strip()
                    })
        
        return results
    
    def parse_wordlebot_message(self, message: Message) -> Optional[Dict]:
        """Parse a complete WordleBot message and extract all relevant data"""
        if not self.is_wordlebot_message(message):
            return None
        
        try:
            # Extract Wordle number
            wordle_number = self.extract_wordle_number(message.content)
            if not wordle_number:
                logger.warning(f"Could not extract Wordle number from message: {message.id}")
                return None
            
            # Parse player results
            player_results = self.parse_player_results(message)
            if not player_results:
                logger.warning(f"No player results found in message: {message.id}")
                return None
            
            # Determine game date (yesterday's results)
            game_date = date.today()
            
            return {
                'wordle_number': wordle_number,
                'game_date': game_date,
                'player_results': player_results,
                'message_id': message.id,
                'channel_id': message.channel.id,
                'guild_id': message.guild.id if message.guild else None
            }
            
        except Exception as e:
            logger.error(f"Error parsing WordleBot message {message.id}: {e}")
            return None
    
    def get_user_from_mention(self, message: Message, user_id: int) -> Optional[User]:
        """Get User object from user ID, checking both guild members and global users"""
        if message.guild:
            # Try to get member from guild first
            member = message.guild.get_member(user_id)
            if member:
                return member
        
        # Fallback to global user lookup
        return message._state.get_user(user_id)
    
    def validate_parsed_data(self, parsed_data: Dict) -> bool:
        """Validate that parsed data contains all required fields"""
        required_fields = ['wordle_number', 'game_date', 'player_results']
        
        for field in required_fields:
            if field not in parsed_data:
                logger.error(f"Missing required field '{field}' in parsed data")
                return False
        
        if not isinstance(parsed_data['player_results'], list):
            logger.error("Player results must be a list")
            return False
        
        for result in parsed_data['player_results']:
            required_result_fields = ['user_id', 'guesses', 'success']
            for field in required_result_fields:
                if field not in result:
                    logger.error(f"Missing required field '{field}' in player result")
                    return False
        
        return True
