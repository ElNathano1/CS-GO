"""
Test with explicit cache-busting headers to bypass Railway CDN
"""

import requests

API_URL = "https://cs-go-production.up.railway.app"
TEST_USER = "elnathano"

print("Testing elnathano thumbnail with cache-busting headers\n")

# Test 1: Normal request
print("[1] Normal request:")
resp = requests.get(f"{API_URL}/users/{TEST_USER}/profile-picture/thumb?format=webp")
print(f"    Status: {resp.status_code}")
print(f"    Size: {len(resp.content)} bytes")

# Test 2: With Cache-Control header
print("\n[2] With 'Cache-Control: no-cache' header:")
resp = requests.get(
    f"{API_URL}/users/{TEST_USER}/profile-picture/thumb?format=webp",
    headers={"Cache-Control": "no-cache"},
)
print(f"    Status: {resp.status_code}")
print(f"    Size: {len(resp.content)} bytes")

# Test 3: With Pragma header
print("\n[3] With 'Pragma: no-cache' header:")
resp = requests.get(
    f"{API_URL}/users/{TEST_USER}/profile-picture/thumb?format=webp",
    headers={"Pragma": "no-cache"},
)
print(f"    Status: {resp.status_code}")
print(f"    Size: {len(resp.content)} bytes")

# Test 4: With query string random (cache busting)
print("\n[4] With random query string (cache buster):")
import time

resp = requests.get(
    f"{API_URL}/users/{TEST_USER}/profile-picture/thumb?format=webp&t={int(time.time()*1000)}"
)
print(f"    Status: {resp.status_code}")
print(f"    Size: {len(resp.content)} bytes")

# Test 5: Check DB to see what profile_picture value is stored
print("\n[5] Check DB state:")
resp = requests.get(f"{API_URL}/users/{TEST_USER}")
profile_pic = resp.json().get("profile_picture")
print(f"    profile_picture in DB: {profile_pic}")

if profile_pic == "default":
    print("\n    >>> DB says 'default' but API returns 200")
    print("        This means the file still exists on disk!")
    print("        Railway volume might not have been cleared")
else:
    print(f"\n    >>> DB still has value: {profile_pic}")
    print("        The delete operation might have failed")

print("\n" + "=" * 70)
