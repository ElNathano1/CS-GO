import os

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, status
from pydantic import BaseModel
from database.models import get_session
from database.repository import AccountRepository
from database.account import Account

app = FastAPI(title="CS-GO User Service")


UPLOAD_DIR = "/data/uploads"  # correspond au volume Docker
os.makedirs(UPLOAD_DIR, exist_ok=True)


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
        "connected": account.is_connected,
    }


@app.get("/users")
def get_all_users(repo: AccountRepository = Depends(get_repo)):
    accounts = repo.get_all_users()
    if not accounts:
        raise HTTPException(status_code=404, detail="User not found")
    return [
        {
            "username": account.username,
            "name": account.name,
            "level": account.level,
            "friends": account.friends,
            "connected": account.is_connected,
        }
        for account in accounts
    ]


@app.post("/users/")
def create_user(user: UserCreate, repo: AccountRepository = Depends(get_repo)):
    if repo.get_by_username(user.username):
        raise HTTPException(status_code=400, detail="Username already exists")
    account = Account(username=user.username, password=user.password, name=user.name)
    repo.create(account)
    return {"status": "success", "username": user.username}


@app.post("/users/{username}/change_password")
def change_password(
    username: str,
    old_password: str,
    new_password: str,
    repo: AccountRepository = Depends(get_repo),
):
    repo.change_password(username, old_password, new_password)
    return {
        "status": "succes",
        "message": f"{username} changed password",
    }


@app.post("/users/{username}/reset_password")
def reset_password(
    username: str, new_password: str, repo: AccountRepository = Depends(get_repo)
):
    repo.reset_password(username, new_password)
    return {
        "status": "succes",
        "message": f"{username} reset password",
    }


@app.post("/users/{username}/change_name")
def change_name(
    username: str,
    new_name: str,
    repo: AccountRepository = Depends(get_repo),
):
    repo.change_name(username, new_name)
    return {
        "status": "succes",
        "message": f"{username} changed name to {new_name}",
    }


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


@app.post("/users/{username}/connect")
def connect(username: str, repo: AccountRepository = Depends(get_repo)):
    repo.connect(username)
    return {
        "status": "succes",
        "is_connected": 1,
    }


@app.post("/users/{username}/disconnect")
def disconnect(username: str, repo: AccountRepository = Depends(get_repo)):
    repo.disconnect(username)
    return {
        "status": "succes",
        "is_connected": 0,
    }


@app.get("/users/get_connected")
def get_connected(repo: AccountRepository = Depends(get_repo)):
    accounts = repo.get_connected()
    if not accounts:
        raise HTTPException(status_code=404, detail="User not found")
    return [
        {
            "username": account.username,
            "name": account.name,
            "level": account.level,
            "friends": account.friends,
            "connected": account.is_connected,
        }
        for account in accounts
    ]


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
