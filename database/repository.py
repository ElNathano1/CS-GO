"""
Data access layer for user account operations using the Repository pattern.

This module provides the AccountRepository class which encapsulates all database
operations for user accounts, friendships, and profile management. It translates
between SQLAlchemy ORM models and the Account business logic class.

Classes:
- AccountRepository: Repository pattern implementation for User data access
"""

from sqlalchemy.orm import Session
from database.models import User, Friendship, Game
from database.account import Account


class AccountRepository:
    def __init__(self, session: Session):
        """
        Initialize the repository with a database session.

        Args:
            session: SQLAlchemy session for database operations
        """
        self.session = session

    def get_by_username(self, username: str) -> Account | None:
        """
        Retrieve a user account by username.

        Args:
            username: The username to search for

        Returns:
            Account object if user exists, None otherwise
        """
        user = self.session.query(User).filter_by(username=username).first()
        if not user:
            return None

        friends = [f.friend.username for f in user.friendships_initiated]

        return Account(
            username=user.username,  # type: ignore
            password_hash=user.password_hash,  # type: ignore
            name=user.name,  # type: ignore
            level=user.level,  # type: ignore
            profile_picture=user.profile_picture,  # type: ignore
            friends=friends,
            is_connected=user.is_connected,  # type: ignore
            in_game=user.in_game,  # type: ignore
        )

    def get_all_users(self) -> list[Account] | None:
        """
        Retrieve all user accounts from the database.

        Returns:
            List of Account objects, or None if no users exist
        """
        users = self.session.query(User).all()
        if not users:
            return None

        all_users = []
        for user in users:
            friends = [f.friend.username for f in user.friendships_initiated]
            all_users.append(
                Account(
                    username=user.username,  # type: ignore
                    password_hash=user.password_hash,  # type: ignore
                    name=user.name,  # type: ignore
                    level=user.level,  # type: ignore
                    profile_picture=user.profile_picture,  # type: ignore
                    friends=friends,
                    is_connected=user.is_connected,  # type: ignore
                    in_game=user.in_game,  # type: ignore
                )
            )

        return all_users

    def create(self, account: Account) -> None:
        """
        Create a new user account in the database.

        Args:
            account: The Account object to create
        """
        user = User(
            username=account.username,
            password_hash=account.password_hash,
            name=account.name,
            level=account.level,
            profile_picture=account.profile_picture,
            is_connected=account.is_connected,
        )
        self.session.add(user)
        self.session.commit()

    def change_password(
        self, username: str, old_password: str, new_password: str
    ) -> None:
        """
        Change a user's password if the old password is correct.

        Args:
            username: The username of the account
            old_password: The current password (plaintext)
            new_password: The new password (plaintext)
        """
        user = self.session.query(User).filter_by(username=username).first()

        if not user:
            return

        if User.hash_password(old_password) == user.password_hash:  # type: ignore
            user.password_hash = User.hash_password(new_password)  # type: ignore
            self.session.commit()

    def reset_password(self, username: str, new_password: str) -> None:
        """
        Reset a user's password without verifying the old password.

        Args:
            username: The username of the account
            new_password: The new password (plaintext)
        """
        user = self.session.query(User).filter_by(username=username).first()
        if user:
            user.password_hash = User.hash_password(new_password)  # type: ignore
            self.session.commit()

    def change_name(self, username: str, new_name: str) -> None:
        """
        Update a user's display name.

        Args:
            username: The username of the account
            new_name: The new display name
        """
        user = self.session.query(User).filter_by(username=username).first()
        if user:
            user.name = new_name  # type: ignore
            self.session.commit()

    def change_profile_picture(self, username: str, new_profile_picture: str) -> None:
        """
        Update a user's profile picture.

        Args:
            username: The username of the account
            new_profile_picture: Path identifier for the new profile picture
        """
        user = self.session.query(User).filter_by(username=username).first()
        if user:
            user.profile_picture = new_profile_picture  # type: ignore
            self.session.commit()

    def add_friend(self, username: str, friend_username: str) -> None:
        """
        Add a friend relationship between two users.

        Args:
            username: The username of the user initiating the friendship
            friend_username: The username of the friend to add
        """
        user = self.session.query(User).filter_by(username=username).first()
        friend = self.session.query(User).filter_by(username=friend_username).first()

        if not user or not friend:
            return

        friendship = Friendship(user_id=user.id, friend_id=friend.id)
        self.session.add(friendship)
        self.session.commit()

    def remove_friend(self, username: str, friend_username: str) -> None:
        """
        Remove a friend relationship between two users.

        Args:
            username: The username of the user
            friend_username: The username of the friend to remove
        """
        user = self.session.query(User).filter_by(username=username).first()
        friend = self.session.query(User).filter_by(username=friend_username).first()

        if not user or not friend:
            return

        friendship = (
            self.session.query(Friendship)
            .filter(
                (Friendship.user_id == user.id) & (Friendship.friend_id == friend.id)
            )
            .first()
        )

        if friendship:
            self.session.delete(friendship)
            self.session.commit()

    def update_level(self, username: str, new_level: int) -> None:
        """
        Update a user's skill level (for matchmaking).

        Args:
            username: The username of the account
            new_level: The new skill level
        """
        user = self.session.query(User).filter_by(username=username).first()
        if user:
            user.level = new_level  # type: ignore
            self.session.commit()

    def connect(self, username: str) -> None:
        """
        Mark a user as connected/online.

        Args:
            username: The username of the account
        """
        user = self.session.query(User).filter_by(username=username).first()
        if user:
            user.is_connected = 1  # type: ignore
            self.session.commit()

    def disconnect(self, username: str) -> None:
        """
        Mark a user as disconnected/offline.

        Args:
            username: The username of the account
        """
        user = self.session.query(User).filter_by(username=username).first()
        if user:
            user.is_connected = 0  # type: ignore
            self.session.commit()

    def set_in_game(self, username: str, in_game: bool) -> None:
        """
        Update a user's in-game status.

        Args:
            username: The username of the account
            in_game: True if the user is currently in a game, False otherwise
        """
        user = self.session.query(User).filter_by(username=username).first()
        if user:
            user.in_game = 1 if in_game else 0  # type: ignore
            self.session.commit()

    def get_connected(self) -> list[Account] | None:
        """
        Retrieve all currently connected/online users.

        Returns:
            List of connected Account objects, or None if no users are online
        """
        users = self.session.query(User).filter_by(is_connected=1).all()
        if not users:
            return None

        connected = []
        for user in users:
            friends = [f.friend.username for f in user.friendships_initiated]
            connected.append(
                Account(
                    username=user.username,  # type: ignore
                    password_hash=user.password_hash,  # type: ignore
                    name=user.name,  # type: ignore
                    level=user.level,  # type: ignore
                    profile_picture=user.profile_picture,  # type: ignore
                    friends=friends,
                    is_connected=user.is_connected,  # type: ignore
                    in_game=user.in_game,  # type: ignore
                )
            )

        return connected

    def get_free(self) -> list[Account] | None:
        """
        Retrieve all currently connected users who are not in a game.

        Returns:
            List of free Account objects, or None if no users are available
        """
        users = self.session.query(User).filter_by(is_connected=1, in_game=0).all()
        if not users:
            return None

        free_users = []
        for user in users:
            friends = [f.friend.username for f in user.friendships_initiated]
            free_users.append(
                Account(
                    username=user.username,  # type: ignore
                    password_hash=user.password_hash,  # type: ignore
                    name=user.name,  # type: ignore
                    level=user.level,  # type: ignore
                    profile_picture=user.profile_picture,  # type: ignore
                    friends=friends,
                    is_connected=user.is_connected,  # type: ignore
                    in_game=user.in_game,  # type: ignore
                )
            )

        return free_users

    def save_game(
        self,
        black_player_username: str,
        white_player_username: str,
        date: str,
        result: str = "0.5-0.5",
        moves: str = "",
    ) -> None:
        """
        Save a completed game to the database.

        Args:
            black_player_username: The username of the black player
            white_player_username: The username of the white player
            date: The date the game was played (ISO format)
            result: The result of the game ("black_win", "white_win", "draw")
            moves: The moves made during the game in a specific format
        """

        # This method would create a new Game record in the database
        # and associate it with the black and white players.

        black_player = (
            self.session.query(User).filter_by(username=black_player_username).first()
        )
        white_player = (
            self.session.query(User).filter_by(username=white_player_username).first()
        )

        if not black_player or not white_player:
            return

        game = Game(
            black_player_id=black_player.id,
            white_player_id=white_player.id,
            date=date,
            result=result,
            moves=moves,
        )
        self.session.add(game)
        self.session.commit()

    def get_game_history(self, username: str) -> list[Game] | None:
        """
        Retrieve the game history for a specific user.

        Args:
            username: The username of the account
        Returns:
            List of Game objects the user participated in, or None if no games found
        """
        user = self.session.query(User).filter_by(username=username).first()
        if not user:
            return None

        games_as_black = (
            self.session.query(Game).filter_by(black_player_id=user.id).all()
        )
        games_as_white = (
            self.session.query(Game).filter_by(white_player_id=user.id).all()
        )

        return games_as_black + games_as_white

    def remove_user(self, username: str) -> None:
        """
        Delete a user account and all associated friendships from the database.

        Args:
            username: The username of the account to delete
        """
        user = self.session.query(User).filter_by(username=username).first()

        if not user:
            return

        friendships = (
            self.session.query(Friendship)
            .filter((Friendship.user_id == user.id) | (Friendship.friend_id == user.id))
            .all()
        )

        for friendship in friendships:
            self.session.delete(friendship)

        self.session.delete(user)
        self.session.commit()
