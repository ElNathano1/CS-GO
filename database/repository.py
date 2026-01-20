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
        )

    def create(self, account: Account) -> None:
        user = User(
            username=account.username,
            password_hash=account.password_hash,
            name=account.name,
            level=account.level,
            profile_picture=account.profile_picture,
        )
        self.session.add(user)
        self.session.commit()

    def add_friend(self, username: str, friend_username: str):
        user = self.session.query(User).filter_by(username=username).first()
        friend = self.session.query(User).filter_by(username=friend_username).first()

        if not user or not friend:
            return

        friendship = Friendship(user_id=user.id, friend_id=friend.id)
        self.session.add(friendship)
        self.session.commit()

    def remove_friend(self, username: str, friend_username: str):
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
