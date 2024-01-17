"""example usage"""

import uvicorn
from fastapi import FastAPI

from app import CRUD, MakeModel
from app.database.mongo import db


class User(MakeModel("create", persistent_delete=True, time_stamp=True)):
    name: str
    age: int


class UserRead(MakeModel("read", persistent_delete=True, time_stamp=True)):
    name: str
    age: int

class UserHandler(CRUD[User, UserRead, UserRead]):
    def __init__(self):
        super().__init__("testusers", UserRead)

    async def on_create(self):
        print("on_create")

    async def on_update(self):
        print("on_update")

    async def on_delete(self):
        print("on_delete")
        
user_handler = UserHandler

tapp = FastAPI()


@tapp.get("/")
async def root():
    return {"message": "Hello World"}


@tapp.post("/user")
async def create_user(user: User):
    return await user_handler.create(user, db)


@tapp.get("/user/{user_id}")
async def get_user(user_id: str):
    return (await user_handler.get_by_id(user_id, db)).model_dump()


if __name__ == "__main__":
    uvicorn.run(tapp, host="localhost", port=8000)
