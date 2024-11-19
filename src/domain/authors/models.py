from datetime import datetime
from email.policy import default

from src.domain.videos.models import VideoPublic
from src.infra.database.pydantic_models import PublicModel, InternalModel
from pydantic import Field
from typing import List, Optional


class _AuthorPublic(PublicModel):
    author: str = Field(description="Имя автора")
    author_url: str = Field(description="URL на профиль автора")

    class Config:
        from_attributes = True

class AuthorCreateRequestBody(_AuthorPublic):
    pass

class AuthorPublic(_AuthorPublic):
    pass

class _AuthorInternal(InternalModel):
    author: str = Field(description="Имя автора")
    author_url: str = Field(description="URL на профиль автора")
    followers: List[int] = Field(default_factory=list, description="Список ID подписчиков автора")
    videos: List[int] = Field(default_factory=list, description="Список ID видео")

    class Config:
        from_attributes = True

class AuthorUncommited(_AuthorInternal):
    pass

class Author(_AuthorInternal):
    id: Optional[int] = Field(description="ID автора", exclude=True)


class AuthorWithFollowers(PublicModel):
    id: int
    author: str = Field(description="Имя автора")
    author_url: str = Field(description="URL автора")
    followers_count: int = Field(default=0, description="Количество подписчиков")
    videos: List[VideoPublic] = []

    class Config:
        from_attributes = True

class AuthorWithUnwatchedVideos(PublicModel):
    id: int
    author: str = Field(description="Имя автора")
    author_url: str = Field(description="URL автора")
    videos_count: int = Field(default=0, description="Количество видео")
    videos: List[VideoPublic] = []

class AuthorWithSubscriptions(PublicModel):
    id: int
    author: str = Field(description="Имя автора")
    author_url: str = Field(description="URL автора")
    author_id: int = Field(description="ID автора")
    last_notified_at: datetime = Field(description="Время последнего оповещения")
    followers: List[int] = Field(description="Список идентификаторов подписчиков")


    class Config:
        from_attributes = True

