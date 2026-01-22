from __future__ import annotations

import os
from sqlalchemy import (
    create_engine,
    text,
    inspect,
    Column,
    Integer,
    String,
    Boolean,
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
    Modèle SQLAlchemy pour représenter un utilisateur.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(64), nullable=False)
    name = Column(String(100), nullable=False)
    level = Column(Integer, default=0)
    profile_picture = Column(String(255), nullable=True)
    is_connected = Column(Boolean, nullable=False)

    # Relations
    friendships_initiated = relationship(
        "Friendship",
        foreign_keys="Friendship.user_id",
        backref="user",
        cascade="all, delete-orphan",
    )
    friendships_received = relationship(
        "Friendship",
        foreign_keys="Friendship.friend_id",
        backref="friend",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"User(id={self.id}, username={self.username}, name={self.name}, level={self.level})"

    def __str__(self) -> str:
        return f"Account: {self.username} - {self.name} (Level {self.level})"

    @staticmethod
    def hash_password(password: str) -> str:
        """Hache un mot de passe avec SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()

    def add_friend(self, friend: User, session: Session) -> None:
        """
        Ajoute un ami à la liste d'amis.

        Args:
            friend (User): L'utilisateur à ajouter en ami.
            session (Session): La session SQLAlchemy.
        """
        if not self.is_friend(friend):
            friendship = Friendship(user_id=self.id, friend_id=friend.id)
            session.add(friendship)
            session.commit()

    def remove_friend(self, friend: User, session: Session) -> None:
        """
        Supprime un ami de la liste d'amis.

        Args:
            friend (User): L'utilisateur à supprimer de la liste d'amis.
            session (Session): La session SQLAlchemy.
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
        Vérifie si un utilisateur est ami avec un autre.

        Args:
            friend (User): L'utilisateur à vérifier.

        Returns:
            bool: True si c'est un ami, False sinon.
        """
        return any(f.friend_id == friend.id for f in self.friendships_initiated)

    def get_friends(self) -> list[User]:
        """
        Retourne la liste des amis de l'utilisateur.

        Returns:
            list[User]: Liste des amis.
        """
        return [f.friend for f in self.friendships_initiated]

    def get_friend_count(self) -> int:
        """
        Retourne le nombre d'amis.

        Returns:
            int: Nombre d'amis.
        """
        return len(self.friendships_initiated)


class Friendship(Base):
    """
    Modèle SQLAlchemy pour représenter une amitié entre deux utilisateurs.
    """

    __tablename__ = "friendships"

    __table_args__ = (UniqueConstraint("user_id", "friend_id", name="uq_friendship"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    friend_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    def __repr__(self) -> str:
        return f"Friendship(user_id={self.user_id}, friend_id={self.friend_id})"


# Créer les tables
def init_db():
    """Initialise la base de données."""
    Base.metadata.create_all(bind=engine)


def get_session() -> Session:
    """Retourne une nouvelle session SQLAlchemy."""
    return Session(engine)
