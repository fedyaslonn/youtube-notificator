from ast import Index
from datetime import datetime
from email.policy import default

from sqlalchemy.orm import relationship, declarative_base, DeclarativeBase
from sqlalchemy import Column, ForeignKey, Integer, String, Table, MetaData, DateTime, Boolean
from typing import TypeVar, Type
from sqlalchemy import Index

class Base(DeclarativeBase):
    pass

class BaseModel(Base):
    __abstract__ = True
    id = Column(Integer, primary_key=True, autoincrement=True)

T = TypeVar("T", bound=Base)

user_author = Table(
    "user_authors",
    Base.metadata,
    Column('user_id', ForeignKey('users.id', ondelete="CASCADE"), primary_key=True),
    Column('author_id', ForeignKey('authors.id', ondelete="CASCADE"), primary_key=True)
)

class User(BaseModel):
    __tablename__ = "users"

    username = Column(String, nullable=False)
    user_tag = Column(String, nullable=False)

    authors = relationship("Author", secondary=user_author, back_populates="followers", cascade="all, delete")
    subscriptions = relationship("Subscription", back_populates="user")

    videos = relationship("Video", back_populates="user", cascade="all, delete-orphan")

class Author(BaseModel):
    __tablename__ = "authors"

    author = Column(String, index=True, nullable=False)
    author_url = Column(String, index=True, nullable=False)

    videos = relationship("Video", back_populates="author", cascade="all, delete-orphan")

    followers = relationship("User", secondary=user_author, back_populates="authors", cascade="all, delete")
    subscriptions = relationship("Subscription", back_populates="author", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_author_name_url', 'author', 'author_url'),
    )

class Video(BaseModel):
    __tablename__ = "videos"

    url = Column(String, index=True)
    title = Column(String, index=True, nullable=False)
    duration = Column(String, nullable=False)
    published_at = Column(String, nullable=False)
    author_id = Column(Integer, ForeignKey("authors.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    viewed = Column(Boolean, default=False)

    author = relationship("Author", back_populates="videos")
    user = relationship("User", back_populates="videos")

    __table_args__ = (
        Index('ix_video_url_title_duration_published_date', 'url', 'title', 'duration', 'published_at'),
    )


class Subscription(BaseModel):
    __tablename__ = "subscriptions"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(Integer, ForeignKey("authors.id", ondelete="CASCADE"), nullable=False)
    last_notified_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="subscriptions")
    author = relationship("Author", back_populates="subscriptions")

    __table_args__ = (
        Index('ix_subscription_user_author', 'user_id', 'author_id', unique=True),
    )