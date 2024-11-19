from src.domain.authors.models import AuthorPublic
from src.infra.database.pydantic_models import PublicModel, InternalModel

from pydantic import Field
from typing import List, Optional


class _UserPublic(PublicModel):
    username: str = Field(description="Имя пользователя")
    user_tag: str = Field(description="ID чата")

    class Config:
        from_attributes = True

class UserCreateRequestBody(_UserPublic):
    pass

class UserPublic(_UserPublic):
    pass

class _UserInternal(InternalModel):
    username: str = Field(description="Имя пользователя")
    user_tag: str = Field(description="ID чата")
    author_id: List[int] = Field(default_factory=list, description="Список ID авторов")
    subscriptions_id: List[int] = Field(default_factory=list, description="Список ID подписок")

    class Config:
        from_attributes = True

class UserUncommit(_UserInternal):
    pass

class User(_UserInternal):
    id: Optional[int] = Field(description="ID пользователя", exclude=True)


class UserSubscriptionCount(PublicModel):
    user_id: int
    count_subscriptions: int

class UserSubscriptionData(PublicModel):
    id: int
    username: str
    user_tag: str
    subscriptions_count: int = Field(default=0, description="Количество подписок пользователя")

    class Config:
        from_attributes = True

class UserWithAuthorsAndSubscriptions(UserSubscriptionData):
    authors: List[AuthorPublic] = Field(default_factory=list, description="Список авторов пользователя")

    class Config:
        from_attributes = True
