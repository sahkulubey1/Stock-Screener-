import sqlite3

# Connect to the SQLite database (this will create the file if it doesn't exist)
connection = sqlite3.connect('database.db')

# Create a cursor object to execute SQL commands
cursor = connection.cursor()

# Create the 'user' table if it doesn't exist
cursor.execute('''
    CREATE TABLE IF NOT EXISTS user (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_verified INTEGER DEFAULT 0
    )
''')

# Create the 'indicator_weights' table for user preferences with an 'id' column
cursor.execute('''
    CREATE TABLE IF NOT EXISTS indicator_weights (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        relative_volume REAL,
        news_event REAL,
        price_movement REAL,
        historical_volatility REAL,
        available_shares REAL,
        stock_universe TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES user(id)
    )
''')
# Create the 'indicator_results' table to store stock screener results
cursor.execute('''
    CREATE TABLE IF NOT EXISTS indicator_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        weight_id BIGINT,
        ticker TEXT,
        score REAL,
        market_sentiment REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES user(id)
    )
''')

# Commit the changes and close the connection
connection.commit()
connection.close()
