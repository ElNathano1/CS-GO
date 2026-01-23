"""
Local test (no emojis, simple output) for debugging profile picture persistence.
Run your FastAPI server locally first: uvicorn main:app --reload
"""

import os
import requests
from io import BytesIO
from PIL import Image

API_URL = "http://localhost:8080"
TEST_USERNAME = "local_test_user"


def create_test_image():
    img = Image.new("RGB", (100, 100), color=(255, 100, 0))
    img_bytes = BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)
    return img_bytes.getvalue()


# Step 1: Check user DB value before upload
print("[1] GET /users/{} - check DB value before upload".format(TEST_USERNAME))
resp = requests.get(f"{API_URL}/users/{TEST_USERNAME}")
if resp.status_code == 200:
    data = resp.json()
    print("    profile_picture = {}".format(data.get("profile_picture")))
else:
    print("    User not found (404)")

# Step 2: Upload
print("\n[2] POST /users/{}/profile-picture - upload image".format(TEST_USERNAME))
image = create_test_image()
resp = requests.post(
    f"{API_URL}/users/{TEST_USERNAME}/profile-picture",
    files={"file": ("test.png", image, "image/png")},
)
print("    Status: {} - {}".format(resp.status_code, resp.json().get("status")))

# Step 3: Check user DB value after upload
print("\n[3] GET /users/{} - check DB value AFTER upload".format(TEST_USERNAME))
resp = requests.get(f"{API_URL}/users/{TEST_USERNAME}")
if resp.status_code == 200:
    data = resp.json()
    profile_pic = data.get("profile_picture")
    print("    profile_picture = {}".format(profile_pic))
    if profile_pic == TEST_USERNAME:
        print("    [PASS] DB was correctly updated!")
    else:
        print("    [FAIL] DB was NOT updated - still null/default")
else:
    print("    Error: {}".format(resp.status_code))

# Step 4: Try to fetch full image
print("\n[4] GET /users/{}/profile-picture - fetch full image".format(TEST_USERNAME))
resp = requests.get(f"{API_URL}/users/{TEST_USERNAME}/profile-picture?format=webp")
print("    Status: {}".format(resp.status_code))
if resp.status_code == 200:
    print("    Size: {} bytes".format(len(resp.content)))
else:
    print("    Error: {}".format(resp.text[:100]))

# Step 5: Try to fetch thumbnail
print(
    "\n[5] GET /users/{}/profile-picture/thumb - fetch thumbnail".format(TEST_USERNAME)
)
resp = requests.get(
    f"{API_URL}/users/{TEST_USERNAME}/profile-picture/thumb?format=webp"
)
print("    Status: {}".format(resp.status_code))
if resp.status_code == 200:
    print("    Size: {} bytes".format(len(resp.content)))
else:
    print("    Error: {}".format(resp.text[:100]))

print("\nDone. Check [PASS]/[FAIL] above.")
