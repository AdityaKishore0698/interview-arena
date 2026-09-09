import requests

res1 = requests.post("http://localhost:8000/api/v1/auth/register", json={
    "email": "test@example.com",
    "password": "password",
    "display_name": "Test User"
})
print(res1.status_code, res1.text)

res2 = requests.post("http://localhost:8000/api/v1/auth/login", json={
    "email": "test@example.com",
    "password": "password"
})
print(res2.status_code, res2.text)

if res2.status_code == 200:
    token = res2.json()["access_token"]
    res3 = requests.get("http://localhost:8000/api/v1/auth/me", headers={
        "Authorization": f"Bearer {token}"
    })
    print(res3.status_code, res3.text)
