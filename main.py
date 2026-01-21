import os

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, status
from pydantic import BaseModel
from database.models import get_session
from database.repository import AccountRepository
from database.account import Account

app = FastAPI(title="CS-GO User Service")


UPLOAD_DIR = "/data/uploads"  # correspond au volume Docker


def get_repo():
    session = get_session()
    try:
        yield AccountRepository(session)
    finally:
        session.close()


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
@app.get("/")
def root():
    return {"message": "Hello from Railway!"}


@app.get("/users/{username}")
def get_user(username: str, repo: AccountRepository = Depends(get_repo)):
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
def create_user(user: UserCreate, repo: AccountRepository = Depends(get_repo)):
    if repo.get_by_username(user.username):
        raise HTTPException(status_code=400, detail="Username already exists")
    account = Account(username=user.username, password=user.password, name=user.name)
    repo.create(account)
    return {"status": "success", "username": user.username}


@app.post("/users/{username}/add_friend")
def add_friend(
    username: str, action: FriendAction, repo: AccountRepository = Depends(get_repo)
):
    repo.add_friend(username, action.friend_username)
    return {
        "status": "success",
        "message": f"{action.friend_username} added to {username}",
    }


@app.post("/users/{username}/remove_friend")
def remove_friend(
    username: str, action: FriendAction, repo: AccountRepository = Depends(get_repo)
):
    repo.remove_friend(username, action.friend_username)
    return {
        "status": "success",
        "message": f"{action.friend_username} removed from {username}",
    }


@app.post("/users/{username}/update_level")
def update_level(
    username: str,
    level_update: LevelUpdate,
    repo: AccountRepository = Depends(get_repo),
):
    repo.update_level(username, level_update.new_level)
    return {
        "status": "success",
        "username": username,
        "new_level": level_update.new_level,
    }


@app.delete("/users/{username}", status_code=status.HTTP_204_NO_CONTENT)
def remove_user(
    username: str,
    repo: AccountRepository = Depends(get_repo),
):
    repo.remove_user(username)


@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)  # type: ignore
    with open(file_path, "wb") as f:
        f.write(await file.read())
    return {"filename": file.filename, "path": file_path}
