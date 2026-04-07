import requests
import json
import time

# Wait for server to start
time.sleep(3)

# Test registration
print("=" * 50)
print("Testing Registration")
print("=" * 50)
payload = {
    'username': 'testfinal',
    'email': 'testfinal@example.com',
    'password': 'Test1234!',
    'name': 'Test Final',
    'role': 'customer'
}

try:
    r = requests.post('http://localhost:8000/api/auth/register/', json=payload, timeout=5)
    print(f"Status: {r.status_code}")
    if r.status_code == 201:
        print("✅ Registration successful!")
        user_data = r.json()
        print(f"   User: {user_data.get('email')}")
        print(f"   Role: {user_data.get('role')}")
    else:
        print("❌ Registration failed")
        print(f"   Response: {r.json()}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test login
print("\n" + "=" * 50)
print("Testing Login")
print("=" * 50)
login_payload = {
    'username': 'testfinal',
    'password': 'Test1234!'
}

try:
    r = requests.post('http://localhost:8000/api/auth/login/', json=login_payload, timeout=5)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        print("✅ Login successful!")
        login_data = r.json()
        print(f"   Access token: {'access' in login_data}")
        print(f"   User email: {login_data.get('user', {}).get('email')}")
    else:
        print("❌ Login failed")
        print(f"   Response: {r.json()}")
except Exception as e:
    print(f"❌ Error: {e}")
