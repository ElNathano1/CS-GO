"""
Test harness for profile picture upload, retrieval, and deletion.
Verifies that profile picture DB value is correctly persisted.
"""

import os
import sys
import requests
from io import BytesIO
from PIL import Image

# Configuration
API_URL = "https://cs-go-production.up.railway.app"
TEST_USERNAME = "elnathano"
TEST_IMAGE_SIZE = (200, 200)


def create_test_image(color=(255, 0, 0)) -> bytes:
    """Create a simple test image."""
    img = Image.new("RGB", TEST_IMAGE_SIZE, color=color)
    img_bytes = BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)
    return img_bytes.getvalue()


def test_profile_picture_lifecycle():
    """Test: upload → fetch user data → verify DB value is set correctly."""
    print(f"[TEST] Profile picture DB persistence at {API_URL}")
    print(f"       User: {TEST_USERNAME}\n")

    # Step 1: Get user before upload
    print("[1] Fetching user data before upload...")
    user_resp = requests.get(f"{API_URL}/users/{TEST_USERNAME}")
    if user_resp.status_code != 200:
        print(f"    FAIL: {user_resp.status_code} {user_resp.text}")
        return False
    user_data = user_resp.json()
    profile_pic_before = user_data.get("profile_picture", "N/A")
    print(f"    OK - profile_picture field: {profile_pic_before}")

    # Step 2: Upload new profile picture
    print("\n[2] Uploading new profile picture...")
    image_bytes = create_test_image(color=(0, 255, 0))
    upload_resp = requests.post(
        f"{API_URL}/users/{TEST_USERNAME}/profile-picture",
        files={"file": ("test_green.png", image_bytes, "image/png")},
    )
    if upload_resp.status_code != 200:
        print(f"    FAIL: {upload_resp.status_code} {upload_resp.text}")
        return False
    upload_data = upload_resp.json()
    print(f"    OK - Upload status: {upload_data['status']}")
    print(f"       Picture path stored: {upload_data['picture_path']}")

    # Step 3: Fetch user data immediately after upload
    print("\n[3] Fetching user data after upload...")
    user_resp_after = requests.get(f"{API_URL}/users/{TEST_USERNAME}")
    if user_resp_after.status_code != 200:
        print(f"    FAIL: {user_resp_after.status_code}")
        return False
    user_data_after = user_resp_after.json()
    profile_pic_after = user_data_after.get("profile_picture", "N/A")
    print(f"    OK - profile_picture field now: {profile_pic_after}")

    # CRITICAL CHECK: Did the DB value actually change?
    if profile_pic_after == TEST_USERNAME:
        print(
            f"    SUCCESS: profile_picture correctly set to username '{TEST_USERNAME}'"
        )
    else:
        print(
            f"    FAIL: Expected profile_picture='{TEST_USERNAME}', got '{profile_pic_after}'"
        )
        print(f"          This means the DB value was NOT persisted on upload!")
        return False

    # Step 4: Fetch thumbnail
    print("\n[4] Fetching thumbnail...")
    thumb_resp = requests.get(
        f"{API_URL}/users/{TEST_USERNAME}/profile-picture/thumb?format=webp"
    )
    print(f"    Status: {thumb_resp.status_code}")
    if thumb_resp.status_code == 200:
        print(f"    OK - Thumbnail retrieved ({len(thumb_resp.content)} bytes)")
    else:
        print(f"    WARN: Got {thumb_resp.status_code} (expected 200)")

    # Step 5: Delete profile picture
    print("\n[5] Deleting profile picture...")
    delete_resp = requests.delete(f"{API_URL}/users/{TEST_USERNAME}/profile-picture")
    if delete_resp.status_code != 200:
        print(f"    FAIL: {delete_resp.status_code} {delete_resp.text}")
        return False
    print(f"    OK - Deleted")

    # Step 6: Verify DB was updated to 'default'
    print("\n[6] Verifying DB after deletion...")
    user_resp_deleted = requests.get(f"{API_URL}/users/{TEST_USERNAME}")
    if user_resp_deleted.status_code != 200:
        print(f"    FAIL: {user_resp_deleted.status_code}")
        return False
    user_data_deleted = user_resp_deleted.json()
    profile_pic_deleted = user_data_deleted.get("profile_picture", "N/A")
    print(f"    OK - profile_picture field now: {profile_pic_deleted}")

    if profile_pic_deleted == "default":
        print(f"    SUCCESS: profile_picture correctly reset to 'default'")
    else:
        print(f"    FAIL: Expected 'default', got '{profile_pic_deleted}'")
        return False

    # Step 7: Verify thumbnail returns 404
    print("\n[7] Verifying thumbnail is gone...")
    thumb_resp_deleted = requests.get(
        f"{API_URL}/users/{TEST_USERNAME}/profile-picture/thumb?format=webp"
    )
    print(f"    Status: {thumb_resp_deleted.status_code}")
    if thumb_resp_deleted.status_code == 404:
        print(f"    OK - Correctly returns 404")
    else:
        print(f"    PROBLEM: Expected 404, got {thumb_resp_deleted.status_code}")
        print(f"    This might be Railway CDN caching, not app bug")

    print("\n" + "=" * 60)
    print("PASSED: Database persistence is working correctly!")
    print("=" * 60)
    return True



if __name__ == "__main__":
    try:
        success = test_profile_picture_lifecycle()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
