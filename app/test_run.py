import asyncio

from database.mongo import db
from schemas.core import Timestamp
from schemas.mongo import FromMongo


class PersontoDB(Timestamp):
    name: str
    age: int


class Person(FromMongo):
    name: str
    age: int


jane = PersontoDB(name="Jane", age=25)


print(jane.model_dump())


async def insert_person():
    return await db.persons.insert_one(jane.model_dump())


async def get_person():
    out = await db.persons.find_one({"name": "Jane"})
    return Person(**out)


print(asyncio.run(insert_person()))
print(asyncio.run(get_person()))
