from typing import Any

from fastapi import HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import EmailStr

from app.core.config import config
from app.core.messenger import send_verification_email
from app.schema.user_schema import (
    CreateUser,
    CreateUserInternal,
    PrivateReadUser,
    ReadUser,
    UpdateUser,
    UpdateUserInternal,
)
from app.security import user_auth as security
from app.services.base import BaseCRUD

# Consts
VERIFICATION_TOKEN_AUDIENCE = config.VERIFICATION_TOKEN_AUDIENCE


class UserHandler(BaseCRUD[CreateUserInternal, ReadUser, UpdateUser | UpdateUserInternal]):
    async def email_exists(self, email: EmailStr, db: AsyncIOMotorDatabase) -> bool:
        item = await db[self._collection].find_one({"email": email})
        return item is not None

    async def get_by_email(self, email: str, db: AsyncIOMotorDatabase) -> ReadUser | None:
        item = await db[self._collection].find_one({"email": email})
        if item:
            return ReadUser(**item)

    async def private_get_by_email(self, email: str, db: AsyncIOMotorDatabase) -> PrivateReadUser | None:
        item = await db[self._collection].find_one({"email": email})
        if item:
            return PrivateReadUser(**item)

    def handle_password(self, user: CreateUser) -> CreateUserInternal:
        user.password = security.hash_password(user.password)
        del user.confirm_password
        return user

    async def register_user(self, user: CreateUser, db: AsyncIOMotorDatabase) -> Any:
        if await self.email_exists(user.email, db):
            raise HTTPException(status_code=409, detail="EMAIL_ALREADY_REGISTERED")
        user_to_db = self.handle_password(user)
        user_in_db = await self.create(
            user_to_db,
            db,
            {"is_verified": False, "role": "client", "status": "active", "updated_at": None},
        )
        return user_in_db

    async def authenticate_user(self, email: str, password: str, db: AsyncIOMotorDatabase) -> Any:
        user = await self.private_get_by_email(email, db)
        if not user:
            return None
        if not await security.verify_password(password, user.password):
            return None

        created_token = security.create_access_token({"sub": str(user.id), "email": user.email})
        return created_token

    # verification
    async def request_email_verification(self, user: ReadUser, request: Request) -> None:
        if not user:
            return None
        if user.is_verified:
            return None
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "aud": VERIFICATION_TOKEN_AUDIENCE,
        }
        verification_code = await security.create_verification_code(token_data)
        await self.after_request_verification(user, verification_code, request)

    async def verify_email(
        self, verification_code: str, db: AsyncIOMotorDatabase, request: Request | None = None
    ) -> bool | None:
        payload = await security.decode_verification_code(verification_code, VERIFICATION_TOKEN_AUDIENCE)
        user = await self.get_by_id(payload["sub"], db)
        if not user:
            raise HTTPException(status_code=404, detail="USER_NOT_FOUND")
        if user["is_verified"]:
            raise HTTPException(status_code=400, detail="USER_ALREADY_VERIFIED")
        user_dict = {"is_verified": True}
        await self._update(payload["sub"], user_dict, db)
        await self.after_verification(payload, request)
        return True

    # <--------   Triggered by events ----------->
    async def after_request_verification(
        self, user: ReadUser, verification_code: str, request: Request
    ) -> None:
        sent = await send_verification_email(user.email, verification_code, request)
        if sent is True:
            pass
        else:
            raise HTTPException(status_code=500, detail="EMAIL_NOT_SENT")

    async def after_verification(self, user: dict, request: Request | None = None) -> None:
        print(user["email"], " has been verified")

