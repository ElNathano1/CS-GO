# CS-GO User Service (Railway Branch)

FastAPI service for account management, messaging, profile pictures, file utilities, and realtime multiplayer over WebSockets.

## Features
- User lifecycle: create, fetch, connect/disconnect, in-game status, level, delete
- Auth: login and token verification
- Social: friend invite/accept/reject/remove
- Match history: save and read games
- Messaging: send and read inbox/sent messages
- Profile pictures: upload, conversion, thumbnail, fetch, delete
- File manager scoped to `UPLOAD_DIR`: list, info, copy, move, rename, create/delete folder
- Realtime sockets: lobby matchmaking/invites + room chat/moves

## Prerequisites
- Python `3.12.7` (from `runtime.txt`)
- A running MySQL-compatible database
- Terminal access (`PowerShell`, `bash`, or similar)

## Install (First Time)

### Windows (PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### macOS/Linux (bash)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Environment Variables
- `UPLOAD_DIR`: absolute directory used for file storage and profile pictures
- `DATABASE_URL`: database connection string used by the repository layer
- `JWT_SECRET`: token secret (defaults to `your-secret-key-change-in-production` if missing)

Example values:
- `UPLOAD_DIR=C:/temp/csgo_uploads`
- `DATABASE_URL=mysql+pymysql://user:password@127.0.0.1:3306/csgo`
- `JWT_SECRET=change-me-in-production`

### Set env vars on Windows (PowerShell, current terminal)
```powershell
$env:UPLOAD_DIR = "C:/temp/csgo_uploads"
$env:DATABASE_URL = "mysql+pymysql://user:password@127.0.0.1:3306/csgo"
$env:JWT_SECRET = "change-me-in-production"
```

### Set env vars on macOS/Linux (bash, current terminal)
```bash
export UPLOAD_DIR="/tmp/csgo_uploads"
export DATABASE_URL="mysql+pymysql://user:password@127.0.0.1:3306/csgo"
export JWT_SECRET="change-me-in-production"
```

## Run Locally
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## 5-Minute Quickstart
1. Install dependencies and set environment variables.
2. Start API with `uvicorn main:app --host 0.0.0.0 --port 8000`.
3. Create a user:
```bash
curl -X POST "http://localhost:8000/users/" -H "Content-Type: application/json" -d '{"username":"alice","password":"p@ss","name":"Alice"}'
```
4. Login and get token:
```bash
curl -X POST "http://localhost:8000/auth/login?username=alice&password=p@ss"
```
5. Mark user connected:
```bash
curl -X POST "http://localhost:8000/users/alice/connect"
```
6. Verify user exists:
```bash
curl "http://localhost:8000/users/alice"
```

## API Conventions
- Base URL examples use `http://localhost:8000`
- Most endpoints return JSON with a `status` key on success
- Several `POST` and `DELETE` routes expect query parameters (not JSON body)
- WebSocket payload format is always:
```json
{"type": "event.name", "payload": {}}
```

## REST API

### 1. Auth

#### `POST /auth/login`
Authenticate user credentials and return a JWT.

Input (query params):
- `username: string`
- `password: string`

Success output:
```json
{
	"status": "success",
	"username": "alice",
	"token": "<jwt>",
	"token_type": "Bearer",
	"expires_in": 86400
}
```

#### `GET /auth/verify`
Verify token validity.

Input (query params):
- `token: string`

Success output:
```json
{
	"status": "success",
	"username": "alice"
}
```

### 2. Users and Presence

#### `GET /users`
List all users.

#### `GET /users/{username}`
Get one user.

#### `POST /users/`
Create a user.

Input (JSON body):
```json
{
	"username": "alice",
	"password": "p@ss",
	"name": "Alice"
}
```

Success output:
```json
{
	"status": "success",
	"username": "alice"
}
```

#### `DELETE /users/{username}`
Delete user.

Success output:
- `204 No Content`

#### `GET /connected`
List users where `connected = true`.

#### `GET /free`
List users available for matchmaking (`connected` and not in game, repository-defined).

User list item format:
```json
{
	"username": "alice",
	"name": "Alice",
	"level": 1200,
	"friends": ["bob"],
	"profile_picture": "alice",
	"connected": true,
	"in_game": false
}
```

#### `POST /users/{username}/connect`
Mark user as connected.

Output:
```json
{
	"status": "success",
	"is_connected": 1
}
```

#### `POST /users/{username}/disconnect`
Mark user as disconnected.

Output:
```json
{
	"status": "success",
	"is_connected": 0
}
```

#### `POST /users/{username}/update_level`
Update user level used by leaderboard/matchmaking.

Input (JSON body):
```json
{
	"new_level": 1234
}
```

Success output:
```json
{
	"status": "success",
	"username": "alice",
	"new_level": 1234
}
```

#### `POST /users/{username}/in_game`
Set `in_game = true`.

#### `POST /users/{username}/not_in_game`
Set `in_game = false`.

Output for game-state routes:
```json
{
	"status": "success",
	"in_game": 1
}
```

or

```json
{
	"status": "success",
	"in_game": 0
}
```

### 3. Profile and Security Updates

#### `POST /users/{username}/change_name`
Input (query params):
- `new_name: string`

#### `POST /users/{username}/change_password`
Input (query params):
- `old_password: string`
- `new_password: string`

#### `POST /users/{username}/reset_password`
Input (query params):
- `new_password: string`

#### `POST /users/{username}/change_profile_picture`
Input (query params):
- `new_profile_picture: string`

Typical output:
```json
{
	"status": "success",
	"message": "alice changed name to Alice 2"
}
```

### 4. Friends

#### `POST /users/{username}/add_friend`
Send/initiate a friend action.

Input (JSON body):
```json
{
	"friend_username": "bob"
}
```

#### `POST /users/{username}/accept_friend`
Accept a friend invite.

Input (JSON body):
```json
{
	"friend_username": "bob"
}
```

#### `POST /users/{username}/reject_friend`
Reject a friend invite.

Input (JSON body):
```json
{
	"friend_username": "bob"
}
```

#### `POST /users/{username}/remove_friend`
Remove an existing friend.

Input (JSON body):
```json
{
	"friend_username": "bob"
}
```

Typical output:
```json
{
	"status": "success",
	"message": "bob added to alice"
}
```

### 5. Games

#### `GET /games/{username}`
Get game history for one user.

Output item format:
```json
{
	"black_player": "alice",
	"white_player": "bob",
	"timestamp": "2026-03-17T10:45:00",
	"result": "black_win",
	"moves": "[(3,4),(4,4)]"
}
```

#### `POST /games/`
Save a game result.

Input (JSON body):
```json
{
	"black_player_username": "alice",
	"white_player_username": "bob",
	"timestamp": "2026-03-17T10:45:00",
	"result": "black_win",
	"moves": "[(3,4),(4,4)]"
}
```

Timestamp accepted formats:
- ISO 8601, example: `2026-03-17T10:45:00`
- `DD-MM-YYYY`, example: `17-03-2026`

Success output:
```json
{
	"status": "success",
	"message": "Game between alice and bob added"
}
```

### 6. Messages

#### `GET /messages/{username}`
Get sent and received messages for a user.

Success output:
```json
{
	"sent": [
		{
			"recipient": "bob",
			"content": "Hello",
			"timestamp": "2026-03-17T11:00:00",
			"type": "chat"
		}
	],
	"received": [
		{
			"sender": "bob",
			"content": "Hi",
			"timestamp": "2026-03-17T11:01:00",
			"type": "chat"
		}
	]
}
```

#### `POST /messages/{sender_username}`
Send a message.

Input (JSON body):
```json
{
	"recipient_username": "bob",
	"timestamp": "2026-03-17T11:00:00",
	"content": "Hello",
	"type": "chat"
}
```

Timestamp accepted formats:
- ISO 8601, example: `2026-03-17T11:00:00`
- `DD-MM-YYYY HH:MM:SS`, example: `17-03-2026 11:00:00`

Success output:
```json
{
	"status": "success",
	"message": "Message sent from alice to bob:\n(chat ; 2026-03-17 11:00:00)\n'Hello'"
}
```

### 7. File Upload and Profile Pictures

#### `POST /upload/`
Upload a raw file to `UPLOAD_DIR`.

Input:
- multipart form-data with `file`

Success output:
```json
{
	"filename": "notes.txt",
	"path": "C:/.../UPLOAD_DIR/notes.txt"
}
```

#### `POST /users/{username}/profile-picture`
Upload and process an image.

Input:
- multipart form-data with `file`
- allowed types: `image/jpeg`, `image/png`, `image/webp`
- max file size: 5 MB

Success output:
```json
{
	"status": "success",
	"message": "Profile picture uploaded successfully",
	"username": "alice",
	"picture_path": "profiles/alice/profile.webp",
	"formats": ["webp", "jpg"],
	"sizes": {
		"full": 34567,
		"thumbnail": 4567
	}
}
```

#### `GET /users/{username}/profile-picture?format=webp|jpg`
Fetch full image.

#### `GET /users/{username}/profile-picture/thumb?format=webp|jpg`
Fetch thumbnail (150x150).

#### `DELETE /users/{username}/profile-picture`
Delete stored profile picture files and reset profile picture to default.

Success output:
```json
{
	"status": "success",
	"message": "Profile picture deleted for user 'alice'"
}
```

### 8. File Manager (`UPLOAD_DIR` scoped)

All paths are validated to remain inside `UPLOAD_DIR`.

#### `GET /files/?folder_path=`
List directory contents.

Input (query params):
- `folder_path: string` (optional, default root)

Success output:
```json
{
	"status": "success",
	"folder": "root",
	"items": [
		{
			"name": "profiles",
			"type": "folder",
			"size": null,
			"path": "profiles"
		},
		{
			"name": "notes.txt",
			"type": "file",
			"size": 123,
			"path": "notes.txt"
		}
	]
}
```

#### `GET /files/info/?file_path=`
Get metadata for one file or folder.

#### `POST /files/copy/`
Input (query params):
- `source_path: string`
- `destination_path: string`

#### `POST /files/move/`
Input (query params):
- `source_path: string`
- `destination_path: string`

#### `POST /files/rename/`
Input (query params):
- `file_path: string`
- `new_name: string`

#### `DELETE /files/`
Input (query params):
- `file_path: string`

#### `POST /folders/`
Input (query params):
- `folder_path: string`

#### `DELETE /folders/`
Input (query params):
- `folder_path: string`

Typical success output:
```json
{
	"status": "success",
	"message": "File moved from 'a.txt' to 'archive/a.txt'"
}
```

## WebSocket API

### Auth Notes
- `/ws/health` does not require auth
- `/ws/lobby` and `/ws/room/{room_id}` require header: `Authorization: Bearer <token>`
- If missing/invalid format, connection is closed with code `1008`

### 1. `WS /ws/health`
Echo endpoint for connectivity checks.

Client sends:
```json
{"message": "ping"}
```

Server responds:
```json
{"type": "health.echo", "payload": {"message": "ping"}}
```

### 2. `WS /ws/lobby`

Client messages:
- `client.hello` payload: `{ "username": string }`
- `queue.join` payload: `{ "level": int }`
- `queue.leave` payload: `{}`
- `invite.send` payload: `{ "to": string }`
- `invite.accept` payload: `{ "invite_id": string }`
- `invite.decline` payload: `{ "invite_id": string }`

Server events:
- `lobby.welcome` payload: `{ "username": string }`
- `queue.match_found` payload: `{ "room_id": string, "opponent": { "username": string, "level"?: int } }`
- `queue.left` payload: `{}`
- `invite.received` payload: `{ "invite_id": string, "from": string }`
- `invite.sent` payload: `{ "invite_id": string }`
- `invite.declined` payload: `{ "invite_id": string, "to"?: string }`
- `error` payload: `{ "message": string, "received"?: string }`

### 3. `WS /ws/room/{room_id}`

Client messages:
- `client.hello` payload: `{ "username": string }`
- `move.play` payload: `{ "x": int, "y": int }`
- `chat.send` payload: `{ "message": string }`
- `room.leave` payload: `{}`

Server events:
- `room.joined` payload: `{ "room_id": string }`
- `room.user_joined` payload: `{ "username": string }`
- `room.user_left` payload: `{ "username": string }`
- `move.played` payload: `{ "x": int, "y": int, "from": string, "color": int | null }`
- `chat.message` payload: `{ "from": string, "message": string }`
- `room.left` payload: `{ "room_id": string }`
- `error` payload: `{ "message": string, "received"?: string }`

## Use Cases

### Use Case 1: Login and Open Lobby Socket
1. Call `POST /auth/login?username=alice&password=p@ss`.
2. Receive `token` in response.
3. Connect to `/ws/lobby` with header `Authorization: Bearer <token>`.
4. Send:
```json
{"type": "client.hello", "payload": {"username": "alice"}}
```
5. Receive:
```json
{"type": "lobby.welcome", "payload": {"username": "alice"}}
```

### Use Case 2: Matchmaking by Level
1. User enters queue:
```json
{"type": "queue.join", "payload": {"level": 1200}}
```
2. Server finds nearest level player and sends:
```json
{
	"type": "queue.match_found",
	"payload": {
		"room_id": "a1b2c3",
		"opponent": {"username": "bob", "level": 1180}
	}
}
```
3. Both clients connect to `/ws/room/a1b2c3`.

### Use Case 3: Friend Invitation Flow
1. Send invite:
```json
{"type": "invite.send", "payload": {"to": "bob"}}
```
2. Inviter receives:
```json
{"type": "invite.sent", "payload": {"invite_id": "inv123"}}
```
3. Receiver gets:
```json
{"type": "invite.received", "payload": {"invite_id": "inv123", "from": "alice"}}
```
4. Receiver accepts or declines:
```json
{"type": "invite.accept", "payload": {"invite_id": "inv123"}}
```

### Use Case 4: Upload and Read Profile Picture
1. Upload image with `POST /users/alice/profile-picture` and form-data file.
2. Receive converted asset paths and sizes.
3. Read full image with `/users/alice/profile-picture?format=webp`.
4. Read thumbnail with `/users/alice/profile-picture/thumb?format=jpg`.
5. Delete with `DELETE /users/alice/profile-picture`.

### Use Case 5: Save and Fetch Match History
1. Save a game with `POST /games/` and JSON body.
2. Receive success message.
3. Fetch user history with `GET /games/alice`.
4. Receive game list containing `black_player`, `white_player`, `timestamp`, `result`, and `moves`.

## Beginner Test Order
Use this order to avoid dependency errors while learning the API.

1. `POST /users/` to create at least one user.
2. `POST /auth/login` to get a token.
3. `GET /auth/verify` to confirm the token works.
4. `POST /users/{username}/connect` to set online status.
5. `GET /users/{username}` to verify the account state.
6. `GET /connected` to verify presence listing.
7. Open WebSocket `/ws/lobby` with `Authorization: Bearer <token>`.
8. Send `client.hello` then `queue.join`.
9. Open `/ws/room/{room_id}` after `queue.match_found`.

## Minimal WebSocket Client Example (Python)
This example uses `websocket-client` from `requirements.txt` and connects to `/ws/health` (no token required).

```python
import json
import websocket

ws = websocket.create_connection("ws://localhost:8000/ws/health")
ws.send(json.dumps({"message": "ping"}))
print(ws.recv())
ws.close()
```

If this works, your server and WebSocket stack are healthy.

## Troubleshooting
- `401 Invalid credentials` on `/auth/login`:
Use the same username/password used during `POST /users/`.
- `401 Invalid token` on `/auth/verify`:
Send the exact token string returned by `/auth/login`.
- WebSocket closes with `1008 unauthorized`:
Add header `Authorization: Bearer <token>` on `/ws/lobby` and `/ws/room/{room_id}`.
- `404 User not found`:
Create the user first with `POST /users/`.
- `404 No connected users found`:
Call `/users/{username}/connect` before `/connected`.
- `400 Invalid path` on file routes:
Pass paths relative to `UPLOAD_DIR`, not absolute OS paths.
- `413 File too large` on profile-picture upload:
Image exceeds 5 MB; reduce file size.
- Startup crash mentioning `DATABASE_URL` or `UPLOAD_DIR`:
Environment variables are missing in the current terminal session.

## Infographics

### 1. Auth then Lobby/Room Flow
```mermaid
flowchart TB
    A[Client] --> B[POST /auth/login]
    B --> C{Credentials valid?}
    C -- No --> D[401 Invalid credentials]
    C -- Yes --> E[JWT token]
    E --> F[WS /ws/lobby with Bearer token]
    F --> G[client.hello]
    G --> H[lobby.welcome]
    H --> I[queue.match_found]
    I --> J[WS /ws/room/:room_id]
```

### 2. Matchmaking and Invite Flow
```mermaid
flowchart TB
    A[User A queue.join level=1200] --> M{Opponent available?}
    M -- Yes --> R[queue.match_found for both users]
    M -- No --> Q[Wait in queue]
    Q --> A2[invite.send to User B]
    A2 --> B1{User B online?}
    B1 -- No --> E1[error user-offline]
    B1 -- Yes --> B2[invite.received on User B]
    B2 --> B3{Accept or decline?}
    B3 -- Accept --> R
    B3 -- Decline --> D1[invite.declined]
```

### 3. Profile Picture Processing Flow
```mermaid
flowchart TB
    A[Upload image POST profile-picture] --> B{Type and size valid?}
    B -- No --> C[400 or 413 error]
    B -- Yes --> D[Convert and resize]
    D --> E[Save full profile.webp and profile.jpg]
    D --> F[Save thumbnails webp and jpg]
    E --> G[Update DB profile_picture]
    F --> H[Return formats and sizes]
    H --> I[GET profile-picture]
    H --> J[GET profile-picture thumb]
```

## Notes
- Runtime state for sockets, queue, invites, and rooms is in memory.
- For multi-instance deployment, use shared state (for example Redis + pub/sub).
- Path-based file endpoints guard against directory traversal by checking resolved paths under `UPLOAD_DIR`.
