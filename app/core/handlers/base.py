from typing import Any, Generic, List, Type, TypeVar

from bson import ObjectId
from fastapi import HTTPException
from local_typing import AgnosticCursor, DeleteResult, InsertOneResult, UpdateResult
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

CreateSchema = TypeVar("CreateSchema", bound=BaseModel)
ReadSchema = TypeVar("ReadSchema", bound=BaseModel)
UpdateSchema = TypeVar("UpdateSchema", bound=BaseModel)


class BaseCRUD(Generic[CreateSchema, ReadSchema, UpdateSchema]):
    def __init__(
        self,
        collection: str,
        read_model: Type[ReadSchema],
    ):
        self._collection = collection
        self._read_model = read_model

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
        return await db.get_collection(self._collection).count_documents({})

    async def get_multiple(
        self, db: AsyncIOMotorDatabase, sort_by: str | None = None, n=100, **filters
    ) -> List:
        items_cursor: AgnosticCursor = db.get_collection(self._collection).find(filters)
        if sort_by:
            items_cursor = items_cursor.sort(sort_by)
        items_cursor = items_cursor.limit(n)
        items: list = await items_cursor.to_list(n)
        return items

    async def get_by_id(self, id: str, db: AsyncIOMotorDatabase) -> ReadSchema:
        item = await db.get_collection(self._collection).find_one({"_id": ObjectId(id)})
        if item is None:
            raise HTTPException(status_code=404, detail="Item with {id} not found")
        return self._read_model(**item)

    async def create(self, item: CreateSchema, db: AsyncIOMotorDatabase, **defaults_fields: Any) -> str:
        item_updated = item.model_dump()
        if defaults_fields:
            item_updated.update(defaults_fields)
        result = await self._create(item_updated, db)
        await self.on_create()
        return str(result.inserted_id)  # type: ignore

    async def update(self, id: str, item: UpdateSchema, db: AsyncIOMotorDatabase) -> bool:
        if await self.id_exists(id, db):
            result = await self._update(
                id, item.model_dump(exclude_none=True, exclude_defaults=True, exclude_unset=True), db
            )
            await self.on_update()
            return result.acknowledged
        else:
            return False

    async def delete(self, id: str, db: AsyncIOMotorDatabase) -> bool:
        if await self.id_exists(id, db):
            result = await self._delete(id, db)
            await self.on_delete()
            return result.acknowledged
        else:
            return False

    async def _create(self, item_dict: dict[str, Any], db: AsyncIOMotorDatabase) -> InsertOneResult:
        return await db.get_collection(self._collection).insert_one(item_dict)

    async def _update(self, id: str, item_dict: dict[str, Any], db: AsyncIOMotorDatabase) -> UpdateResult:
        return await db.get_collection(self._collection).update_one({"_id": ObjectId(id)}, {"$set": item_dict})

    async def _delete(self, id: str, db: AsyncIOMotorDatabase) -> DeleteResult:
        return await db.get_collection(self._collection).delete_one({"_id": ObjectId(id)})
