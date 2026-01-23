"""
Debug test: Check if API returns 404 after file deletion
"""

import requests
import json

API_URL = "https://cs-go-production.up.railway.app"
TEST_USER = "elnathano"

print("=" * 70)
print("DEBUG: File-on-disk vs API response mismatch")
print("=" * 70)

# Step 1: Check current DB state
print("\n[1] Checking current DB state...")
resp = requests.get(f"{API_URL}/users/{TEST_USER}")
data = resp.json()
profile_pic = data.get("profile_picture")
print(f"    profile_picture in DB: {profile_pic}")

# Step 2: Try to fetch thumbnail
print(f"\n[2] Attempting to GET /users/{TEST_USER}/profile-picture/thumb...")
thumb_resp = requests.get(
    f"{API_URL}/users/{TEST_USER}/profile-picture/thumb?format=webp"
)
print(f"    Status Code: {thumb_resp.status_code}")
print(f"    Content-Type: {thumb_resp.headers.get('Content-Type')}")
print(f"    Cache-Control: {thumb_resp.headers.get('Cache-Control')}")
print(f"    Content-Length: {thumb_resp.headers.get('Content-Length', 'N/A')}")
print(f"    Actual Response Size: {len(thumb_resp.content)} bytes")

if thumb_resp.status_code == 200:
    print(f"\n    PROBLEM: Got 200 OK with image data!")
    print(f"    -> File was deleted, but API still returns it")
    print(f"    -> This is either:")
    print(f"       A) Cache at Railway level (proxy/CDN)")
    print(f"       B) File wasn't actually deleted")
    print(f"       C) Wrong file path being used")
elif thumb_resp.status_code == 404:
    print(f"\n    OK: Got 404 as expected")
else:
    print(f"\n    UNEXPECTED: Got {thumb_resp.status_code}")

# Step 3: Check response headers for caching indicators
print(f"\n[3] Checking response headers...")
headers_to_check = [
    "Cache-Control",
    "Pragma",
    "Expires",
    "ETag",
    "Last-Modified",
    "Age",
    "X-Cache",
    "CF-Cache-Status",
]
for header in headers_to_check:
    value = thumb_resp.headers.get(header)
    if value:
        print(f"    {header}: {value}")

print("\n" + "=" * 70)
