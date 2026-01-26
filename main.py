"""
CS-GO User Service (Railway branch)

This FastAPI service provides:
- Account management APIs (users, friends, levels, connection state)
- Profile picture processing (upload, convert to WebP/JPEG, thumbnails)
- File management utilities scoped to `UPLOAD_DIR`
- Realtime multiplayer support via WebSockets:
  - `/ws/lobby`: matchmaking queue by level and invitations
  - `/ws/room/{room_id}`: in-room events (moves, chat, presence)

WebSocket Protocol (JSON):
Outgoing from client:
- `client.hello`: `{ username }`
- `queue.join`: `{ level, username }`
- `queue.leave`: `{}`
- `invite.send`: `{ to }`
- `invite.accept`: `{ invite_id }`
- `invite.decline`: `{ invite_id }`
- `room.join`: `{ room_id }` (handled in room socket)
- `move.play`: `{ x, y }`
- `chat.send`: `{ message }`

Incoming from server:
- `lobby.welcome`: `{ username }`
- `queue.match_found`: `{ room_id, opponent: { username, level } }`
- `invite.received`: `{ invite_id, from }`
- `invite.sent`: `{ invite_id }`
- `invite.declined`: `{ invite_id, to? }`
- `room.joined`: `{ room_id }`
- `room.user_joined`: `{ username }`
- `room.user_left`: `{ username }`
- `move.played`: `{ x, y, from, color }`
- `chat.message`: `{ from, message }`
- `error`: `{ message }`
"""

import os
import shutil
import jwt
from datetime import datetime, timedelta
from pathlib import Path
from PIL import Image
from io import BytesIO

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, status
from fastapi.responses import FileResponse, StreamingResponse
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from database.models import get_session
from database.repository import AccountRepository
from database.account import Account
import asyncio
import json
import uuid

app = FastAPI(title="CS-GO User Service")

# JWT Secret - use environment variable in production
JWT_SECRET = os.environ.get("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24


def generate_token(username: str) -> str:
    """
    Generate a JWT token for a user.

    Args:
        username: The username to encode in the token

    Returns:
        JWT token string
    """
    payload = {
        "username": username,
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> str | None:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token string

    Returns:
        Username if token is valid, None otherwise
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("username")
    except Exception:
        return None


os.makedirs(os.environ["UPLOAD_DIR"], exist_ok=True)


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


# === Helper functions for profile pictures ===
def get_profile_pic_dir(profile_picture: str) -> str:
    """Get profile picture directory for a user"""
    upload_dir = os.environ["UPLOAD_DIR"]
    return os.path.join(upload_dir, "profiles", profile_picture)


def ensure_profile_pic_dir(username: str) -> str:
    """Ensure profile picture directory exists"""
    pic_dir = get_profile_pic_dir(username)
    os.makedirs(pic_dir, exist_ok=True)
    return pic_dir


def is_valid_image(file_bytes: bytes) -> bool:
    """Check if file is a valid image"""
    try:
        Image.open(BytesIO(file_bytes))
        return True
    except Exception:
        return False


def process_profile_picture(file_bytes: bytes, username: str) -> tuple[str, str]:
    """
    Process profile picture: convert to WebP and JPEG, create thumbnails.
    Returns (webp_path, jpeg_path)
    """
    pic_dir = ensure_profile_pic_dir(username)

    # Open and validate image
    image = Image.open(BytesIO(file_bytes)).convert("RGB")

    # Resize to 500x500 for full version
    image.thumbnail((500, 500), Image.Resampling.LANCZOS)

    # Save WebP version
    webp_path = os.path.join(pic_dir, "profile.webp")
    image.save(webp_path, "WebP", quality=85, method=6)

    # Save JPEG version (fallback)
    jpeg_path = os.path.join(pic_dir, "profile.jpg")
    image.save(jpeg_path, "JPEG", quality=85)

    # Create thumbnail (150x150)
    thumb = image.copy()
    thumb.thumbnail((150, 150), Image.Resampling.LANCZOS)

    # Save thumbnail WebP
    thumb_webp_path = os.path.join(pic_dir, "profile_thumb.webp")
    thumb.save(thumb_webp_path, "WebP", quality=80, method=6)

    # Save thumbnail JPEG
    thumb_jpeg_path = os.path.join(pic_dir, "profile_thumb.jpg")
    thumb.save(thumb_jpeg_path, "JPEG", quality=80)

    return webp_path, jpeg_path


@app.post("/auth/login")
def login(username: str, password: str, repo: AccountRepository = Depends(get_repo)):
    """
    Login endpoint - verify credentials and return JWT token.

    Args:
        username: User's username
        password: User's password (plaintext)

    Returns:
        JWT token for use in WebSocket connections
    """
    account = repo.get_by_username(username)
    if not account or not account.check_password(password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = generate_token(username)
    return {
        "status": "success",
        "username": username,
        "token": token,
        "token_type": "Bearer",
        "expires_in": TOKEN_EXPIRE_HOURS * 3600,  # seconds
    }


@app.get("/auth/verify")
def verify_auth(token: str):
    """
    Verify if a token is valid.

    Args:
        token: JWT token to verify

    Returns:
        Username if valid
    """
    username = verify_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")

    return {"status": "success", "username": username}


@app.get("/connected")
def get_connected(repo: AccountRepository = Depends(get_repo)):
    accounts = repo.get_connected()
    if not accounts:
        raise HTTPException(status_code=404, detail="No connected users found")
    return [
        {
            "username": account.username,
            "name": account.name,
            "level": account.level,
            "friends": account.friends,
            "profile_picture": account.profile_picture,
            "connected": account.is_connected,
        }
        for account in accounts
    ]


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
        "profile_picture": account.profile_picture,
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
            "profile_picture": account.profile_picture,
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


@app.post("/users/{username}/change_profile_picture")
def change_profile_picture(
    username: str,
    new_profile_picture: str,
    repo: AccountRepository = Depends(get_repo),
):
    repo.change_profile_picture(username, new_profile_picture)
    return {
        "status": "succes",
        "message": f"{username} changed profile picture to {new_profile_picture}",
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


@app.delete("/users/{username}", status_code=status.HTTP_204_NO_CONTENT)
def remove_user(
    username: str,
    repo: AccountRepository = Depends(get_repo),
):
    repo.remove_user(username)


@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    file_path = os.path.join(os.environ["UPLOAD_DIR"], file.filename)  # type: ignore
    with open(file_path, "wb") as f:
        f.write(await file.read())
    return {"filename": file.filename, "path": file_path}


# === Profile picture routes ===
@app.post("/users/{username}/profile-picture")
async def upload_profile_picture(
    username: str,
    file: UploadFile = File(...),
    repo: AccountRepository = Depends(get_repo),
):
    """Upload and process a profile picture for a user"""
    # Check user exists
    account = repo.get_by_username(username)
    if not account:
        raise HTTPException(status_code=404, detail="User not found")

    # Validate file type
    if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(
            status_code=400, detail="Only JPEG, PNG, and WebP images are allowed"
        )

    # Read file
    file_bytes = await file.read()

    # Validate image
    if not is_valid_image(file_bytes):
        raise HTTPException(status_code=400, detail="Invalid or corrupted image file")

    # Check file size (max 5MB)
    if len(file_bytes) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 5MB)")

    try:
        # Process and convert image
        webp_path, jpeg_path = process_profile_picture(file_bytes, username)

        # Store relative path in database and persist to DB
        relative_path = f"profiles/{username}/profile.webp"
        # Update the actual DB record via repository to avoid stale Account instance
        repo.change_profile_picture(username, username)
        # Keep local in-memory value in sync for this response
        account.profile_picture = username

        return {
            "status": "success",
            "message": "Profile picture uploaded successfully",
            "username": username,
            "picture_path": relative_path,
            "formats": ["webp", "jpg"],
            "sizes": {
                "full": os.path.getsize(webp_path),
                "thumbnail": os.path.getsize(
                    os.path.join(get_profile_pic_dir(username), "profile_thumb.webp")
                ),
            },
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error processing profile picture: {str(e)}"
        )


@app.get("/users/{username}/profile-picture")
async def get_profile_picture(
    username: str,
    format: str = "webp",
    repo: AccountRepository = Depends(get_repo),
):
    """Get profile picture (full size) - supports WebP and JPEG"""
    # Check user exists
    account = repo.get_by_username(username)
    if not account:
        raise HTTPException(status_code=404, detail="User not found")

    if not account.profile_picture:
        raise HTTPException(status_code=404, detail="User has no profile picture")

    pic_dir = get_profile_pic_dir(account.profile_picture)

    # Determine file format
    if format.lower() == "jpg":
        file_path = os.path.join(pic_dir, "profile.jpg")
        media_type = "image/jpeg"
    else:  # default to webp
        file_path = os.path.join(pic_dir, "profile.webp")
        media_type = "image/webp"

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Profile picture file not found")

    return FileResponse(
        path=file_path,
        media_type=media_type,
        headers={
            "Cache-Control": "private, no-store, max-age=0",
            "Pragma": "no-cache",
        },
    )


@app.get("/users/{username}/profile-picture/thumb")
async def get_profile_picture_thumb(
    username: str,
    format: str = "webp",
    repo: AccountRepository = Depends(get_repo),
):
    """Get profile picture thumbnail (150x150) - supports WebP and JPEG"""
    # Check user exists
    account = repo.get_by_username(username)
    if not account:
        raise HTTPException(status_code=404, detail="User not found")

    if not account.profile_picture:
        raise HTTPException(status_code=404, detail="User has no profile picture")

    pic_dir = get_profile_pic_dir(account.profile_picture)

    # Determine file format
    if format.lower() == "jpg":
        file_path = os.path.join(pic_dir, "profile_thumb.jpg")
        media_type = "image/jpeg"
    else:  # default to webp
        file_path = os.path.join(pic_dir, "profile_thumb.webp")
        media_type = "image/webp"

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404, detail="Profile picture thumbnail not found"
        )

    return FileResponse(
        path=file_path,
        media_type=media_type,
        headers={
            "Cache-Control": "private, no-store, max-age=0",
            "Pragma": "no-cache",
        },
    )


@app.delete("/users/{username}/profile-picture")
async def delete_profile_picture(
    username: str,
    repo: AccountRepository = Depends(get_repo),
):
    """Delete a user's profile picture"""
    # Check user exists
    account = repo.get_by_username(username)
    if not account:
        raise HTTPException(status_code=404, detail="User not found")

    if not account.profile_picture:
        raise HTTPException(status_code=404, detail="User has no profile picture")

    try:
        # Store the profile picture identifier BEFORE clearing it
        pic_identifier = account.profile_picture
        pic_dir = get_profile_pic_dir(pic_identifier)

        # Delete files from disk
        if os.path.exists(pic_dir):
            shutil.rmtree(pic_dir)

        # Only update DB if files were actually deleted
        # This ensures the DB only says "default" if the files are gone
        repo.change_profile_picture(username, "default")

        return {
            "status": "success",
            "message": f"Profile picture deleted for user '{username}'",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error deleting profile picture: {str(e)}"
        )


# === Routes de gestion des fichiers ===
@app.delete("/files/")
def delete_file(file_path: str):
    """Delete a file from UPLOAD_DIR"""
    upload_dir = os.environ["UPLOAD_DIR"]
    full_path = os.path.join(upload_dir, file_path)

    # Check that the path stays within UPLOAD_DIR (security)
    if not os.path.abspath(full_path).startswith(os.path.abspath(upload_dir)):
        raise HTTPException(status_code=400, detail="Invalid path")

    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="File not found")

    if not os.path.isfile(full_path):
        raise HTTPException(status_code=400, detail="Path does not point to a file")

    try:
        os.remove(full_path)
        return {"status": "success", "message": f"File '{file_path}' deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")


@app.post("/files/move/")
def move_file(source_path: str, destination_path: str):
    """Move a file within UPLOAD_DIR"""
    upload_dir = os.environ["UPLOAD_DIR"]
    source_full = os.path.join(upload_dir, source_path)
    destination_full = os.path.join(upload_dir, destination_path)

    # Check that paths stay within UPLOAD_DIR
    if not os.path.abspath(source_full).startswith(os.path.abspath(upload_dir)):
        raise HTTPException(status_code=400, detail="Invalid source path")
    if not os.path.abspath(destination_full).startswith(os.path.abspath(upload_dir)):
        raise HTTPException(status_code=400, detail="Invalid destination path")

    if not os.path.exists(source_full):
        raise HTTPException(status_code=404, detail="Source file not found")

    if not os.path.isfile(source_full):
        raise HTTPException(status_code=400, detail="Source path is not a file")

    if os.path.exists(destination_full):
        raise HTTPException(status_code=400, detail="Destination file already exists")

    # Create destination directory if needed
    os.makedirs(os.path.dirname(destination_full), exist_ok=True)

    try:
        shutil.move(source_full, destination_full)
        return {
            "status": "success",
            "message": f"File moved from '{source_path}' to '{destination_path}'",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error moving file: {str(e)}")


@app.post("/files/rename/")
def rename_file(file_path: str, new_name: str):
    """Rename a file in UPLOAD_DIR"""
    upload_dir = os.environ["UPLOAD_DIR"]
    full_path = os.path.join(upload_dir, file_path)

    # Check that the path stays within UPLOAD_DIR
    if not os.path.abspath(full_path).startswith(os.path.abspath(upload_dir)):
        raise HTTPException(status_code=400, detail="Invalid path")

    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="File not found")

    if not os.path.isfile(full_path):
        raise HTTPException(status_code=400, detail="Path is not a file")

    if "/" in new_name or "\\" in new_name:
        raise HTTPException(
            status_code=400, detail="New name cannot contain path separators"
        )

    directory = os.path.dirname(full_path)
    new_full_path = os.path.join(directory, new_name)

    if os.path.exists(new_full_path):
        raise HTTPException(status_code=400, detail="File with new name already exists")

    try:
        os.rename(full_path, new_full_path)
        return {
            "status": "success",
            "message": f"File renamed from '{os.path.basename(file_path)}' to '{new_name}'",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error renaming file: {str(e)}")


@app.post("/folders/")
def create_folder(folder_path: str):
    """Create a folder in UPLOAD_DIR"""
    upload_dir = os.environ["UPLOAD_DIR"]
    full_path = os.path.join(upload_dir, folder_path)

    # Check that the path stays within UPLOAD_DIR
    if not os.path.abspath(full_path).startswith(os.path.abspath(upload_dir)):
        raise HTTPException(status_code=400, detail="Invalid path")

    if os.path.exists(full_path):
        raise HTTPException(status_code=400, detail="Folder already exists")

    try:
        os.makedirs(full_path, exist_ok=False)
        return {"status": "success", "message": f"Folder '{folder_path}' created"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating folder: {str(e)}")


@app.delete("/folders/")
def delete_folder(folder_path: str):
    """Delete a folder and all its contents from UPLOAD_DIR"""
    upload_dir = os.environ["UPLOAD_DIR"]
    full_path = os.path.join(upload_dir, folder_path)

    # Check that the path stays within UPLOAD_DIR
    if not os.path.abspath(full_path).startswith(os.path.abspath(upload_dir)):
        raise HTTPException(status_code=400, detail="Invalid path")

    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="Folder not found")

    if not os.path.isdir(full_path):
        raise HTTPException(status_code=400, detail="Path is not a folder")

    try:
        shutil.rmtree(full_path)
        return {"status": "success", "message": f"Folder '{folder_path}' deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting folder: {str(e)}")


@app.post("/files/copy/")
def copy_file(source_path: str, destination_path: str):
    """Copy a file in UPLOAD_DIR"""
    upload_dir = os.environ["UPLOAD_DIR"]
    source_full = os.path.join(upload_dir, source_path)
    destination_full = os.path.join(upload_dir, destination_path)

    # Check that paths stay within UPLOAD_DIR
    if not os.path.abspath(source_full).startswith(os.path.abspath(upload_dir)):
        raise HTTPException(status_code=400, detail="Invalid source path")
    if not os.path.abspath(destination_full).startswith(os.path.abspath(upload_dir)):
        raise HTTPException(status_code=400, detail="Invalid destination path")

    if not os.path.exists(source_full):
        raise HTTPException(status_code=404, detail="Source file not found")

    if not os.path.isfile(source_full):
        raise HTTPException(status_code=400, detail="Source path is not a file")

    if os.path.exists(destination_full):
        raise HTTPException(status_code=400, detail="Destination file already exists")

    # Create destination directory if needed
    os.makedirs(os.path.dirname(destination_full), exist_ok=True)

    try:
        shutil.copy2(source_full, destination_full)
        return {
            "status": "success",
            "message": f"File copied from '{source_path}' to '{destination_path}'",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error copying file: {str(e)}")


@app.get("/files/")
def list_files(folder_path: str = ""):
    """List all files and folders in a directory"""
    upload_dir = os.environ["UPLOAD_DIR"]
    full_path = os.path.join(upload_dir, folder_path) if folder_path else upload_dir

    # Check that the path stays within UPLOAD_DIR
    if not os.path.abspath(full_path).startswith(os.path.abspath(upload_dir)):
        raise HTTPException(status_code=400, detail="Invalid path")

    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="Path not found")

    if not os.path.isdir(full_path):
        raise HTTPException(status_code=400, detail="Path is not a folder")

    try:
        items = []
        for item in os.listdir(full_path):
            item_path = os.path.join(full_path, item)
            is_dir = os.path.isdir(item_path)
            size = None if is_dir else os.path.getsize(item_path)

            items.append(
                {
                    "name": item,
                    "type": "folder" if is_dir else "file",
                    "size": size,
                    "path": os.path.join(folder_path, item) if folder_path else item,
                }
            )

        return {
            "status": "success",
            "folder": folder_path or "root",
            "items": sorted(items, key=lambda x: (x["type"] != "folder", x["name"])),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing files: {str(e)}")


@app.get("/files/info/")
def get_file_info(file_path: str):
    """Get detailed information about a file or folder"""
    upload_dir = os.environ["UPLOAD_DIR"]
    full_path = os.path.join(upload_dir, file_path)

    # Check that the path stays within UPLOAD_DIR
    if not os.path.abspath(full_path).startswith(os.path.abspath(upload_dir)):
        raise HTTPException(status_code=400, detail="Invalid path")

    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="Path not found")

    try:
        stat_info = os.stat(full_path)
        is_dir = os.path.isdir(full_path)

        info = {
            "name": os.path.basename(full_path),
            "type": "folder" if is_dir else "file",
            "path": file_path,
            "size": stat_info.st_size if not is_dir else None,
            "created": stat_info.st_ctime,
            "modified": stat_info.st_mtime,
            "is_file": not is_dir,
            "is_folder": is_dir,
        }

        if is_dir:
            info["item_count"] = len(os.listdir(full_path))

        return {"status": "success", "info": info}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting file info: {str(e)}"
        )


# =============================
# Realtime (WebSocket) endpoints
# =============================


class WSManager:
    """In-memory manager for lobby connections, matchmaking, invites and rooms.

    This is a simple implementation suitable for a single process. For
    production scaling, consider using a shared store (Redis) for state.
    """

    def __init__(self) -> None:
        self.lock = asyncio.Lock()
        self.lobby_clients: dict[str, WebSocket] = {}
        self.client_levels: dict[str, int] = {}
        self.queue: list[str] = []
        self.invites: dict[str, dict] = {}
        self.rooms: dict[str, set[WebSocket]] = {}
        self.room_users: dict[str, set[str]] = {}
        self.room_colors: dict[str, dict[str, int]] = {}  # Goban.BLACK=1, WHITE=2

    async def send(self, ws: WebSocket, obj: dict) -> None:
        await ws.send_text(json.dumps(obj))

    async def broadcast_room(
        self, room_id: str, sender: WebSocket | None, obj: dict
    ) -> None:
        if room_id not in self.rooms:
            return
        payload = json.dumps(obj)
        for ws in list(self.rooms[room_id]):
            if sender is not None and ws is sender:
                continue
            try:
                await ws.send_text(payload)
            except Exception:
                # best effort
                pass


ws_manager = WSManager()


def extract_token(ws: WebSocket) -> str | None:
    """
    Extract Bearer token from WebSocket headers.

    Expected format: "Authorization: Bearer <token>"

    Args:
        ws: WebSocket connection object

    Returns:
        Token string if valid Bearer format, None otherwise
    """
    try:
        auth_header = ws.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        return auth_header[7:]  # strip "Bearer "
    except Exception:
        return None


@app.websocket("/ws/health")
async def ws_health(ws: WebSocket):
    """
    Simple WebSocket health check and echo endpoint (no auth required).

    Use this for diagnostics and to verify WebSocket connectivity without
    authentication overhead. Client sends any JSON message; server echoes
    it back with `type: "health.echo"`.

    Example:
        Send: {"message": "ping"}
        Recv: {"type": "health.echo", "payload": {"message": "ping"}}
    """
    await ws.accept()
    try:
        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_text(
                    json.dumps(
                        {"type": "error", "payload": {"message": "invalid-json"}}
                    )
                )
                continue
            await ws.send_text(json.dumps({"type": "health.echo", "payload": data}))
    except WebSocketDisconnect:
        pass


@app.websocket("/ws/lobby")
async def ws_lobby(ws: WebSocket):
    """
    WebSocket lobby endpoint.

    Authentication: Requires `Authorization: Bearer <token>` header.
    If missing or invalid, connection is rejected.

    Responsibilities:
    - Accept `client.hello { username }`
    - Handle matchmaking via `queue.join { level }` and `queue.leave`
    - Handle social invitations: `invite.send`, `invite.accept`, `invite.decline`
    - Emit `queue.match_found { room_id, opponent }` when a match is ready

    Messages are JSON objects with `type` and `payload` fields.
    """
    # Validate auth token
    token = extract_token(ws)
    if not token:
        await ws.close(code=1008, reason="unauthorized")
        return

    await ws.accept()
    username: str | None = None

    try:
        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_text(
                    json.dumps(
                        {"type": "error", "payload": {"message": "invalid-json"}}
                    )
                )
                continue

            msg_type = data.get("type")
            payload = data.get("payload", {})

            # Identify client
            if msg_type == "client.hello":
                username = str(payload.get("username"))
                if not username:
                    await ws_manager.send(
                        ws,
                        {"type": "error", "payload": {"message": "username-required"}},
                    )
                    continue
                async with ws_manager.lock:
                    ws_manager.lobby_clients[username] = ws
                await ws_manager.send(
                    ws, {"type": "lobby.welcome", "payload": {"username": username}}
                )
                continue

            if username is None:
                await ws_manager.send(
                    ws, {"type": "error", "payload": {"message": "hello-first"}}
                )
                continue

            # Queue join/leave
            if msg_type == "queue.join":
                level = int(payload.get("level", 0))
                async with ws_manager.lock:
                    ws_manager.client_levels[username] = level
                    if username not in ws_manager.queue:
                        ws_manager.queue.append(username)

                    # Try to find the closest level opponent
                    opponent: str | None = None
                    best_diff = 1_000_000
                    for other in ws_manager.queue:
                        if other == username:
                            continue
                        diff = abs(level - ws_manager.client_levels.get(other, level))
                        if diff < best_diff:
                            best_diff = diff
                            opponent = other

                    if opponent:
                        # Create room
                        room_id = uuid.uuid4().hex
                        # Remove from queue
                        ws_manager.queue = [
                            u for u in ws_manager.queue if u not in (username, opponent)
                        ]
                        # Notify both
                        opp_ws = ws_manager.lobby_clients.get(opponent)
                        await ws_manager.send(
                            ws,
                            {
                                "type": "queue.match_found",
                                "payload": {
                                    "room_id": room_id,
                                    "opponent": {
                                        "username": opponent,
                                        "level": ws_manager.client_levels.get(opponent),
                                    },
                                },
                            },
                        )
                        if opp_ws:
                            await ws_manager.send(
                                opp_ws,
                                {
                                    "type": "queue.match_found",
                                    "payload": {
                                        "room_id": room_id,
                                        "opponent": {
                                            "username": username,
                                            "level": level,
                                        },
                                    },
                                },
                            )

                        # Assign colors deterministically
                        ws_manager.room_colors[room_id] = {username: 1, opponent: 2}
                        ws_manager.room_users[room_id] = {username, opponent}
                continue

            if msg_type == "queue.leave":
                async with ws_manager.lock:
                    ws_manager.queue = [u for u in ws_manager.queue if u != username]
                await ws_manager.send(ws, {"type": "queue.left", "payload": {}})
                continue

            # Invitations
            if msg_type == "invite.send":
                to_user = payload.get("to")
                if not to_user:
                    await ws_manager.send(
                        ws, {"type": "error", "payload": {"message": "to-required"}}
                    )
                    continue
                invite_id = uuid.uuid4().hex
                async with ws_manager.lock:
                    ws_manager.invites[invite_id] = {"from": username, "to": to_user}
                to_ws = ws_manager.lobby_clients.get(str(to_user))
                if to_ws:
                    await ws_manager.send(
                        to_ws,
                        {
                            "type": "invite.received",
                            "payload": {"invite_id": invite_id, "from": username},
                        },
                    )
                    await ws_manager.send(
                        ws, {"type": "invite.sent", "payload": {"invite_id": invite_id}}
                    )
                else:
                    await ws_manager.send(
                        ws, {"type": "error", "payload": {"message": "user-offline"}}
                    )
                continue

            if msg_type == "invite.accept":
                invite_id = payload.get("invite_id")
                async with ws_manager.lock:
                    invite = ws_manager.invites.pop(str(invite_id), None)
                if not invite or invite.get("to") != username:
                    await ws_manager.send(
                        ws, {"type": "error", "payload": {"message": "invalid-invite"}}
                    )
                    continue
                room_id = uuid.uuid4().hex
                inviter = str(invite.get("from"))
                inviter_ws = ws_manager.lobby_clients.get(inviter)
                # Assign colors deterministically
                ws_manager.room_colors[room_id] = {inviter: 1, username: 2}
                ws_manager.room_users[room_id] = {inviter, username}
                await ws_manager.send(
                    ws,
                    {
                        "type": "queue.match_found",
                        "payload": {
                            "room_id": room_id,
                            "opponent": {"username": inviter},
                        },
                    },
                )
                if inviter_ws:
                    await ws_manager.send(
                        inviter_ws,
                        {
                            "type": "queue.match_found",
                            "payload": {
                                "room_id": room_id,
                                "opponent": {"username": username},
                            },
                        },
                    )
                continue

            if msg_type == "invite.decline":
                invite_id = payload.get("invite_id")
                async with ws_manager.lock:
                    invite = ws_manager.invites.pop(str(invite_id), None)
                if invite:
                    inviter = str(invite.get("from"))
                    inviter_ws = ws_manager.lobby_clients.get(inviter)
                    if inviter_ws:
                        await ws_manager.send(
                            inviter_ws,
                            {
                                "type": "invite.declined",
                                "payload": {
                                    "invite_id": str(invite_id),
                                    "to": username,
                                },
                            },
                        )
                await ws_manager.send(
                    ws,
                    {
                        "type": "invite.declined",
                        "payload": {"invite_id": str(invite_id)},
                    },
                )
                continue

            # Default: unknown message
            await ws_manager.send(
                ws,
                {
                    "type": "error",
                    "payload": {"message": "unknown-message", "received": msg_type},
                },
            )

    except WebSocketDisconnect:
        # Cleanup on disconnect
        async with ws_manager.lock:
            if username:
                ws_manager.lobby_clients.pop(username, None)
                ws_manager.client_levels.pop(username, None)
                ws_manager.queue = [u for u in ws_manager.queue if u != username]


@app.websocket("/ws/room/{room_id}")
async def ws_room(ws: WebSocket, room_id: str):
    """
    WebSocket room endpoint.

    Authentication: Requires `Authorization: Bearer <token>` header.
    If missing or invalid, connection is rejected.

    Responsibilities:
    - Accept `client.hello { username }` and join user to room
    - Broadcast `room.user_joined` and `room.user_left`
    - Relay `move.play { x, y }` as `move.played { x, y, from, color }`
    - Relay `chat.send { message }` as `chat.message { from, message }`

    Rooms are created on demand and kept in memory.
    """
    # Validate auth token
    token = extract_token(ws)
    if not token:
        await ws.close(code=1008, reason="unauthorized")
        return

    await ws.accept()
    username: str | None = None

    # Create room on demand
    async with ws_manager.lock:
        ws_manager.rooms.setdefault(room_id, set())
        ws_manager.room_users.setdefault(room_id, set())
        ws_manager.room_colors.setdefault(room_id, {})

    try:
        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_text(
                    json.dumps(
                        {"type": "error", "payload": {"message": "invalid-json"}}
                    )
                )
                continue

            msg_type = data.get("type")
            payload = data.get("payload", {})

            if msg_type == "client.hello":
                username = str(payload.get("username"))
                async with ws_manager.lock:
                    ws_manager.rooms[room_id].add(ws)
                    ws_manager.room_users[room_id].add(username)
                await ws_manager.send(
                    ws, {"type": "room.joined", "payload": {"room_id": room_id}}
                )
                # Broadcast presence
                await ws_manager.broadcast_room(
                    room_id,
                    sender=ws,
                    obj={"type": "room.user_joined", "payload": {"username": username}},
                )
                continue

            if username is None:
                await ws_manager.send(
                    ws, {"type": "error", "payload": {"message": "hello-first"}}
                )
                continue

            if msg_type == "move.play":
                x = int(payload.get("x", -1))
                y = int(payload.get("y", -1))
                color = ws_manager.room_colors.get(room_id, {}).get(username)
                await ws_manager.broadcast_room(
                    room_id,
                    sender=ws,
                    obj={
                        "type": "move.played",
                        "payload": {"x": x, "y": y, "from": username, "color": color},
                    },
                )
                continue

            if msg_type == "chat.send":
                message = str(payload.get("message", ""))
                await ws_manager.broadcast_room(
                    room_id,
                    sender=None,
                    obj={
                        "type": "chat.message",
                        "payload": {"from": username, "message": message},
                    },
                )
                continue

            if msg_type == "room.leave":
                async with ws_manager.lock:
                    if room_id in ws_manager.rooms and ws in ws_manager.rooms[room_id]:
                        ws_manager.rooms[room_id].remove(ws)
                await ws_manager.send(
                    ws, {"type": "room.left", "payload": {"room_id": room_id}}
                )
                break

            await ws_manager.send(
                ws,
                {
                    "type": "error",
                    "payload": {"message": "unknown-message", "received": msg_type},
                },
            )

    except WebSocketDisconnect:
        async with ws_manager.lock:
            if room_id in ws_manager.rooms and ws in ws_manager.rooms[room_id]:
                ws_manager.rooms[room_id].remove(ws)
        # Broadcast user left if we know the username
        if username:
            await ws_manager.broadcast_room(
                room_id,
                sender=None,
                obj={"type": "room.user_left", "payload": {"username": username}},
            )
