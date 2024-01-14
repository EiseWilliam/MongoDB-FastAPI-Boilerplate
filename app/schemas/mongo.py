from typing import Any
from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field, field_serializer, validator


class FromMongo(BaseModel):
    id: str | ObjectId = Field(alias="_id")
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="ignore")
    
    @validator('id', pre=True)
    def validate_id(cls, id: str | ObjectId) -> str:
        if isinstance(id, ObjectId):
            return str(id)
        return id
    
    # @field_serializer('id')
    # def serialize_id(self, id: str | ObjectId) -> str:
    #     if isinstance(id, ObjectId):
    #         return str(id)
    #     return id