from datetime import datetime
from typing import Any, Generic, List, TypeVar

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

CreateSchema = TypeVar("CreateSchema", bound=BaseModel)
ReadSchema = TypeVar("ReadSchema", bound=BaseModel)
UpdateSchema = TypeVar("UpdateSchema", bound=BaseModel)


class BaseCRUD(Generic[CreateSchema, ReadSchema, UpdateSchema]):
    def __init__(
        self,
        collection: str,
    ):
        self._collection = collection

    async def on_create(self) -> None:
        print("user created")

    async def on_update(self) -> None:
        print("user updated")

    async def on_delete(self) -> None:
        print("user deleted")

    async def id_exists(self, id: str, db: AsyncIOMotorDatabase) -> bool:
        item = await db[self._collection].find_one({"_id": ObjectId(id)})
        return item is not None

    async def count(self, db: AsyncIOMotorDatabase) -> int:
        count = await db[self._collection].count_documents({})
        return count

    async def get_n(self, db: AsyncIOMotorDatabase, n=1000) -> List:
        items = await db[self._collection].find().to_list(n)
        return items

    async def get_by_id(self, id: str, db: AsyncIOMotorDatabase) -> dict | None:
        item = await db[self._collection].find_one({"_id": ObjectId(id)})
        return item

    async def create(
        self, item: CreateSchema, db: AsyncIOMotorDatabase, defaults: dict[str, Any] | None
    ) -> ReadSchema:
        item_updated = item.model_dump()
        if defaults:
            item_updated.update(defaults)
        item_in_db = await self._create(item_updated, db)
        await self.on_create()
        return item_in_db  # type: ignore

    async def update(self, id: str, item: UpdateSchema, db: AsyncIOMotorDatabase) -> dict | None:
        result = await self._update(
            id, item.model_dump(exclude_none=True, exclude_defaults=True, exclude_unset=True), db
        )
        await self.on_update()
        return result

    async def delete(self, id: str, db: AsyncIOMotorDatabase) -> dict | None:
        result = await self._delete(id, db)
        await self.on_delete()
        return result

    async def _create(self, item_dict: dict[str, Any], db: AsyncIOMotorDatabase) -> dict | None:
        item_dict["created_at"] = datetime.utcnow()
        inserted = await db[self._collection].insert_one(item_dict)
        item_in_db = await db[self._collection].find_one({"_id": inserted.inserted_id})
        return item_in_db

    async def _update(self, id: str, item_dict: dict[str, Any], db: AsyncIOMotorDatabase) -> Any:
        item_dict["updated_at"] = datetime.utcnow()
        result = await db[self._collection].update_one({"_id": ObjectId(id)}, {"$set": item_dict})
        return result

    async def _delete(self, id: str, db: AsyncIOMotorDatabase) -> Any:
        if self.id_exists(id, db):
            result = await db[self._collection].delete_one({"_id": ObjectId(id)})
            return result
