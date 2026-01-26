"""
Demo script to verify Railway WebSocket connection and test all endpoints.

This script tests:
1. Health check endpoint (no auth)
2. Login to generate a Bearer token
3. WebSocket lobby connection with Bearer token
4. Queue operations (join/leave)
5. Room connection and in-game events
"""

import asyncio
import json
import uuid
import websockets
from websockets.exceptions import InvalidStatus
import httpx


# Configuration
RAILWAY_URL = "cs-go-production.up.railway.app"
REST_API = f"https://{RAILWAY_URL}"
HEALTH_URL = f"wss://{RAILWAY_URL}/ws/health"
LOBBY_URL = f"wss://{RAILWAY_URL}/ws/lobby"

# Demo credentials (create these users first via REST API)
DEMO_USER_1 = "elnathano"
DEMO_USER_2 = "biggo"
DEMO_PASSWORD = "password123"
DEMO_TOKEN = None  # Will be generated via login


class WebSocketDemo:
    def __init__(self, url: str, token: str = None):
        self.url = url
        self.token = token
        self.ws = None

    async def connect(self):
        """Connect to WebSocket endpoint."""
        try:
            kwargs = {}
            if self.token:
                kwargs["additional_headers"] = {"Authorization": f"Bearer {self.token}"}
            
            self.ws = await websockets.connect(self.url, **kwargs)
            print(f"✅ Connected to {self.url}")
            return True
        except InvalidStatus as e:
            print(f"❌ Connection failed: {e}")
            return False
        except Exception as e:
            print(f"❌ Connection failed: {type(e).__name__}: {e}")
            return False

    async def send(self, message: dict):
        """Send JSON message."""
        if not self.ws:
            print("❌ Not connected")
            return

        await self.ws.send(json.dumps(message))
        print(f"📤 Sent: {json.dumps(message, indent=2)}")

    async def receive(self, timeout: float = 5) -> dict | None:
        """Receive JSON message with timeout."""
        if not self.ws:
            print("❌ Not connected")
            return None

        try:
            message = await asyncio.wait_for(self.ws.recv(), timeout=timeout)
            data = json.loads(message)
            print(f"📥 Received: {json.dumps(data, indent=2)}")
            return data
        except asyncio.TimeoutError:
            print(f"⏱️ No response (timeout {timeout}s)")
            return None
        except Exception as e:
            print(f"❌ Error receiving: {e}")
            return None

    async def close(self):
        """Close connection."""
        if self.ws:
            await self.ws.close()
            print("🔌 Disconnected")


async def test_login():
    """Generate a Bearer token via login endpoint."""
    print("\n" + "=" * 60)
    print("TEST 1: Login & Generate Bearer Token")
    print("=" * 60)
    
    global DEMO_TOKEN
    
    try:
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(
                f"{REST_API}/auth/login",
                params={"username": DEMO_USER_1, "password": DEMO_PASSWORD}
            )
            if response.status_code == 200:
                data = response.json()
                DEMO_TOKEN = data.get("token")
                print(f"✅ Login successful")
                print(f"   Token: {DEMO_TOKEN[:20]}...")
                return True
            else:
                print(f"❌ Login failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
    except Exception as e:
        print(f"❌ Login error: {type(e).__name__}: {e}")
        return False


async def test_health_check():
    """Test health check endpoint (no auth required)."""
    print("\n" + "=" * 60)
    print("TEST 2: Health Check Endpoint")
    print("=" * 60)

    demo = WebSocketDemo(HEALTH_URL)

    if not await demo.connect():
        return False

    # Send ping
    await demo.send({"message": "ping"})
    response = await demo.receive(timeout=3)

    await demo.close()

    return response is not None and response.get("type") == "health.echo"


async def test_lobby_connection():
    """Test lobby connection with Bearer token."""
    print("\n" + "=" * 60)
    print("TEST 3: Lobby Connection (with auth)")
    print("=" * 60)

    demo = WebSocketDemo(LOBBY_URL, token=DEMO_TOKEN)

    if not await demo.connect():
        print("❌ Auth may be required. Create a user first:")
        print("   curl -X POST http://cs-go-production.up.railway.app/users/ \\")
        print("     -H 'Content-Type: application/json' \\")
        print(
            f'     -d \'{{"username":"{DEMO_USER_1}","password":"test123","name":"Alice"}}\''
        )
        return False

    # Send hello message
    await demo.send({"type": "client.hello", "payload": {"username": DEMO_USER_1}})
    response = await demo.receive(timeout=3)

    await demo.close()

    return response is not None


async def test_queue_join():
    """Test joining matchmaking queue."""
    print("\n" + "=" * 60)
    print("TEST 4: Queue Join")
    print("=" * 60)

    demo = WebSocketDemo(LOBBY_URL, token=DEMO_TOKEN)

    if not await demo.connect():
        return False

    # Say hello
    await demo.send({"type": "client.hello", "payload": {"username": DEMO_USER_1}})
    await demo.receive(timeout=2)

    # Join queue
    await demo.send({"type": "queue.join", "payload": {"level": 1200}})
    response = await demo.receive(timeout=3)

    # Leave queue
    await demo.send({"type": "queue.leave", "payload": {}})
    await demo.receive(timeout=2)

    await demo.close()

    return response is not None


async def test_room_connection():
    """Test room connection."""
    print("\n" + "=" * 60)
    print("TEST 5: Room Connection")
    print("=" * 60)

    # Use a dummy room ID for testing
    room_id = str(uuid.uuid4())
    room_url = f"wss://{RAILWAY_URL}/ws/room/{room_id}"

    demo = WebSocketDemo(room_url, token=DEMO_TOKEN)

    if not await demo.connect():
        return False

    # Say hello in room
    await demo.send({"type": "client.hello", "payload": {"username": DEMO_USER_1}})
    response = await demo.receive(timeout=3)

    await demo.close()

    return response is not None


async def test_invitation_flow():
    """Test invitation sending and receiving."""
    print("\n" + "=" * 60)
    print("TEST 6: Invitation Flow")
    print("=" * 60)

    demo = WebSocketDemo(LOBBY_URL, token=DEMO_TOKEN)

    if not await demo.connect():
        return False

    # Say hello
    await demo.send({"type": "client.hello", "payload": {"username": DEMO_USER_1}})
    await demo.receive(timeout=2)

    # Send invite
    await demo.send({"type": "invite.send", "payload": {"to": DEMO_USER_2}})
    response = await demo.receive(timeout=3)

    await demo.close()

    return response is not None and response.get("type") == "invite.sent"


async def run_all_tests():
    """Run all tests."""
    print("\n" + "🔍 RAILWAY WebSocket Connection Test Suite 🔍".center(60))

    results = {
        "Login": await test_login(),
        "Health Check": await test_health_check(),
        "Lobby Connection": await test_lobby_connection(),
        "Queue Join": await test_queue_join(),
        "Room Connection": await test_room_connection(),
        "Invitation Flow": await test_invitation_flow(),
    }

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} | {test_name}")

    print(f"\n📊 Result: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Railway connection is working.")
    else:
        print("⚠️  Some tests failed. Check the errors above.")

    return passed == total


if __name__ == "__main__":
    print(f"\n🚀 Testing WebSocket at: {RAILWAY_URL}")
    print(f"📌 REST API: {REST_API}")
    print(f"📌 Health URL: {HEALTH_URL}")
    print(f"📌 Lobby URL: {LOBBY_URL}")
    print("\n⚠️  Before running, ensure:")
    print("   1. Railway deployment is live")
    print("   2. Test users exist (elnathano, biggo)")
    print("   3. User passwords match DEMO_PASSWORD")
    
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)
