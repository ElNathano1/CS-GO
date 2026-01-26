# CS-GO User Service (Railway Branch)

This FastAPI service powers user accounts, profile pictures, file utilities, and realtime multiplayer via WebSockets. It is designed to run on Railway.

## Overview
- REST APIs for users: create, connect, update level, manage friends
- Profile pictures: upload, convert to WebP/JPEG, thumbnails, fetch & delete
- File utilities: list, info, copy, move, rename, folder create/delete (scoped to `UPLOAD_DIR`)
- Realtime WebSockets: matchmaking queue and invitations (`/ws/lobby`), room events (`/ws/room/{room_id}`)

## Environment
- `UPLOAD_DIR`: Absolute path used to store files and profile pictures

## Run Locally
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## REST Endpoints

### Users
- `GET /connected` — List connected users
- `GET /users` — List all users
- `GET /users/{username}` — Get a user
- `POST /users/` — Create user `{ username, password, name }`
- `POST /users/{username}/connect` — Mark user connected
- `POST /users/{username}/disconnect` — Mark user disconnected
- `POST /users/{username}/update_level` — Update `{ new_level }`
- `POST /users/{username}/add_friend` — `{ friend_username }`
- `POST /users/{username}/remove_friend` — `{ friend_username }`
- `POST /users/{username}/change_name` — `{ new_name }`
- `POST /users/{username}/change_password` — `{ old_password, new_password }`

### Profile Pictures
- `POST /users/{username}/profile-picture` — Upload `file`
- `GET /users/{username}/profile-picture?format=webp|jpg` — Fetch full picture
- `GET /users/{username}/profile-picture/thumb?format=webp|jpg` — Fetch thumbnail
- `DELETE /users/{username}/profile-picture` — Delete picture

### Files (scoped to `UPLOAD_DIR`)
- `GET /files/?folder_path=` — List
- `GET /files/info/?file_path=` — Info
- `POST /files/copy/` — `{ source_path, destination_path }`
- `POST /files/move/` — `{ source_path, destination_path }`
- `POST /files/rename/` — `{ file_path, new_name }`
- `POST /folders/` — `{ folder_path }`
- `DELETE /folders/` — `{ folder_path }`
- `DELETE /files/` — `{ file_path }`

## WebSockets

### Health Check `/ws/health` (no auth)
Quick diagnostics endpoint. Client connects and sends JSON; server echoes back.

```json
// Send
{"message":"ping"}

// Receive
{"type":"health.echo","payload":{"message":"ping"}}
```

### Lobby `/ws/lobby` (auth required)
- **Auth**: Requires `Authorization: Bearer <token>` header
- Connect and send: `{"type":"client.hello","payload":{"username":"alice"}}`
- Join queue: `{"type":"queue.join","payload":{"level":1200}}`
- Leave queue: `{"type":"queue.leave","payload":{}}`
- Send invite: `{"type":"invite.send","payload":{"to":"bob"}}`
- Accept invite: `{"type":"invite.accept","payload":{"invite_id":"..."}}`
- Decline invite: `{"type":"invite.decline","payload":{"invite_id":"..."}}`

Server events:
- `queue.match_found { room_id, opponent }`
- `invite.received { invite_id, from }`
- `invite.sent { invite_id }`
- `invite.declined { invite_id, to? }`
- `error { message }`

### Room `/ws/room/{room_id}` (auth required)
- **Auth**: Requires `Authorization: Bearer <token>` header
- Connect and send: `{"type":"client.hello","payload":{"username":"alice"}}`
- Play move: `{"type":"move.play","payload":{"x":3,"y":4}}`
- Send chat: `{"type":"chat.send","payload":{"message":"gg"}}`
- Leave: `{"type":"room.leave","payload":{}}`

Server events:
- `room.joined { room_id }`
- `room.user_joined { username }`
- `room.user_left { username }`
- `move.played { x, y, from, color }`
- `chat.message { from, message }`
- `error { message }`

## Notes
- All WebSocket messages are JSON objects with `type` and `payload` keys.
- This implementation stores state in memory. For scaling across instances, use a shared store (e.g., Redis) and a pub/sub for room broadcasts.
- WebSocket connections require Bearer token authentication (except `/ws/health`). Connections without valid auth are rejected with code 1008 (unauthorized).
- Use `/ws/health` to test connectivity without setting up auth.
