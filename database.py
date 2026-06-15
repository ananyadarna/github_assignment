"""
Sample Database Connection Module
Demonstrates connection pooling, CRUD operations, and error handling.
"""

import sqlite3
import logging
from contextlib import contextmanager
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    database_path: str = "app.db"
    timeout: float = 5.0
    check_same_thread: bool = False


class DatabaseConnectionPool:
    """Simple connection pool for database management."""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._connection = None
    
    def get_connection(self) -> sqlite3.Connection:
        """Get or create a database connection."""
        if self._connection is None:
            try:
                self._connection = sqlite3.connect(
                    self.config.database_path,
                    timeout=self.config.timeout,
                    check_same_thread=self.config.check_same_thread
                )
                self._connection.row_factory = sqlite3.Row
                logger.info(f"Connected to database: {self.config.database_path}")
            except sqlite3.Error as e:
                logger.error(f"Database connection failed: {e}")
                raise
        
        return self._connection
    
    def close(self):
        """Close the database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("Database connection closed")
    
    @contextmanager
    def get_cursor(self):
        """Context manager for database cursor."""
        connection = self.get_connection()
        cursor = connection.cursor()
        try:
            yield cursor
            connection.commit()
        except sqlite3.Error as e:
            connection.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            cursor.close()


class DatabaseManager:
    """Manages database operations with CRUD methods."""
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        self.config = config or DatabaseConfig()
        self.pool = DatabaseConnectionPool(self.config)
        self.init_database()
    
    def init_database(self):
        """Initialize database schema."""
        with self.pool.get_cursor() as cursor:
            # Create users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create posts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            logger.info("Database schema initialized")
    
    # User operations
    def create_user(self, username: str, email: str, password_hash: str) -> int:
        """Create a new user and return user ID."""
        with self.pool.get_cursor() as cursor:
            try:
                cursor.execute("""
                    INSERT INTO users (username, email, password_hash)
                    VALUES (?, ?, ?)
                """, (username, email, password_hash))
                user_id = cursor.lastrowid
                logger.info(f"User created: {username} (ID: {user_id})")
                return user_id
            except sqlite3.IntegrityError as e:
                logger.error(f"User creation failed: {e}")
                raise
    
    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve user by ID."""
        with self.pool.get_cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Retrieve user by username."""
        with self.pool.get_cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_all_users(self) -> List[Dict[str, Any]]:
        """Retrieve all users."""
        with self.pool.get_cursor() as cursor:
            cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def update_user(self, user_id: int, **kwargs) -> bool:
        """Update user record."""
        allowed_fields = {'email', 'password_hash'}
        fields = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not fields:
            return False
        
        fields['updated_at'] = datetime.utcnow().isoformat()
        
        with self.pool.get_cursor() as cursor:
            set_clause = ", ".join([f"{k} = ?" for k in fields.keys()])
            values = list(fields.values()) + [user_id]
            
            cursor.execute(f"""
                UPDATE users SET {set_clause} WHERE id = ?
            """, values)
            
            logger.info(f"User {user_id} updated")
            return cursor.rowcount > 0
    
    def delete_user(self, user_id: int) -> bool:
        """Delete user record."""
        with self.pool.get_cursor() as cursor:
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            logger.info(f"User {user_id} deleted")
            return cursor.rowcount > 0
    
    # Post operations
    def create_post(self, user_id: int, title: str, content: str) -> int:
        """Create a new post."""
        with self.pool.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO posts (user_id, title, content)
                VALUES (?, ?, ?)
            """, (user_id, title, content))
            post_id = cursor.lastrowid
            logger.info(f"Post created: {title} (ID: {post_id})")
            return post_id
    
    def get_post(self, post_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve post by ID."""
        with self.pool.get_cursor() as cursor:
            cursor.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_user_posts(self, user_id: int) -> List[Dict[str, Any]]:
        """Retrieve all posts by a user."""
        with self.pool.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM posts WHERE user_id = ?
                ORDER BY created_at DESC
            """, (user_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def update_post(self, post_id: int, **kwargs) -> bool:
        """Update post record."""
        allowed_fields = {'title', 'content'}
        fields = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not fields:
            return False
        
        fields['updated_at'] = datetime.utcnow().isoformat()
        
        with self.pool.get_cursor() as cursor:
            set_clause = ", ".join([f"{k} = ?" for k in fields.keys()])
            values = list(fields.values()) + [post_id]
            
            cursor.execute(f"""
                UPDATE posts SET {set_clause} WHERE id = ?
            """, values)
            
            logger.info(f"Post {post_id} updated")
            return cursor.rowcount > 0
    
    def delete_post(self, post_id: int) -> bool:
        """Delete post record."""
        with self.pool.get_cursor() as cursor:
            cursor.execute("DELETE FROM posts WHERE id = ?", (post_id,))
            logger.info(f"Post {post_id} deleted")
            return cursor.rowcount > 0
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute custom query."""
        with self.pool.get_cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def close(self):
        """Close database connection."""
        self.pool.close()


# Example usage
if __name__ == "__main__":
    # Initialize database manager
    db = DatabaseManager()
    
    print("=== User Operations ===")
    
    # Create users
    user1_id = db.create_user("alice", "alice@example.com", "hashed_password_1")
    user2_id = db.create_user("bob", "bob@example.com", "hashed_password_2")
    print(f"Created users: {user1_id}, {user2_id}")
    
    # Get user
    user = db.get_user(user1_id)
    print(f"Retrieved user: {user['username']} ({user['email']})")
    
    # Update user
    db.update_user(user1_id, email="alice.new@example.com")
    print(f"Updated user {user1_id}")
    
    print("\n=== Post Operations ===")
    
    # Create posts
    post1_id = db.create_post(user1_id, "First Post", "This is my first post!")
    post2_id = db.create_post(user1_id, "Second Post", "More content here.")
    print(f"Created posts: {post1_id}, {post2_id}")
    
    # Get user posts
    posts = db.get_user_posts(user1_id)
    print(f"User {user1_id} has {len(posts)} posts")
    for post in posts:
        print(f"  - {post['title']}")
    
    # Update post
    db.update_post(post1_id, content="Updated content for first post!")
    print(f"Updated post {post1_id}")
    
    print("\n=== List All Users ===")
    all_users = db.get_all_users()
    for user in all_users:
        print(f"  - {user['username']} ({user['email']})")
    
    # Close connection
    db.close()
