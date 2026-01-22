from sqlalchemy.orm import Session
from database.models import User, Friendship
from database.account import Account


class AccountRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_username(self, username: str) -> Account | None:
        user = self.session.query(User).filter(User.username == username).first()
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
        )

    def get_all_users(self) -> list[Account] | None:
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
                )
            )

        return all_users

    def create(self, account: Account) -> None:
        user = User(
            username=account.username,
            password_hash=account.password_hash,
            name=account.name,
            level=account.level,
            profile_picture=account.profile_picture,
            is_connected=False,
        )
        self.session.add(user)
        self.session.commit()

    def change_password(
        self, username: str, old_password: str, new_password: str
    ) -> None:
        user = self.session.query(User).filter_by(username=username).first()

        if not user:
            return

        if User.hash_password(old_password) == user.password_hash:  # type: ignore
            user.password_hash = User.hash_password(new_password)  # type: ignore
            self.session.commit()

    def reset_password(self, username: str, new_password: str) -> None:
        user = self.session.query(User).filter_by(username=username).first()
        if user:
            user.password_hash = User.hash_password(new_password)  # type: ignore
            self.session.commit()

    def change_name(self, username: str, new_name: str) -> None:
        user = self.session.query(User).filter_by(username=username).first()
        if user:
            user.name = new_name  # type: ignore
            self.session.commit()

    def add_friend(self, username: str, friend_username: str) -> None:
        user = self.session.query(User).filter_by(username=username).first()
        friend = self.session.query(User).filter_by(username=friend_username).first()

        if not user or not friend:
            return

        friendship = Friendship(user_id=user.id, friend_id=friend.id)
        self.session.add(friendship)
        self.session.commit()

    def remove_friend(self, username: str, friend_username: str) -> None:
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
        user = self.session.query(User).filter_by(username=username).first()
        if user:
            user.level = new_level  # type: ignore
            self.session.commit()

    def connect(self, username: str) -> None:
        user = self.session.query(User).filter_by(username=username).first()
        if user:
            user.is_connected = 1  # type: ignore
            self.session.commit()

    def disconnect(self, username: str) -> None:
        user = self.session.query(User).filter_by(username=username).first()
        if user:
            user.is_connected = 0  # type: ignore
            self.session.commit()

    def get_connected(self) -> list[Account] | None:
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
                )
            )

        return connected

    def remove_user(self, username: str) -> None:
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
