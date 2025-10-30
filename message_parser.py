import re
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
from discord import Message, User, Member

logger = logging.getLogger(__name__)

class WordleMessageParser:
    def __init__(self):
        # Patterns based on the WordleBot message format
        # Be tolerant of curly quotes, extra spaces, and punctuation variants
        self.results_header_pattern = re.compile(r"Here are yesterday[’']s results:?", re.IGNORECASE)
        self.wordle_number_pattern = re.compile(r"Wordle\s+No[\.:\s]+(\d+)", re.IGNORECASE)
        self.score_pattern = re.compile(r"(\d+)/6")
        self.user_mention_pattern = re.compile(r"<@!?(\d+)>")
        
    def _message_text(self, message: Message) -> str:
        """Aggregate message content and embed text for parsing."""
        parts = [message.content or ""]
        try:
            for emb in getattr(message, 'embeds', []) or []:
                if getattr(emb, 'title', None):
                    parts.append(str(emb.title))
                if getattr(emb, 'description', None):
                    parts.append(str(emb.description))
                # Include author and footer text if present
                author = getattr(emb, 'author', None)
                if author and getattr(author, 'name', None):
                    parts.append(str(author.name))
                footer = getattr(emb, 'footer', None)
                if footer and getattr(footer, 'text', None):
                    parts.append(str(footer.text))
                # Include simple fields as well
                for field in getattr(emb, 'fields', []) or []:
                    if getattr(field, 'name', None):
                        parts.append(str(field.name))
                    if getattr(field, 'value', None):
                        parts.append(str(field.value))
        except Exception:
            pass
        return "\n".join([p for p in parts if p])

    def is_wordlebot_message(self, message: Message) -> bool:
        """Heuristically determine if this message contains WordleBot results."""
        text = self._message_text(message)
        if not text:
            return False
        has_header = self.results_header_pattern.search(text) is not None
        has_wordle_no = self.wordle_number_pattern.search(text) is not None
        # Prefer textual patterns over author identity to handle embeds/webhooks
        if has_header and has_wordle_no:
            return True
        # Fallback: author name contains Wordle and there is a score pattern
        try:
            if (getattr(message.author, 'bot', False) and 'wordle' in message.author.name.lower() and self.score_pattern.search(text)):
                return True
        except Exception:
            pass
        return False
    
    def extract_wordle_number(self, content: str) -> Optional[int]:
        """Extract Wordle number from message content"""
        match = self.wordle_number_pattern.search(content)
        if match:
            return int(match.group(1))
        return None
    
    def parse_player_results(self, message: Message) -> List[Dict]:
        """Parse individual player results from WordleBot message"""
        results = []
        content = self._message_text(message)
        
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
            text = self._message_text(message)
            wordle_number = self.extract_wordle_number(text)
            
            # Parse player results
            player_results = self.parse_player_results(message)
            if not player_results:
                logger.warning(f"No player results found in message: {message.id}")
                return None
            
            # Determine game date based on when this message was posted
            # WordleBot posts "yesterday's results", so subtract one day from message time
            try:
                msg_date = message.created_at.date()
            except Exception:
                msg_date = date.today()
            game_date = msg_date - timedelta(days=1)
            
            # If Wordle number wasn't in the embed/text, derive from date (Wordle #0 = 2021-06-19)
            if not wordle_number:
                try:
                    epoch = date(2021, 6, 19)
                    derived = (game_date - epoch).days
                    if derived >= 0:
                        wordle_number = derived
                except Exception:
                    pass
            if not wordle_number:
                logger.warning(f"Could not extract or derive Wordle number from message: {message.id}")
                return None
            
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
