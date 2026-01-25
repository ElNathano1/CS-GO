"""
Minimal demo to exercise the MultiplayerClient using a public echo server.

Note: This is only for validating the event loop locally. It does not
reflect your production protocol. Replace ECHO_URL with your server's
WebSocket URL when available.
"""

import json
import time

from client import MultiplayerClient, Event

# Try a list of public echo WebSocket endpoints (some networks block DNS)
ECHO_URLS = [
    "wss://echo.websocket.events",  # primary
    "wss://ws.ifelse.io",  # fallback 1
    "wss://demo.piesocket.com/v3/echo?api_key=TEST",  # fallback 2
]


def on_event(evt: Event) -> None:
    print("EVENT:", evt.type, evt.payload)


if __name__ == "__main__":
    last_error = None
    for url in ECHO_URLS:
        try:
            # Temporarily override the client's URLs to the echo server
            client = MultiplayerClient(
                base_url=url.replace("wss://", "https://"),
                username="demo",
                on_event=on_event,
            )
            client.ws_url_lobby = url
            print(f"Connecting to: {url}")
            client.start()

            # Send a few messages
            client.send_chat("hello world")
            client._send({"type": "queue.join", "payload": {"level": 1200}})
            time.sleep(3)
            client.stop()
            print("Success with:", url)
            break
        except Exception as e:
            print("Failed:", url, "->", e)
            last_error = e
            try:
                client.stop()
            except Exception:
                pass
    else:
        raise SystemExit(f"All echo endpoints failed: {last_error}")
