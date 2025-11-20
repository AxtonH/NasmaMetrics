from database import Database
from datetime import datetime
import json

def debug_data():
    print(f"Current Server Time: {datetime.now()}")
    print(f"Current UTC Time: {datetime.utcnow()}")
    
    db = Database()
    try:
        # Fetch last 10 metrics
        print("\nFetching last 10 metrics...")
        response = (
            db.client.table(db.SUPABASE_METRIC_TABLE if hasattr(db, 'SUPABASE_METRIC_TABLE') else "session_metrics")
            .select("*")
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )
        
        data = response.data
        print(f"Found {len(data)} records.")
        for item in data:
            print(f"ID: {item.get('id')}, Created At: {item.get('created_at')}, Type: {item.get('metric_type')}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_data()
