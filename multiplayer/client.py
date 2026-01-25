"""
Realtime multiplayer client for the Go game.

This client manages a WebSocket connection to the backend server to
support real-time play between two players.

Features:
- Matchmaking queue by player level
- Invitations and accept/decline
- Room join/leave and move broadcasting
- Heartbeats and reconnection with backoff

Message Protocol (JSON):
- Outgoing messages:
  {"type": "queue.join", "payload": {"level": 1200, "username": "alice"}}
  {"type": "invite.send", "payload": {"to": "bob"}}
  {"type": "invite.accept", "payload": {"invite_id": "..."}}
  {"type": "room.join", "payload": {"room_id": "..."}}
  {"type": "move.play", "payload": {"x": 12, "y": 5}}
  {"type": "chat.send", "payload": {"message": "gg"}}

- Incoming messages:
  {"type": "queue.match_found", "payload": {"room_id": "...", "opponent": {"username": "bob", "level": 1150}}}
  {"type": "invite.received", "payload": {"invite_id": "...", "from": "alice"}}
  {"type": "room.joined", "payload": {"room_id": "..."}}
  {"type": "move.played", "payload": {"x": 12, "y": 5, "color": 1}}
  {"type": "chat.message", "payload": {"from": "bob", "message": "hi"}}
  {"type": "error", "payload": {"code": "...", "message": "..."}}

Usage:
  from multiplayer.client import MultiplayerClient
  client = MultiplayerClient(base_url="https://CS-GO.up.railway.app", username="alice")
  client.start()  # starts the background thread
  client.join_queue(level=1200)
  ...

Threading:
Tkinter should not be blocked by network I/O. This client runs networking
in a background thread and calls a user-provided callback on incoming
messages. Use thread-safe queues to bridge with the GUI.
"""

from __future__ import annotations

import json
import time
import threading
import queue
import logging
import importlib
from dataclasses import dataclass
from typing import Callable, Optional, Any, Dict

# Import websocket lazily inside runtime methods to avoid static analysis issues

logger = logging.getLogger(__name__)


@dataclass
class Event:
    """Wrapper for incoming messages.

    Attributes:
        type: Message type identifier
        payload: JSON payload dict
    """

    type: str
    payload: Dict[str, Any]


class MultiplayerClient:
    """
    WebSocket client handling matchmaking, invites and room events.

    This client is resilient to transient network failures with
    exponential backoff, and can be cleanly stopped.
    """

    def __init__(
        self,
        base_url: str,
        username: str,
        token: Optional[str] = None,
        on_event: Optional[Callable[[Event], None]] = None,
    ) -> None:
        """
        Initialize the client.

        Args:
            base_url: Base HTTP URL of the backend (e.g., https://CS-GO.up.railway.app)
            username: Current user's username
            token: Optional auth token (sent as header if provided)
            on_event: Optional callback invoked for each incoming event
        """
        self.base_url = base_url.rstrip("/")
        self.ws_url_lobby = self._http_to_ws(self.base_url + "/ws/lobby")
        self.ws_url_room_base = self._http_to_ws(self.base_url + "/ws/room")
        self.username = username
        self.token = token
        self.on_event = on_event

        self._ws: Optional[Any] = None
        self._thread: Optional[threading.Thread] = None
        self._outbox: "queue.Queue[str]" = queue.Queue()
        self._stop = threading.Event()
        self._connected = threading.Event()
        self._current_room_id: Optional[str] = None

    @staticmethod
    def _http_to_ws(url: str) -> str:
        return url.replace("https://", "wss://").replace("http://", "ws://")

    def start(self) -> None:
        """Start the background networking thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="ws-thread", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the client and close the connection."""
        self._stop.set()
        try:
            if self._ws:
                self._ws.close()
        except Exception:
            pass
        if self._thread:
            self._thread.join(timeout=2)

    # -------------- Public API --------------

    def join_queue(self, level: int) -> None:
        """
        Join the matchmaking queue.

        Args:
            level: Player level/rating used for matchmaking
        """
        self._send({"type": "queue.join", "payload": {"level": level, "username": self.username}})

    def leave_queue(self) -> None:
        """Leave the matchmaking queue."""
        self._send({"type": "queue.leave", "payload": {"username": self.username}})

    def send_invite(self, to_username: str) -> None:
        """
        Send a game invitation to another user.
        """
        self._send({"type": "invite.send", "payload": {"to": to_username}})

    def accept_invite(self, invite_id: str) -> None:
        """Accept a pending invitation."""
        self._send({"type": "invite.accept", "payload": {"invite_id": invite_id}})

    def decline_invite(self, invite_id: str) -> None:
        """Decline a pending invitation."""
        self._send({"type": "invite.decline", "payload": {"invite_id": invite_id}})

    def join_room(self, room_id: str) -> None:
        """Join a game room to start playing."""
        self._current_room_id = room_id
        self._send({"type": "room.join", "payload": {"room_id": room_id}})

    def leave_room(self) -> None:
        """Leave the current game room."""
        if self._current_room_id:
            self._send({"type": "room.leave", "payload": {"room_id": self._current_room_id}})
            self._current_room_id = None

    def send_move(self, x: int, y: int) -> None:
        """Send a played move to the room."""
        self._send({"type": "move.play", "payload": {"x": x, "y": y}})

    def send_chat(self, message: str) -> None:
        """Send a chat message to the room."""
        self._send({"type": "chat.send", "payload": {"message": message}})

    # -------------- Internals --------------

    def _run(self) -> None:
        backoff = 1.0
        while not self._stop.is_set():
            try:
                headers = []
                if self.token:
                    headers.append(f"Authorization: Bearer {self.token}")

                # Lazy import here to avoid import resolution errors before installation
                try:
                    ws_module = importlib.import_module("websocket")
                    WebSocketApp = getattr(ws_module, "WebSocketApp")
                except Exception:
                    raise RuntimeError(
                        "websocket-client is not installed. Please install dependencies."
                    )

                self._ws = WebSocketApp(
                    self.ws_url_lobby,
                    header=headers,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_close=self._on_close,
                    on_error=self._on_error,
                )
                if self._ws is not None:
                    self._ws.run_forever(ping_interval=20, ping_timeout=10)
            except Exception as e:
                logger.warning("WebSocket run_forever error: %s", e)

            # Wait and retry
            self._connected.clear()
            if self._stop.is_set():
                break
            time.sleep(backoff)
            backoff = min(backoff * 2, 30)

    def _on_open(self, ws: Any) -> None:  # noqa: ANN001
        self._connected.set()
        logger.info("WebSocket connected")
        # Identify
        self._send({"type": "client.hello", "payload": {"username": self.username}})

    def _on_message(self, ws: Any, message: str) -> None:  # noqa: ANN001
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            logger.warning("Invalid JSON from server: %s", message)
            return

        evt = Event(type=data.get("type", "unknown"), payload=data.get("payload", {}))
        if self.on_event:
            try:
                self.on_event(evt)
            except Exception:
                logger.exception("on_event callback raised an exception")

    def _on_close(self, ws: Any, status_code: int, msg: str) -> None:  # noqa: ANN001
        logger.info("WebSocket closed: %s %s", status_code, msg)

    def _on_error(self, ws: Any, error: Exception) -> None:  # noqa: ANN001
        logger.error("WebSocket error: %s", error)

    def _send(self, obj: Dict[str, Any]) -> None:
        """Enqueue a JSON message to be sent as soon as connected."""
        payload = json.dumps(obj)
        # Try sending immediately if connected
        try:
            if self._ws and self._connected.is_set():
                self._ws.send(payload)
                return
        except Exception:
            pass
        # Fallback: queue for later
        self._outbox.put(payload)
        # Drain if connected
        if self._ws and self._connected.is_set():
            while not self._outbox.empty():
                try:
                    self._ws.send(self._outbox.get_nowait())
                except Exception:
                    break
