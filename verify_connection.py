from database import Database
import sys

def test_connection():
    print("Testing Supabase connection...")
    try:
        db = Database()
        # Try a simple query
        print("Attempting to fetch request count...")
        requests = db.get_all_time_requests()
        print(f"Successfully fetched {len(requests)} request types.")
        print("Connection successful!")
        return True
    except Exception as e:
        print(f"Connection failed: {e}")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
