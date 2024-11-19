from email.policy import default

from src.infra.database.pydantic_models import PublicModel, InternalModel
from datetime import datetime
from pydantic import Field
from typing import Optional

class _VideoPublic(PublicModel):
    url: str = Field(description="URL видео")
    title: str = Field(description="Название видео")
    duration: int = Field(description="Длительность видео")
    published_at: datetime = Field(description="Дата публикации видео")
    author_id: int = Field(description="ID автора")

    class Config:
        from_attributes = True

class VideoCreateRequestBody(_VideoPublic):
    pass

class VideoPublic(_VideoPublic):
    pass

class _VideoInternal(InternalModel):
    url: str = Field(description="URL видео")
    title: str = Field(description="Название видео")
    duration: int = Field(description="Длительность видео")
    published_at: datetime = Field(description="Дата публикации видео")
    author_id: int = Field(description="ID автора")

    class Config:
        from_attributes = True

class VideoUncommit(_VideoInternal):
    pass

class Video(_VideoInternal):
    id: Optional[int] = Field(description="ID видео", exclude=True)
