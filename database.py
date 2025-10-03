import sqlite3
import asyncio
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class WordleDatabase:
    def __init__(self, db_path: str = 'wordle_leaderboard.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                display_name TEXT,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Games table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                wordle_number INTEGER NOT NULL,
                game_date DATE NOT NULL,
                guesses INTEGER NOT NULL,
                score INTEGER NOT NULL,
                success BOOLEAN NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Leaderboard cache table for performance
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS leaderboard_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                period_type TEXT NOT NULL,  -- 'weekly', 'monthly', 'alltime'
                period_start DATE NOT NULL,
                total_score INTEGER NOT NULL,
                games_played INTEGER NOT NULL,
                average_score REAL NOT NULL,
                rank INTEGER,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                UNIQUE(user_id, period_type, period_start)
            )
        ''')
        
        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_games_user_date ON games(user_id, game_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_games_date ON games(game_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_leaderboard_period ON leaderboard_cache(period_type, period_start)')
        
        conn.commit()
        conn.close()
    
    def add_or_update_user(self, user_id: int, username: str, display_name: str = None):
        """Add a new user or update existing user info"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO users (user_id, username, display_name)
            VALUES (?, ?, ?)
        ''', (user_id, username, display_name))
        
        conn.commit()
        conn.close()
    
    def add_game_result(self, user_id: int, wordle_number: int, game_date: date, 
                       guesses: int, success: bool):
        """Add a game result to the database"""
        # Calculate score: guesses + 1 for success, 1 for failure, 0 for no attempt
        score = guesses + 1 if success else 1
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if game already exists (prevent duplicates)
        cursor.execute('''
            SELECT id FROM games 
            WHERE user_id = ? AND wordle_number = ? AND game_date = ?
        ''', (user_id, wordle_number, game_date))
        
        if cursor.fetchone():
            conn.close()
            return False  # Game already exists
        
        cursor.execute('''
            INSERT INTO games (user_id, wordle_number, game_date, guesses, score, success)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, wordle_number, game_date, guesses, score, success))
        
        conn.commit()
        conn.close()
        return True
    
    def get_user_stats(self, user_id: int, period_type: str = 'alltime') -> Dict:
        """Get user statistics for a specific period"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Calculate period boundaries
        today = date.today()
        if period_type == 'weekly':
            period_start = today.replace(day=today.day - today.weekday())
        elif period_type == 'monthly':
            period_start = today.replace(day=1)
        else:  # alltime
            period_start = date(2020, 1, 1)  # Wordle started in 2021, but safe date
        
        cursor.execute('''
            SELECT 
                COUNT(*) as games_played,
                SUM(score) as total_score,
                AVG(score) as average_score,
                COUNT(CASE WHEN success = 1 THEN 1 END) as successful_games,
                MIN(game_date) as first_game,
                MAX(game_date) as last_game
            FROM games 
            WHERE user_id = ? AND game_date >= ?
        ''', (user_id, period_start))
        
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0] > 0:
            return {
                'games_played': result[0],
                'total_score': result[1] or 0,
                'average_score': round(result[2] or 0, 2),
                'successful_games': result[3] or 0,
                'first_game': result[4],
                'last_game': result[5]
            }
        return {
            'games_played': 0,
            'total_score': 0,
            'average_score': 0,
            'successful_games': 0,
            'first_game': None,
            'last_game': None
        }
    
    def get_leaderboard(self, period_type: str = 'alltime', limit: int = 10) -> List[Dict]:
        """Get leaderboard for a specific period"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Calculate period boundaries
        today = date.today()
        if period_type == 'weekly':
            period_start = today.replace(day=today.day - today.weekday())
        elif period_type == 'monthly':
            period_start = today.replace(day=1)
        else:  # alltime
            period_start = date(2020, 1, 1)
        
        cursor.execute('''
            SELECT 
                u.user_id,
                u.username,
                u.display_name,
                COUNT(g.id) as games_played,
                SUM(g.score) as total_score,
                AVG(g.score) as average_score,
                COUNT(CASE WHEN g.success = 1 THEN 1 END) as successful_games
            FROM users u
            LEFT JOIN games g ON u.user_id = g.user_id AND g.game_date >= ?
            GROUP BY u.user_id, u.username, u.display_name
            HAVING games_played > 0
            ORDER BY total_score DESC, average_score DESC
            LIMIT ?
        ''', (period_start, limit))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'user_id': row[0],
                'username': row[1],
                'display_name': row[2],
                'games_played': row[3],
                'total_score': row[4] or 0,
                'average_score': round(row[5] or 0, 2),
                'successful_games': row[6] or 0
            })
        
        conn.close()
        return results
    
    def get_user_rank(self, user_id: int, period_type: str = 'alltime') -> int:
        """Get user's rank in the leaderboard"""
        leaderboard = self.get_leaderboard(period_type, limit=1000)
        for i, entry in enumerate(leaderboard, 1):
            if entry['user_id'] == user_id:
                return i
        return -1  # User not found in leaderboard
