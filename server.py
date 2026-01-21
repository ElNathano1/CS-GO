from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from database.models import get_session
from database.repository import AccountRepository
from database.account import Account

app = FastAPI(title="CS-GO User Service")


# === Schemas Pydantic pour validation ===
class UserCreate(BaseModel):
    username: str
    password: str
    name: str


class FriendAction(BaseModel):
    friend_username: str


class LevelUpdate(BaseModel):
    new_level: int


# === Routes ===
@app.get("/users/{username}")
def get_user(username: str):
    session = get_session()
    repo = AccountRepository(session)
    account = repo.get_by_username(username)
    if not account:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "username": account.username,
        "name": account.name,
        "level": account.level,
        "friends": account.friends,
    }


@app.post("/users/")
def create_user(user: UserCreate):
    session = get_session()
    repo = AccountRepository(session)
    if repo.get_by_username(user.username):
        raise HTTPException(status_code=400, detail="Username already exists")
    account = Account(username=user.username, password=user.password, name=user.name)
    repo.create(account)
    return {"status": "success", "username": user.username}


@app.post("/users/{username}/add_friend")
def add_friend(username: str, action: FriendAction):
    session = get_session()
    repo = AccountRepository(session)
    repo.add_friend(username, action.friend_username)
    return {
        "status": "success",
        "message": f"{action.friend_username} added to {username}",
    }


@app.post("/users/{username}/remove_friend")
def remove_friend(username: str, action: FriendAction):
    session = get_session()
    repo = AccountRepository(session)
    repo.remove_friend(username, action.friend_username)
    return {
        "status": "success",
        "message": f"{action.friend_username} removed from {username}",
    }


@app.post("/users/{username}/update_level")
def update_level(username: str, level_update: LevelUpdate):
    session = get_session()
    repo = AccountRepository(session)
    repo.update_level(username, level_update.new_level)
    return {
        "status": "success",
        "username": username,
        "new_level": level_update.new_level,
    }
