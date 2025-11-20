import requests
import sys

BASE_URL = "http://127.0.0.1:5000"

def test_endpoints():
    endpoints = [
        "/api/requests",
        "/api/active-users",
        "/api/adoption"
    ]
    
    all_success = True
    
    print(f"Testing API endpoints at {BASE_URL}...")
    
    for endpoint in endpoints:
        url = f"{BASE_URL}{endpoint}"
        try:
            print(f"Testing {endpoint}...")
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    print(f"  SUCCESS: {endpoint} returned data.")
                else:
                    print(f"  FAILURE: {endpoint} returned success=False. Error: {data.get('error')}")
                    all_success = False
            else:
                print(f"  FAILURE: {endpoint} returned status {response.status_code}")
                all_success = False
        except Exception as e:
            print(f"  ERROR: Could not connect to {endpoint}. Is the server running? {e}")
            all_success = False
            
    return all_success

if __name__ == "__main__":
    success = test_endpoints()
    sys.exit(0 if success else 1)
