-- Postgres initial schema (Supabase compatible)

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


