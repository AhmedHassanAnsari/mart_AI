import requests
import json
from db.manager import DBManager

BASE_URL = "http://localhost:8000"

def test_auth_flow():
    # Clear customers table for clean test
    manager = DBManager()
    conn = manager.get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM customers")
    finally:
        conn.close()

    # 1. Signup
    print("Testing Signup...")
    signup_data = {
        "email": "test_customer@example.com",
        "password": "SecurePassword123",
        "profile_info": {"name": "Test User"}
    }
    res = requests.post(f"{BASE_URL}/auth/signup", json=signup_data)
    print(f"Signup status: {res.status_code}, response: {res.json()}")
    if res.status_code != 201:
        print("Signup failed")
        return

    # 2. Login
    print("\nTesting Login...")
    # FastAPI OAuth2PasswordRequestForm expects form-data, not JSON
    login_data = {
        "username": "test_customer@example.com",
        "password": "SecurePassword123"
    }
    res = requests.post(f"{BASE_URL}/auth/login", data=login_data)
    print(f"Login status: {res.status_code}, response: {res.json()}")
    if res.status_code != 200:
        print("Login failed")
        return

    token = res.json()["access_token"]

    # 3. Try Checkout WITHOUT token (should fail)
    print("\nTesting Checkout without token...")
    checkout_data = {
        "tenant_id": "788aeac9-8539-4ad5-8fc7-356b4d1633da", # Using ID from previous test
        "items": [
            {"item_id": "7fc0f7ca-d8d8-439c-8a74-fec47be17c8d", "quantity": 1, "sale_price": 50000}
        ]
    }
    res = requests.post(f"{BASE_URL}/ingestion/checkout", json=checkout_data)
    print(f"Checkout without token status: {res.status_code}, response: {res.json()}")
    if res.status_code != 401:
        print("FAILURE: Checkout should have been blocked by auth wall")
        return

    # 4. Try Checkout WITH token (should succeed)
    print("\nTesting Checkout with token...")
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.post(f"{BASE_URL}/ingestion/checkout", json=checkout_data, headers=headers)
    print(f"Checkout with token status: {res.status_code}, response: {res.json()}")
    if res.status_code != 200:
        print("FAILURE: Checkout failed with valid token")
        return

    print("\n--- AUTH FLOW VERIFIED SUCCESSFULLY ---")

if __name__ == "__main__":
    test_auth_flow()
