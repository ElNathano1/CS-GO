import requests

BASE_URL = "https://cs-go-production.up.railway.app"

for account in [
    {"username": "biggo", "password": "azertyuiop", "name": "S4c3 B1gG0"},
    {"username": "rafouloulou", "password": "rafouloulou", "name": "R4f0u10u10u"},
    {"username": "angie", "password": "Angie979902", "name": "Angie"},
]:
    response = requests.post(f"{BASE_URL}/users/", json=account)
    if response.status_code == 200:
        print(f"Login successful for {account['username']}")
    else:
        print(f"Login failed for {account['username']}: {response.text}")
