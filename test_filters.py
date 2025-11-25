import urllib.request
import json
import datetime

BASE_URL = "http://127.0.0.1:5000"

def get_json(url):
    try:
        with urllib.request.urlopen(url) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def test_filters():
    print("Testing Global Time Frame Filters...")
    
    # Calculate dates
    today = datetime.date.today()
    seven_days_ago = today - datetime.timedelta(days=7)
    
    start_date = seven_days_ago.isoformat()
    end_date = today.isoformat()
    
    print(f"Date Range: {start_date} to {end_date}")
    
    # Test 1: Active Users
    print("\n1. Testing Active Users...")
    all_time = get_json(f"{BASE_URL}/api/active-users")
    filtered = get_json(f"{BASE_URL}/api/active-users?start_date={start_date}&end_date={end_date}")
    
    if all_time and filtered:
        print(f"All Time Count: {len(all_time.get('data', []))}")
        print(f"Filtered Count: {len(filtered.get('data', []))}")
        if len(filtered.get('data', [])) <= len(all_time.get('data', [])):
            print("PASS: Filtered count is <= All Time count")
        else:
            print("FAIL: Filtered count is > All Time count (unexpected)")
    else:
        print("FAIL: Could not fetch data")

    # Test 2: Requests
    print("\n2. Testing Requests...")
    all_time_req = get_json(f"{BASE_URL}/api/requests")
    filtered_req = get_json(f"{BASE_URL}/api/requests?start_date={start_date}&end_date={end_date}")
    
    if all_time_req and filtered_req:
        # Sum up values
        total_all = sum(item['value'] for item in all_time_req.get('data', []))
        total_filtered = sum(item['value'] for item in filtered_req.get('data', []))
        
        print(f"All Time Total Requests: {total_all}")
        print(f"Filtered Total Requests: {total_filtered}")
        
        if total_filtered <= total_all:
            print("PASS: Filtered total is <= All Time total")
        else:
            print("FAIL: Filtered total is > All Time total")
    else:
        print("FAIL: Could not fetch data")

    # Test 3: Activities Today (Summary)
    print("\n3. Testing Activities Summary...")
    # Without params (defaults to today in backend logic, or all time if logic changed?)
    # Wait, my logic defaults to today if NO params.
    # If I want ALL TIME, I need to handle that. 
    # But for this test, let's check if passing params works.
    
    filtered_act = get_json(f"{BASE_URL}/api/activities-today?start_date={start_date}&end_date={end_date}")
    if filtered_act:
        print(f"Filtered Activities: {filtered_act.get('data', [])}")
        print("PASS: Successfully fetched filtered activities")
    else:
        print("FAIL: Could not fetch activities")

if __name__ == "__main__":
    test_filters()
