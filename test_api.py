import requests

BASE_URL = "https://CS-GO.up.railway.app"

# Créer un utilisateur
res = requests.post(
    f"{BASE_URL}/users/",
    json={"username": "test2", "password": "test2", "name": "Test-Man 2"},
)

print(res)
