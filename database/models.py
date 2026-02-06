"""
Database models and ORM configuration for the CS-GO user service.

This module provides:
- SQLAlchemy ORM models (User, Friendship)
- Database engine initialization
- Password hashing utilities
- Session management

Models:
- User: Represents a player account with profile, level, and friends
- Friendship: Represents a directional friendship relationship between users
"""

from __future__ import annotations

import os
from sqlalchemy import (
    create_engine,
    text,
    inspect,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship, Session
import hashlib


# Créer la base de données
engine = create_engine(os.environ["DATABASE_URL"], echo=False)
Base = declarative_base()


class User(Base):
    """
    SQLAlchemy ORM model for a user account.

    Attributes:
        id: Primary key
        username: Unique username (indexed for fast lookup)
        password_hash: SHA-256 hash of password
        name: Display name of the user
        level: Rating/skill level (for matchmaking)
        profile_picture: Path identifier for user's profile picture
        is_connected: Connection status (1=connected, 0=offline)
        friendships_initiated: List of friendships where this user is the initiator
        friendships_received: List of friendships where this user is the friend
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(64), nullable=False)
    name = Column(String(100), nullable=False)
    level = Column(Integer, default=0)
    profile_picture = Column(String(255), nullable=True)
    is_connected = Column(Integer, nullable=False, default=0)
    in_game = Column(Integer, nullable=False, default=0)

    # Relations
    friendships_initiated = relationship(
        "Friendship",
        foreign_keys="Friendship.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    friendships_received = relationship(
        "Friendship",
        foreign_keys="Friendship.friend_id",
        back_populates="friend",
        cascade="all, delete-orphan",
    )

    games_played_as_black = relationship(
        "Game",
        foreign_keys="Game.black_player_id",
        back_populates="black_player",
        cascade="all, delete-orphan",
    )
    games_played_as_white = relationship(
        "Game",
        foreign_keys="Game.white_player_id",
        back_populates="white_player",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"User(id={self.id}, username={self.username}, name={self.name}, level={self.level})"

    def __str__(self) -> str:
        return f"Account: {self.username} - {self.name} (Level {self.level})"

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using SHA-256.

        Args:
            password: The plaintext password to hash

        Returns:
            Hexadecimal SHA-256 hash of the password
        """
        return hashlib.sha256(password.encode()).hexdigest()

    def add_friend(self, friend: User, session: Session) -> None:
        """
        Add a friend to this user's friend list.

        Args:
            friend: The User object to add as friend
            session: SQLAlchemy session for database operations
        """
        if not self.is_friend(friend):
            friendship = Friendship(user_id=self.id, friend_id=friend.id)
            session.add(friendship)
            session.commit()

    def remove_friend(self, friend: User, session: Session) -> None:
        """
        Remove a friend from this user's friend list.

        Args:
            friend: The User object to remove from friends
            session: SQLAlchemy session for database operations
        """
        friendship = (
            session.query(Friendship)
            .filter(
                (Friendship.user_id == self.id) & (Friendship.friend_id == friend.id)
            )
            .first()
        )
        if friendship:
            session.delete(friendship)
            session.commit()

    def is_friend(self, friend: User) -> bool:
        """
        Check if another user is a friend of this user.

        Args:
            friend: The User object to check

        Returns:
            True if user is a friend, False otherwise
        """
        return any(f.friend_id == friend.id for f in self.friendships_initiated)

    def get_friends(self) -> list[User]:
        """
        Get list of all friends of this user.

        Returns:
            List of User objects that are friends
        """
        return [f.friend for f in self.friendships_initiated]

    def get_friend_count(self) -> int:
        """
        Get the number of friends.

        Returns:
            Integer count of friends
        """
        return len(self.friendships_initiated)

    def get_games(self) -> list[Game]:
        """
        Get list of all games played by this user.

        Returns:
            List of Game objects that this user has played
        """
        return self.games_played_as_black + self.games_played_as_white

    def get_game_count(self) -> int:
        """
        Get the number of games played.

        Returns:
            Integer count of games played
        """
        return len(self.games_played_as_black) + len(self.games_played_as_white)

    def get_win_count(self) -> int:
        """
        Get the number of games won by this user.

        Returns:
            Integer count of games won
        """
        wins_as_black = sum(
            1 for game in self.games_played_as_black if game.result == "1-0"
        )
        wins_as_white = sum(
            1 for game in self.games_played_as_white if game.result == "0-1"
        )
        return wins_as_black + wins_as_white


class Friendship(Base):
    """
    SQLAlchemy ORM model for a friendship relationship between two users.

    Represents a directional friendship from user_id to friend_id.
    Includes a unique constraint to prevent duplicate friendships.

    Attributes:
        id: Primary key
        user_id: Foreign key to User (friend initiator)
        friend_id: Foreign key to User (friend being followed)
        user: Relationship to the initiating User
        friend: Relationship to the friend User
    """

    __tablename__ = "friendships"

    __table_args__ = (UniqueConstraint("user_id", "friend_id", name="uq_friendship"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    friend_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    user = relationship(
        "User", foreign_keys=[user_id], back_populates="friendships_initiated"
    )
    friend = relationship(
        "User", foreign_keys=[friend_id], back_populates="friendships_received"
    )

    def __repr__(self) -> str:
        return f"Friendship(user_id={self.user_id}, friend_id={self.friend_id})"


class Game(Base):
    """
    SQLAlchemy ORM model for a game record.

    Attributes:
        id: Primary key
        black_player_id: Foreign key to User (first player)
        white_player_id: Foreign key to User (second player)
        date: Timestamp of when the game was played
        result: String representing the game result (e.g., "1-0", "0-1", "0.5-0.5")
        moves: String representing the sequence of moves in the game
    """

    __tablename__ = "games"

    __table_args__ = (
        UniqueConstraint("black_player_id", "white_player_id", "date", name="uq_game"),
    )

    id = Column(Integer, primary_key=True, index=True)
    black_player_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    white_player_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    result = Column(String(10), nullable=False)
    moves = Column(Text, nullable=False)

    black_player = relationship(
        "User", foreign_keys=[black_player_id], back_populates="games_played_as_black"
    )
    white_player = relationship(
        "User", foreign_keys=[white_player_id], back_populates="games_played_as_white"
    )

    def __repr__(self) -> str:
        return f"Game(id={self.id}, black_player_id={self.black_player_id}, white_player_id={self.white_player_id}, date={self.date}, result={self.result})"


# Database initialization
def init_db():
    """Initialize database and create all tables."""
    Base.metadata.create_all(bind=engine)


def get_session() -> Session:
    """
    Get a new SQLAlchemy session.

    Returns:
        A new Session bound to the database engine
    """
    return Session(engine)


init_db()

sql = """
ALTER TABLE users
ADD COLUMN in_game TINYINT(1) NOT NULL DEFAULT 0
"""

with engine.begin() as conn:
    conn.execute(text(sql))
