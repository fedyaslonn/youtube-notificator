from typing import Optional

from src.infra.database.pydantic_models import PublicModel, InternalModel
from datetime import datetime
from pydantic import Field

class _SubscriptionPublic(PublicModel):
    last_notified_at: datetime = Field(description="Время последнего уведомления")
    user_id: int = Field(description="ID пользователя")
    author_id: int = Field(description="ID автора")

    class Config:
        from_attributes = True

class SubscriptionRequestBody(_SubscriptionPublic):
    pass

class SubscriptionPublic(_SubscriptionPublic):
    pass

class _SubscriptionInternal(InternalModel):
    user_id: int = Field(description="ID пользователя")
    author_id: int = Field(description="ID автора")
    last_notified_at: datetime = Field(description="Время последнего уведомления")

    class Config:
        from_attributes = True

class SubscriptionUncommit(_SubscriptionInternal):
    pass

class Subscription(_SubscriptionInternal):
    id: Optional[int] = Field(default=None, description="ID подписки", exclude=True)