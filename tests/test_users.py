import pytest

from src.core.errors import (
    DuplicateError,
    ForbiddenError,
    InvalidDataError,
    UnauthorizedError,
)
from src.users.use_cases.user_use_cases import UserUseCases
from tests.fakes import FakeHasher, FakeTokens, FakeUow, FakeUserRepo


def make_uc(allow_registration=False):
    return UserUseCases(
        FakeUserRepo(), FakeHasher(), FakeTokens(), FakeUow(), allow_registration
    )


async def _first_user(uc):
    return await uc.register("Me@Example.com ", "Me", "secret-pass")


async def test_register_normalizes_email_and_never_stores_the_plain_password():
    uc = make_uc()
    user = await _first_user(uc)
    assert user.email == "me@example.com"
    assert user.password_hash != "secret-pass"


async def test_only_the_first_account_is_open_unless_registration_is_enabled():
    closed = make_uc(allow_registration=False)
    await _first_user(closed)
    with pytest.raises(ForbiddenError):
        await closed.register("two@example.com", "Two", "secret-pass")

    open_ = make_uc(allow_registration=True)
    await _first_user(open_)
    await open_.register("two@example.com", "Two", "secret-pass")


async def test_duplicate_email_and_bad_input_are_rejected():
    uc = make_uc(allow_registration=True)
    await _first_user(uc)
    with pytest.raises(DuplicateError):
        await uc.register("me@example.com", "Again", "secret-pass")
    with pytest.raises(InvalidDataError):
        await uc.register("not-an-email", "X", "secret-pass")
    with pytest.raises(InvalidDataError):
        await uc.register("x@example.com", "X", "short")
    with pytest.raises(InvalidDataError):
        await uc.register("x@example.com", "   ", "secret-pass")


async def test_login_returns_a_token_that_identifies_the_user():
    uc = make_uc()
    user = await _first_user(uc)
    token = await uc.login("ME@example.com", "secret-pass")
    assert (await uc.authenticate(token)).id == user.id


async def test_wrong_password_or_unknown_email_look_the_same():
    uc = make_uc()
    await _first_user(uc)
    for email, password in [("me@example.com", "wrong"), ("who@example.com", "x")]:
        with pytest.raises(UnauthorizedError, match="Invalid email or password"):
            await uc.login(email, password)


async def test_garbage_token_and_inactive_user_are_rejected():
    uc = make_uc()
    user = await _first_user(uc)
    with pytest.raises(UnauthorizedError):
        await uc.authenticate("garbage")
    token = await uc.login("me@example.com", "secret-pass")
    user.is_active = False
    with pytest.raises(UnauthorizedError):
        await uc.authenticate(token)
    with pytest.raises(UnauthorizedError):
        await uc.login("me@example.com", "secret-pass")
