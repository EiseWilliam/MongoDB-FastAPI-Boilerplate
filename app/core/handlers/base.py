from datetime import datetime, timezone
from typing import Any, Generic, List, Type, TypeVar

from bson import ObjectId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from app.local_typing import AgnosticCursor, DBDeleteResult, DBInsertOneResult, DBUpdateResult, DBInsertManyResult

CreateSchema = TypeVar("CreateSchema", bound=BaseModel)
ReadSchema = TypeVar("ReadSchema", bound=BaseModel)
UpdateSchema = TypeVar("UpdateSchema", bound=BaseModel)


class BaseCRUD(Generic[CreateSchema, ReadSchema, UpdateSchema]):
    def __init__(
        self,
        collection: str,
        read_model: Type[ReadSchema],
        make_time_stamps: bool = True,
        soft_delete: bool = False,
    ):
        self._collection = collection
        self._read_model = read_model
        self._make_time_stamps = make_time_stamps
        self._soft_delete = soft_delete

    async def on_create(self) -> None:
        pass

    async def on_update(self) -> None:
        pass

    async def on_delete(self) -> None:
        pass

    async def id_exists(self, id: str, db: AsyncIOMotorDatabase) -> bool:
        item = await db.get_collection(self._collection).find_one({"_id": ObjectId(id)})
        return item is not None

    async def find_and_is_soft_deleted(self, id: str, db: AsyncIOMotorDatabase) -> bool:
        """
        Find an item by its ID in the database and check if it is marked as soft deleted.

        Args:
            id (str): The ID of the item to find.
            db (AsyncIOMotorDatabase): The database to search in.

        Returns:
            bool: True if the item is marked as soft deleted, False otherwise.

        Raises:
            HTTPException: If the item with the given ID is not found.
        """
        item: dict = await db.get_collection(self._collection).find_one({"_id": ObjectId(id)})
        if item is None:
            raise HTTPException(status_code=404, detail="Item with {id} not found")
        return item.get("is_deleted", False)
        
    
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
    
    async def create_many(self, items: list[CreateSchema], db: AsyncIOMotorDatabase, **defaults_fields: Any) -> list[str]:
        items_updated = [item.model_dump() for item in items]
        if defaults_fields:
            items_updated = [{**item, **defaults_fields} for item in items_updated]
        result = await self._create_many(items_updated, db)
        await self.on_create()
        return [str(id) for id in result.inserted_ids]

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

    # Would invoke time stamps if enabled
    async def _create(self, item_dict: dict[str, Any], db: AsyncIOMotorDatabase) -> DBInsertOneResult:
        if self._make_time_stamps:
            item_dict["created_at"] = item_dict["updated_at"] = datetime.now(timezone.utc)
        return await self.__create(item_dict, db)
    
    async def _create_many(self, items_dict: list[dict[str, Any]], db: AsyncIOMotorDatabase) -> DBInsertManyResult:
        if self._make_time_stamps:
            for item_dict in items_dict:
                item_dict["created_at"] = item_dict["updated_at"] = datetime.now(timezone.utc)
        return await db.get_collection(self._collection).insert_many(items_dict)

    async def _update(self, id: str, item_dict: dict[str, Any], db: AsyncIOMotorDatabase) -> DBUpdateResult:
        if self._make_time_stamps:
            item_dict["updated_at"] = datetime.now(timezone.utc)
        return await self.__update(id, item_dict, db)

    async def _delete(self, id: str, db: AsyncIOMotorDatabase) -> DBDeleteResult | DBUpdateResult:
        """
        Deletes a document from the collection based on the provided ID.

        Args:
            id (str): The ID of the document to be deleted.
            db (AsyncIOMotorDatabase): The database connection.

        Returns:
            DBDeleteResult | DBUpdateResult: The result of the delete operation.
        """
        if self.find_and_is_soft_deleted(id, db):
            return await db.get_collection(self._collection).delete_one({"_id": ObjectId(id)})
        if self._soft_delete:
            update_fields: dict[str,Any] = {"deleted": True}
            if self._make_time_stamps:
                update_fields["updated_at"] = datetime.now(timezone.utc)
            return await db.get_collection(self._collection).update_one(
                {"_id": ObjectId(id)},
                {"$set": update_fields},
            )
        return await db.get_collection(self._collection).delete_one({"_id": ObjectId(id)})
    
    
    # Won't invoke time stamps no matter what
    #  This is for internal use only, only use to avoid functions triggered by events a
    async def __create(self, item_dict: dict[str, Any], db: AsyncIOMotorDatabase) -> DBInsertOneResult:
        return await db.get_collection(self._collection).insert_one(item_dict)
    
    async def __update(self, id: str, item_dict: dict[str, Any], db: AsyncIOMotorDatabase) -> DBUpdateResult:
        return await db.get_collection(self._collection).update_one(
            {"_id": ObjectId(id)}, {"$set": item_dict}
        )
        
    
