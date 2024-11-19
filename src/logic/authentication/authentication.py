from typing import Optional

from datetime import datetime, timedelta
from passlib.context import CryptContext
import jwt

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer

from src.infra.database.uow import UnitOfWork, get_unit_of_work
from src.settings.config import jwt_algorithm, access_token_expire_minutes, refresh_token_expire_days, secret_key, refresh_secret_key

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_token_from_header(request: Request):
    auth_header = request.headers.get("Authorization")
    if auth_header is None or not auth_header.startswith("Bearer"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не удалось найти токен"
        )
    token = auth_header[len("Bearer "):]
    return token


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=access_token_expire_minutes)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, key=secret_key, algorithm=jwt_algorithm)

    return encoded_jwt


def refresh_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=refresh_token_expire_days)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, key=refresh_secret_key, algorithm=jwt_algorithm)

    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme), uow: UnitOfWork = Depends(get_unit_of_work)):
    credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не получилось провалидировать результат",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = jwt.decode(token, key=secret_key, algorithms=[jwt_algorithm])
    username = payload.get("sub")
    user_tag = payload.get("user_tag")

    if username is None or user_tag is None:
        raise credentials_exception

    user = await uow.users.get_user(username=username, user_tag=user_tag)

    if user is None:
        raise credentials_exception

    return user

def verify_password(input_tag: str, stored_tag: str):
    return input_tag == stored_tag

def get_password_hash(password: str):
    return pwd_context.hash(password)