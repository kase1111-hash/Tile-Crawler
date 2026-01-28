"""
Authentication service for Tile-Crawler

Handles user registration, login, password hashing, and JWT token management.
"""

import os
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional
from contextlib import contextmanager

from jose import jwt, JWTError
from passlib.context import CryptContext

from .models import User, UserCreate, UserInDB, Token, TokenData


# Password hashing configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT configuration
_jwt_secret = os.getenv("JWT_SECRET_KEY")
if not _jwt_secret and os.getenv("ENVIRONMENT", "development") == "production":
    raise ValueError("JWT_SECRET_KEY must be set in production environment")
SECRET_KEY = _jwt_secret or "tile-crawler-dev-secret-key-not-for-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_EXPIRE_DAYS", "7"))


class AuthService:
    """
    Authentication service for user management.

    Handles:
    - User registration with password hashing
    - User login with password verification
    - JWT token generation and validation
    - User profile management
    """

    def __init__(self, db_path: str = "game_data.db"):
        self.db_path = db_path
        self._initialized = False

    @contextmanager
    def _get_connection(self):
        """Get a database connection with context management."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        """Create users table if it doesn't exist."""
        if self._initialized:
            return

        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT,
                    hashed_password TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    total_playtime INTEGER DEFAULT 0,
                    games_played INTEGER DEFAULT 0
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)
            """)

        self._initialized = True

    def _hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        return pwd_context.hash(password)

    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)

    def _create_access_token(self, user: User) -> tuple[str, int]:
        """
        Create a JWT access token for a user.

        Returns:
            Tuple of (token, expires_in_seconds)
        """
        expires_delta = timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
        expire = datetime.now(timezone.utc) + expires_delta

        to_encode = {
            "sub": str(user.id),
            "username": user.username,
            "exp": expire
        }

        token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        expires_in = int(expires_delta.total_seconds())

        return token, expires_in

    def verify_token(self, token: str) -> Optional[TokenData]:
        """
        Verify a JWT token and extract user data.

        Returns:
            TokenData if valid, None if invalid
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = int(payload.get("sub"))
            username = payload.get("username")
            exp = datetime.fromtimestamp(payload.get("exp"))

            if user_id is None or username is None:
                return None

            return TokenData(user_id=user_id, username=username, exp=exp)
        except JWTError:
            return None

    def register(self, user_data: UserCreate) -> Optional[User]:
        """
        Register a new user.

        Args:
            user_data: User registration data

        Returns:
            Created User or None if username exists
        """
        self.initialize()

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Check if username exists
            cursor.execute(
                "SELECT id FROM users WHERE username = ?",
                (user_data.username,)
            )
            if cursor.fetchone():
                return None  # Username taken

            # Check if email exists (if provided)
            if user_data.email:
                cursor.execute(
                    "SELECT id FROM users WHERE email = ?",
                    (user_data.email,)
                )
                if cursor.fetchone():
                    return None  # Email taken

            # Create user
            hashed_password = self._hash_password(user_data.password)
            cursor.execute("""
                INSERT INTO users (username, email, hashed_password, created_at)
                VALUES (?, ?, ?, ?)
            """, (
                user_data.username,
                user_data.email,
                hashed_password,
                datetime.now().isoformat()
            ))

            user_id = cursor.lastrowid

            return User(
                id=user_id,
                username=user_data.username,
                email=user_data.email,
                created_at=datetime.now(),
                is_active=True,
                total_playtime=0,
                games_played=0
            )

    def login(self, username: str, password: str) -> Optional[Token]:
        """
        Authenticate a user and return a token.

        Args:
            username: Username
            password: Plain text password

        Returns:
            Token if successful, None if authentication failed
        """
        self.initialize()

        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM users WHERE username = ? AND is_active = 1
            """, (username,))

            row = cursor.fetchone()
            if not row:
                return None

            if not self._verify_password(password, row["hashed_password"]):
                return None

            # Update last login
            cursor.execute("""
                UPDATE users SET last_login = ? WHERE id = ?
            """, (datetime.now().isoformat(), row["id"]))

            user = User(
                id=row["id"],
                username=row["username"],
                email=row["email"],
                created_at=datetime.fromisoformat(row["created_at"]),
                last_login=datetime.now(),
                is_active=bool(row["is_active"]),
                total_playtime=row["total_playtime"] or 0,
                games_played=row["games_played"] or 0
            )

            access_token, expires_in = self._create_access_token(user)

            return Token(
                access_token=access_token,
                token_type="bearer",
                expires_in=expires_in,
                user=user
            )

    def get_user(self, user_id: int) -> Optional[User]:
        """Get a user by ID."""
        self.initialize()

        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()

            if not row:
                return None

            return User(
                id=row["id"],
                username=row["username"],
                email=row["email"],
                created_at=datetime.fromisoformat(row["created_at"]),
                last_login=datetime.fromisoformat(row["last_login"]) if row["last_login"] else None,
                is_active=bool(row["is_active"]),
                total_playtime=row["total_playtime"] or 0,
                games_played=row["games_played"] or 0
            )

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get a user by username."""
        self.initialize()

        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()

            if not row:
                return None

            return User(
                id=row["id"],
                username=row["username"],
                email=row["email"],
                created_at=datetime.fromisoformat(row["created_at"]),
                last_login=datetime.fromisoformat(row["last_login"]) if row["last_login"] else None,
                is_active=bool(row["is_active"]),
                total_playtime=row["total_playtime"] or 0,
                games_played=row["games_played"] or 0
            )

    def update_playtime(self, user_id: int, additional_seconds: int) -> None:
        """Update a user's total playtime."""
        self.initialize()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET total_playtime = total_playtime + ?
                WHERE id = ?
            """, (additional_seconds, user_id))

    def increment_games_played(self, user_id: int) -> None:
        """Increment a user's games played count."""
        self.initialize()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET games_played = games_played + 1
                WHERE id = ?
            """, (user_id,))

    def delete_user(self, user_id: int) -> bool:
        """Delete a user (soft delete by setting is_active=False)."""
        self.initialize()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET is_active = 0 WHERE id = ?
            """, (user_id,))
            return cursor.rowcount > 0

    def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        """
        Change a user's password.

        Returns:
            True if password was changed, False if old password was incorrect
        """
        self.initialize()

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Get current password hash
            cursor.execute(
                "SELECT hashed_password FROM users WHERE id = ?",
                (user_id,)
            )
            row = cursor.fetchone()
            if not row:
                return False

            # Verify old password
            if not self._verify_password(old_password, row["hashed_password"]):
                return False

            # Update password
            new_hash = self._hash_password(new_password)
            cursor.execute("""
                UPDATE users SET hashed_password = ? WHERE id = ?
            """, (new_hash, user_id))

            return True


# Singleton management
_auth_service: Optional[AuthService] = None


def get_auth_service(db_path: Optional[str] = None) -> AuthService:
    """Get the singleton auth service instance."""
    global _auth_service
    if _auth_service is None:
        # Use DB_PATH env var if set, otherwise default to game_data.db
        if db_path is None:
            db_path = os.getenv("DB_PATH", "game_data.db")
        _auth_service = AuthService(db_path)
    return _auth_service


def reset_auth_service() -> None:
    """Reset the auth service singleton (for testing)."""
    global _auth_service
    _auth_service = None
