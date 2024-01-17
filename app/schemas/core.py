from datetime import datetime, timezone
from typing import Any, Literal, Type

from pydantic import BaseModel, Field, field_serializer

from app.schemas.mongo import FromMongo


class Timestamp(BaseModel):
    created_at: datetime = Field(default_factory= lambda: datetime.now(timezone.utc))
    updated_at: datetime | None = Field(default=None)

    @field_serializer("created_at")
    def serialize_dt(self, created_at: datetime | None, _info: Any) -> str | None:
        return created_at.isoformat() if created_at is not None else None

    @field_serializer("updated_at")
    def serialize_updated_at(self, updated_at: datetime | None, _info: Any) -> str | None:
        return updated_at.isoformat() if updated_at is not None else None


class SoftDeletion(BaseModel):
    deleted_at: datetime | None = Field(default=None)
    is_deleted: bool = False

    @field_serializer("deleted_at")
    def serialize_dates(self, deleted_at: datetime | None, _info: Any) -> str | None:
        return deleted_at.isoformat() if deleted_at is not None else None


class ModelGenerator:
    def __init__(
        self,
        type: Literal["read", "create", "update"],
        persistent_delete: bool = False,
        time_stamp: bool = True,
    ) -> None:
        self.type = type
        self.persistent_delete = persistent_delete
        self.time_stamp = time_stamp

    @staticmethod
    def make_model(
        type: Literal["read", "create", "update"],
        persistent_delete: bool = False,
        time_stamp: bool = True,
    ) -> Type[BaseModel]:
        return ModelGenerator(type, persistent_delete, time_stamp)._generate()

    def _generate(self) -> Type[BaseModel]:
        match self.type:
            case "read":
                return self.__generate_read_model()
            case "create":
                return BaseModel
            case "update":
                return BaseModel
            case _:
                raise ValueError("Invalid model type")

    def __generate_read_model(self) -> Type[BaseModel]:
        bases: list = [
            FromMongo,
        ]
        if self.persistent_delete:
            bases.append(SoftDeletion)
        if self.time_stamp:
            bases.append(Timestamp)

        class NewModel(*bases):
            pass

        return NewModel

    def __generate_create_model(self) -> None:
        pass

    def __generate_update_model(self) -> None:
        pass
