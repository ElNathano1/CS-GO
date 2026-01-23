"""
Full lifecycle test with unique user to isolate the caching issue
"""

import requests
from io import BytesIO
from PIL import Image
import time
import uuid

API_URL = "https://cs-go-production.up.railway.app"
# Use a unique username each run to avoid stale caches
TEST_USER = f"test_pic_{uuid.uuid4().hex[:8]}"


def create_test_image():
    img = Image.new("RGB", (100, 100), color=(255, 0, 0))
    img_bytes = BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)
    return img_bytes.getvalue()


print("=" * 70)
print(f"LIFECYCLE TEST: {TEST_USER}")
print("=" * 70)

# Step 1: Create unique user
print(f"\n[1] Creating user {TEST_USER}...")
resp = requests.post(
    f"{API_URL}/users/",
    json={"username": TEST_USER, "password": "test123", "name": "Test User"},
)
if resp.status_code in [200, 400]:
    print(f"    OK (status {resp.status_code})")
else:
    print(f"    FAIL: {resp.status_code}")
    exit(1)

# Step 2: Upload image
print(f"\n[2] Uploading profile picture...")
image = create_test_image()
resp = requests.post(
    f"{API_URL}/users/{TEST_USER}/profile-picture",
    files={"file": ("test.png", image, "image/png")},
)
if resp.status_code == 200:
    print(f"    OK - uploaded")
else:
    print(f"    FAIL: {resp.status_code} {resp.text}")
    exit(1)

# Step 3: Fetch thumbnail (should be 200)
print(f"\n[3] Fetching thumbnail...")
resp = requests.get(f"{API_URL}/users/{TEST_USER}/profile-picture/thumb?format=webp")
print(f"    Status: {resp.status_code}")
if resp.status_code != 200:
    print(f"    FAIL: Expected 200, got {resp.status_code}")
    exit(1)
print(f"    Size: {len(resp.content)} bytes")

# Step 4: Delete profile picture
print(f"\n[4] Deleting profile picture...")
resp = requests.delete(f"{API_URL}/users/{TEST_USER}/profile-picture")
if resp.status_code == 200:
    print(f"    OK - deleted")
else:
    print(f"    FAIL: {resp.status_code}")
    exit(1)

# Step 5: Try to fetch thumbnail immediately (should be 404)
print(f"\n[5] Fetching thumbnail IMMEDIATELY after delete...")
resp = requests.get(f"{API_URL}/users/{TEST_USER}/profile-picture/thumb?format=webp")
print(f"    Status: {resp.status_code}")
if resp.status_code == 404:
    print(f"    OK - Got 404 as expected")
else:
    print(f"    PROBLEM: Expected 404, got {resp.status_code}")
    print(f"    Content-Length: {len(resp.content)} bytes")
    if resp.status_code == 200:
        print(f"    -> FILE WAS DELETED BUT API STILL RETURNS IT!")

# Step 6: Wait and retry
print(f"\n[6] Waiting 3 seconds and retrying...")
time.sleep(3)
resp = requests.get(f"{API_URL}/users/{TEST_USER}/profile-picture/thumb?format=webp")
print(f"    Status: {resp.status_code}")
if resp.status_code == 404:
    print(f"    OK - Got 404")
else:
    print(f"    PROBLEM: Still getting {resp.status_code}")

# Step 7: Check DB state
print(f"\n[7] Checking DB state...")
resp = requests.get(f"{API_URL}/users/{TEST_USER}")
profile_pic = resp.json().get("profile_picture")
print(f"    profile_picture in DB: {profile_pic}")
if profile_pic == "default":
    print(f"    OK - DB correctly reset to 'default'")
else:
    print(f"    PROBLEM: Expected 'default', got {profile_pic}")

print("\n" + "=" * 70)
