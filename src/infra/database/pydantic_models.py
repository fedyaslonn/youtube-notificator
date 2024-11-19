from pydantic import BaseModel,  Extra
from typing import TypeVar
import json


class PublicModel(BaseModel):
    class Config:
        from_attributes = True
        use_enum_values = True
        validate_assignment = True
        arbitrary_types_allowed = True

    def encoded_dict(self, by_alies=True):
        return json.loads(self.json(by_alies=by_alies))

class InternalModel(BaseModel):
    class Config:
        from_attributes = True
        use_enum_values = True
        validate_assignment = True
        extra = Extra.forbid

    def update_fields(self, **kwargs):
        for field, value in kwargs.items():
            if field in self.__fields__:
                setattr(self, field, value)
            else:
                raise ValueError(f"Поле {field} не разрешено в модели {self.__class__.__name__}")

# class UserSchema(BaseModel):
#     id: int
#     username: str
#     user_tag: str
#     authors: List[int]
#
#     class Config:
#         orm_mode = True
#
# class AuthorSchema(BaseModel):
#     id: int
#     author: str
#     author_url: HttpUrl
#     followers: List[int]
#
#     class Config:
#         orm_mode = True
#
# class VideoSchema(BaseModel):
#     id: int
#     video: str
#     url: HttpUrl
#     title: str
#     duration: int
#     published_at: datetime
#     author_id: int
#
#     class Config:
#         orm_mode = True
#
# class Subscription(BaseModel):
#     id: int
#     user_id: int
#     author_id: int
#     last_notified_at: datetime
#
#     class Config:
#         orm_mode = True
#
# class UserCreateSchema(BaseModel):
#     username: str
#
# class AuthorCreateSchema(BaseModel):
#     author: str
#     author_url: HttpUrl
#
# class VideoCreateSchema(BaseModel):
#     video_id: str
#     url: HttpUrl
#     title: str
#     duration: int
#     published_at: datetime
#     author_id: int
