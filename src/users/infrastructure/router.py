from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from src.users.domain.entities import UserEntity
from src.users.infrastructure.dependencies import get_current_user, get_user_use_cases
from src.users.infrastructure.schemas import RegisterIn, TokenOut, UserOut
from src.users.use_cases.user_use_cases import UserUseCases

router = APIRouter(tags=["auth"])
UseCases = Annotated[UserUseCases, Depends(get_user_use_cases)]


@router.post("/auth/register", response_model=UserOut, status_code=201)
async def register(body: RegisterIn, uc: UseCases):
    return UserOut.from_entity(await uc.register(**body.model_dump()))


@router.post("/auth/login", response_model=TokenOut)
async def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], uc: UseCases):
    # OAuth2 forms call the login field "username"; here it holds the email.
    return TokenOut(access_token=await uc.login(form.username, form.password))


@router.get("/users/me", response_model=UserOut)
async def me(user: Annotated[UserEntity, Depends(get_current_user)]):
    return UserOut.from_entity(user)
