from asyncpg.pgproto.pgproto import timedelta
from fastapi import APIRouter, Request, status, Depends, HTTPException, Query, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from src.application.authentication.authentication_form import OAuth2PasswordRequestFormCustom

from src.domain.users.models import UserCreateRequestBody, UserPublic, User, UserSubscriptionCount, UserSubscriptionData, UserWithAuthorsAndSubscriptions
from src.infra.database.uow import UnitOfWork, get_unit_of_work

from typing import List, Optional

from src.settings.config import access_token_expire_minutes, refresh_token_expire_days

from src.logic.authentication.authentication import create_access_token, refresh_access_token, verify_password, \
    get_password_hash, oauth2_scheme

user_router = APIRouter(prefix="/users", tags=["Users"])


@user_router.post("/create_user", status_code=status.HTTP_201_CREATED)
async def create_user(request: UserCreateRequestBody, uow: UnitOfWork = Depends(get_unit_of_work)):
    try:
        async with uow:
            hashed_password = get_password_hash(request.user_tag)
            user = await uow.users.create_user(request.username, request.user_tag)
        return {
            "status": "success",
            "user": user
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@user_router.get("/get_all_users", response_model=List[UserPublic], status_code=status.HTTP_200_OK)
async def get_all_users(token = Depends(oauth2_scheme), uow: UnitOfWork = Depends(get_unit_of_work), limit: Optional[int] = Query(default=None)):
    try:
        user_list = await uow.users.get_all(limit=limit)

        if not isinstance(user_list, list):
            raise HTTPException(status_code=500, detail="Некорректный формат данных")

        return user_list

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@user_router.get("/get_by_username", response_model=UserPublic, status_code=status.HTTP_200_OK)
async def get_by_username(token = Depends(oauth2_scheme), uow: UnitOfWork = Depends(get_unit_of_work), username: str = Query(...)):
    try:
        user = await uow.users.get_by_username(username=username)

        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        return user

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@user_router.get("/get_by_tag", response_model=UserPublic, status_code=status.HTTP_200_OK)
async def get_by_tag(token = Depends(oauth2_scheme), uow: UnitOfWork = Depends(get_unit_of_work), tag: str = Query(...)):
    try:
        user = await uow.users.get_by_tag(tag=tag)

        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        return user

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@user_router.get("/get_user/{id}", response_model=UserPublic, status_code=status.HTTP_200_OK)
async def get_user_by_id(id: int, token = Depends(oauth2_scheme), uow: UnitOfWork = Depends(get_unit_of_work)):
    try:
        user_by_id = await uow.users.get_by_id(id=id)

        if not user_by_id:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        return user_by_id

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@user_router.delete("/delete_user/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(id: int, uow: UnitOfWork = Depends(get_unit_of_work)):
    try:
        user_deleted = await uow.users.delete_user(id=id)

        if not user_deleted:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@user_router.post("/login", status_code=status.HTTP_202_ACCEPTED)
async def login_user(form_data: OAuth2PasswordRequestForm = Depends(), uow: UnitOfWork = Depends(get_unit_of_work)):
    try:
        user_data = await uow.users.get_by_username(username=form_data.username)
        if not user_data or not verify_password(form_data.password, str(user_data.user_tag)):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный username или tag")

        access_token_expires = timedelta(minutes=access_token_expire_minutes)
        access_token = create_access_token(data={"sub": user_data.username, "user_tag": user_data.user_tag},
                                           expires_delta=access_token_expires)

        refresh_token_expires = timedelta(days=refresh_token_expire_days)
        refresh_token = refresh_access_token(data={"sub": user_data.username, "user_tag": user_data.user_tag},
                                             expires_delta=refresh_token_expires)

        return {"access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "Bearer"}

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@user_router.get("/count_subscriptions", status_code=status.HTTP_200_OK)
async def get_count_subscriptions(token = Depends(oauth2_scheme), uow: UnitOfWork = Depends(get_unit_of_work), user_id: int = Query(...)):
    try:
        async with uow:
            user_subscriptions = await uow.users.count_subscriptions(user_id)

        return UserSubscriptionCount(user_id=user_id, count_subscriptions=user_subscriptions)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Не удалось пользователя с подписками {str(e)}")

@user_router.get("/get_users_with_count_subscriptions", response_model=List[UserSubscriptionData], status_code=status.HTTP_200_OK)
async def get_users_with_count_subscriptions(token = Depends(oauth2_scheme), uow: UnitOfWork = Depends(get_unit_of_work)):
    try:
        async with uow:
            users_with_subscriptions = await uow.users.get_users_with_count_subscriptions()

        return users_with_subscriptions

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Не удалось пользователей с подписками {str(e)}")


@user_router.get("/get_users_with_authors_with_count_subscriptions", response_model=List[UserWithAuthorsAndSubscriptions], status_code=status.HTTP_200_OK)
async def get_users_with_authors_with_count_subscriptions(token = Depends(oauth2_scheme), uow: UnitOfWork = Depends(get_unit_of_work)):
    try:
        async with uow:
            users_with_subscriptions = await uow.users.get_users_with_authors_with_count_subcscriptions()

        return users_with_subscriptions

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Не удалось пользователей с подписками и авторами {str(e)}")