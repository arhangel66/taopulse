from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel

# База данных пользователей для примера
fake_users_db = {
    "admin": {
        "username": "admin",
        "full_name": "Administrator",
        "email": "admin@taopulse.com",
        "hashed_password": "fakehashednewsecret",
        "disabled": False,
    },
    "user": {
        "username": "user",
        "full_name": "Regular User",
        "email": "user@taopulse.com",
        "hashed_password": "fakehasheddemo",
        "disabled": False,
    },
}

# OAuth2 с простой схемой Bearer token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/token")


class User(BaseModel):
    """Базовая модель пользователя"""
    username: str
    email: str | None = None
    full_name: str | None = None
    disabled: bool | None = None


class UserInDB(User):
    """Модель пользователя с хэшем пароля"""
    hashed_password: str


def fake_hash_password(password: str):
    """Имитация хэширования пароля"""
    return "fakehashed" + password


def get_user(db, username: str):
    """Получение пользователя из базы данных"""
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)
    return None


def fake_decode_token(token):
    """Имитация декодирования токена"""
    user = get_user(fake_users_db, token)
    return user


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    """Получение текущего пользователя из токена"""
    user = fake_decode_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_active_user(current_user: Annotated[User, Depends(get_current_user)]):
    """Проверка, что пользователь активен"""
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
