from database import Database
import json

def test_query():
    print("Testing get_nasma_activities_today()...")
    db = Database()
    try:
        results = db.get_nasma_activities_today()
        print(f"Results: {json.dumps(results, indent=2)}")
        if not results:
            print("FAILURE: Returned empty list.")
        else:
            print(f"SUCCESS: Found {len(results)} categories.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_query()
