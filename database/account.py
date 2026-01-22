import sys
from pathlib import Path

# Add parent directory to path to import goban
sys.path.insert(0, str(Path(__file__).parent.parent))
from database.models import User


class Account:
    """
    A class representing a user account.

    Attributes:
        username (str): The username of the account.
        password_hash (str): The hash of the password of the account.
        name (str): The name of the account holder.
        level (int): The skill level of the account holder.
        profile_picture (str | None): The path to the profile picture of the account holder.

        friends (list[str]): The list of usernames of friends.
    """

    def __init__(
        self,
        username: str,
        password: str | None = None,
        password_hash: str | None = None,
        name: str = "",
        level: int = 0,
        profile_picture: str | None = None,
        friends: list[str] | None = None,
        is_connected: bool | int = False,
    ):
        """
        Initializes the user account.

        Args:
            username (str): The username of the account.
            password (str): The password of the account.
            name (str): The name of the account holder.
            level (int): The skill level of the account holder. Defaults to 0.
            profile_picture (str): The path to the profile picture of the account holder. Defaults to None.

            friends (list[str]): The list of usernames of friends. Defaults to empty list.
        """

        self.username = username
        self.password_hash = User.hash_password(password) if password else password_hash
        self.name = name
        self.level = level
        self.profile_picture = profile_picture
        self.friends = friends or []
        self.is_connected = (
            is_connected if isinstance(is_connected, bool) else (is_connected == 1)
        )

    def __str__(self) -> str:
        return f"Account: {self.username} - {self.name} (Level {self.level})"

    def check_password(self, password: str) -> bool:
        """
        Checks if the given password matches the stored password hash.

        Args:
            password (str): The password to check.

        Returns:
            bool: True if the password matches, False otherwise.
        """

        return User.hash_password(password) == self.password_hash

    def change_password(self, old_password: str, new_password: str) -> bool:
        """
        Changes the password of the account if the old password matches.

        Args:
            old_password (str): The current password.
            new_password (str): The new password to set.
        Returns:
            bool: True if the password was changed, False otherwise.
        """

        if self.check_password(old_password):
            self.password_hash = User.hash_password(new_password)
            return True
        return False

    def reset_password(self, new_password: str) -> None:
        """
        Resets the password of the account without checking the old password.

        Args:
            new_password (str): The new password to set.
        """

        self.password_hash = User.hash_password(new_password)

    def add_friend(self, friend_id: str) -> None:
        """
        Adds a friend to the account.

        Args:
            friend_id (str): The ID of the friend to add.
        """

        if friend_id not in self.friends:
            self.friends.append(friend_id)

    def remove_friend(self, friend_id: str) -> None:
        """
        Removes a friend from the account.

        Args:
            friend_id (str): The ID of the friend to remove.
        """

        if friend_id in self.friends:
            self.friends.remove(friend_id)
