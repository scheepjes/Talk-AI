import sqlite3
from datetime import datetime
from contextlib import contextmanager

DATABASE_PATH = "conversations.db"


@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Initialize the database with required tables."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                topic TEXT NOT NULL,
                depth_level INTEGER NOT NULL,
                server_a_url TEXT,
                server_b_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                sender TEXT,
                display INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations (id)
            )
        """)
        # Migration: add columns if they don't exist
        cursor.execute("PRAGMA table_info(conversations)")
        columns = [row["name"] for row in cursor.fetchall()]
        if "server_a_url" not in columns:
            cursor.execute("ALTER TABLE conversations ADD COLUMN server_a_url TEXT")
        if "server_b_url" not in columns:
            cursor.execute("ALTER TABLE conversations ADD COLUMN server_b_url TEXT")
        if "language" not in columns:
            cursor.execute("ALTER TABLE conversations ADD COLUMN language TEXT DEFAULT 'en'")
        conn.commit()


def save_conversation(conversation_id, topic, depth_level, server_a_url=None, server_b_url=None, language="en"):
    """Save a new conversation."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO conversations (id, topic, depth_level, server_a_url, server_b_url, language)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (conversation_id, topic, depth_level, server_a_url, server_b_url, language),
        )
        conn.commit()


def save_message(conversation_id, role, content, sender=None, display=True):
    """Save a message to the database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO messages (conversation_id, role, content, sender, display)
            VALUES (?, ?, ?, ?, ?)
        """,
            (conversation_id, role, content, sender, 1 if display else 0),
        )
        conn.commit()


def get_all_conversations():
    """Get all conversations sorted by creation date."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, topic, depth_level, server_a_url, server_b_url, language, created_at
            FROM conversations
            ORDER BY created_at DESC
        """
        )
        return cursor.fetchall()


def get_conversation_messages(conversation_id):
    """Get all messages for a specific conversation."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT role, content, sender, display, created_at
            FROM messages
            WHERE conversation_id = ?
            ORDER BY created_at ASC
        """,
            (conversation_id,),
        )
        return cursor.fetchall()


def delete_conversation(conversation_id):
    """Delete a conversation and all its messages."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM messages WHERE conversation_id = ?", (conversation_id,)
        )
        cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        conn.commit()


def delete_all_conversations():
    """Delete all conversations."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages")
        cursor.execute("DELETE FROM conversations")
        conn.commit()


# Initialize database when module is imported
init_db()
