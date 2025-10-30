import os
import sqlite3
from datetime import date, timedelta
from typing import List, Dict
import logging
from config import DATABASE_URL

try:
    import psycopg
except Exception:  # psycopg is optional for local sqlite
    psycopg = None

logger = logging.getLogger(__name__)

class WordleDatabase:
    def __init__(self, db_path: str = 'wordle_leaderboard.db'):
        self.db_path = db_path
        self.use_postgres = bool(DATABASE_URL)
        if self.use_postgres and not psycopg:
            logger.warning("DATABASE_URL is set but psycopg is not installed; falling back to SQLite")
            self.use_postgres = False
        self.init_database()

    def _conn(self):
        if self.use_postgres:
            return psycopg.connect(DATABASE_URL)
        return sqlite3.connect(self.db_path)

    def _q(self, query: str) -> str:
        """Adapt placeholder style to the active backend."""
        if self.use_postgres:
            return query.replace('?', '%s')
        return query
    
    def init_database(self):
        """Initialize the database with required tables"""
        if self.use_postgres:
            with self._conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        CREATE TABLE IF NOT EXISTS users (
                          user_id BIGINT PRIMARY KEY,
                          username TEXT NOT NULL,
                          display_name TEXT,
                          first_seen TIMESTAMP DEFAULT NOW()
                        )
                        """
                    )
                    cursor.execute(
                        """
                        CREATE TABLE IF NOT EXISTS games (
                          id BIGSERIAL PRIMARY KEY,
                          user_id BIGINT NOT NULL REFERENCES users(user_id),
                          wordle_number INTEGER NOT NULL,
                          game_date DATE NOT NULL,
                          guesses INTEGER NOT NULL,
                          score INTEGER NOT NULL,
                          success BOOLEAN NOT NULL,
                          created_at TIMESTAMP DEFAULT NOW(),
                          UNIQUE(user_id, wordle_number, game_date)
                        )
                        """
                    )
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_games_user_date ON games(user_id, game_date)")
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_games_date ON games(game_date)")
        else:
            conn = self._conn()
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT NOT NULL,
                    display_name TEXT,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
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
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    UNIQUE(user_id, wordle_number, game_date)
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_games_user_date ON games(user_id, game_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_games_date ON games(game_date)')
            conn.commit()
            conn.close()
    
    def add_or_update_user(self, user_id: int, username: str, display_name: str = None):
        """Add a new user or update existing user info"""
        query_sqlite = 'INSERT OR REPLACE INTO users (user_id, username, display_name) VALUES (?, ?, ?)'
        query_pg = 'INSERT INTO users (user_id, username, display_name) VALUES (%s, %s, %s) ON CONFLICT (user_id) DO UPDATE SET username = EXCLUDED.username, display_name = EXCLUDED.display_name'
        with self._conn() as conn:
            with conn.cursor() as cursor:
                if self.use_postgres:
                    cursor.execute(query_pg, (user_id, username, display_name))
                else:
                    cursor.execute(query_sqlite, (user_id, username, display_name))
    
    def add_game_result(self, user_id: int, wordle_number: int, game_date: date, 
                        guesses: int, success: bool):
        """Add a game result to the database"""
        # Calculate score per spec:
        # success: score = 8 - guesses (guesses 1..6 => scores 7..2)
        # failure (X): score = 1
        # no attempt: not inserted here; would be 0 if tracked
        score = (8 - guesses) if success else 1
        with self._conn() as conn:
            with conn.cursor() as cursor:
                # Check duplicate
                cursor.execute(
                    self._q('SELECT id FROM games WHERE user_id = ? AND wordle_number = ? AND game_date = ?'),
                    (user_id, wordle_number, game_date)
                )
                if cursor.fetchone():
                    return False
                cursor.execute(
                    self._q('INSERT INTO games (user_id, wordle_number, game_date, guesses, score, success) VALUES (?, ?, ?, ?, ?, ?)'),
                    (user_id, wordle_number, game_date, guesses, score, success)
                )
                return True
    
    def get_user_stats(self, user_id: int, period_type: str = 'alltime') -> Dict:
        """Get user statistics for a specific period"""
        conn = self._conn()
        cursor = conn.cursor()
        # Calculate period boundaries
        today = date.today()
        if period_type == 'weekly':
            # Go back to Monday of current week (weekday() returns 0=Monday, 6=Sunday)
            period_start = today - timedelta(days=today.weekday())
        elif period_type == 'monthly':
            period_start = today.replace(day=1)
        else:  # alltime
            period_start = date(2020, 1, 1)  # Wordle started in 2021, but safe date
        query = self._q('''
            SELECT 
                COUNT(*) as games_played,
                SUM(score) as total_score,
                AVG(score) as average_score,
                COUNT(CASE WHEN success THEN 1 END) as successful_games,
                MIN(game_date) as first_game,
                MAX(game_date) as last_game
            FROM games 
            WHERE user_id = ? AND game_date >= ?
        ''')
        cursor.execute(query, (user_id, period_start))
        
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
        conn = self._conn()
        cursor = conn.cursor()
        
        # Calculate period boundaries
        today = date.today()
        if period_type == 'weekly':
            # Go back to Monday of current week (weekday() returns 0=Monday, 6=Sunday)
            period_start = today - timedelta(days=today.weekday())
        elif period_type == 'monthly':
            period_start = today.replace(day=1)
        else:  # alltime
            period_start = date(2020, 1, 1)
        
        query = self._q('''
            SELECT 
                u.user_id,
                u.username,
                u.display_name,
                COUNT(g.id) as games_played,
                SUM(g.score) as total_score,
                AVG(g.score) as average_score,
                COUNT(CASE WHEN g.success THEN 1 END) as successful_games
            FROM users u
            LEFT JOIN games g ON u.user_id = g.user_id AND g.game_date >= ?
            GROUP BY u.user_id, u.username, u.display_name
            HAVING COUNT(g.id) > 0
            ORDER BY total_score DESC, average_score DESC
            LIMIT ?
        ''')
        cursor.execute(query, (period_start, limit))
        
        results = []
        for row in cursor.fetchall():
            user_id = row[0]
            streak_info = self.get_user_streak(user_id)
            results.append({
                'user_id': user_id,
                'username': row[1],
                'display_name': row[2],
                'games_played': row[3],
                'total_score': row[4] or 0,
                'average_score': round(row[5] or 0, 2),
                'successful_games': row[6] or 0,
                'current_streak': streak_info['current_streak'],
                'longest_streak': streak_info['longest_streak']
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
    
    def get_user_streak(self, user_id: int) -> Dict:
        """Get user's current and longest streak"""
        conn = self._conn()
        cursor = conn.cursor()
        
        # Get all unique game dates for this user, ordered by date descending
        query = self._q('''
            SELECT DISTINCT game_date 
            FROM games 
            WHERE user_id = ? 
            ORDER BY game_date DESC
        ''')
        cursor.execute(query, (user_id,))
        dates = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        if not dates:
            return {'current_streak': 0, 'longest_streak': 0}
        
        # Calculate current streak (count consecutive days backwards from most recent game date)
        current_streak = 0
        unique_dates = sorted(set(dates), reverse=True)  # Most recent first
        
        if unique_dates:
            expected_date = unique_dates[0]  # Most recent game date
            
            for game_date in unique_dates:
                if game_date == expected_date:
                    current_streak += 1
                    expected_date = game_date - timedelta(days=1)
                else:
                    # Gap found, streak ends
                    break
        
        # Calculate longest streak (find longest consecutive sequence)
        longest_streak = 0
        if dates:
            unique_dates = sorted(set(dates))
            if unique_dates:
                current_run = 1
                longest_streak = 1
                
                for i in range(1, len(unique_dates)):
                    prev_date = unique_dates[i - 1]
                    curr_date = unique_dates[i]
                    
                    if (curr_date - prev_date).days == 1:
                        # Consecutive day
                        current_run += 1
                        longest_streak = max(longest_streak, current_run)
                    else:
                        # Gap found, reset current run
                        current_run = 1
        
        return {
            'current_streak': current_streak,
            'longest_streak': longest_streak
        }
