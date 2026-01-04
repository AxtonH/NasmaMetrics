"""
Configuration file for Nasma Dashboard
Contains Supabase connection credentials and table names
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://xtyyoqcgwzexjlupkuto.supabase.co")
SUPABASE_SERVICE_ROLE = os.getenv(
    "SUPABASE_SERVICE_ROLE",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inh0eXlvcWNnd3pleGpsdXBrdXRvIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MTYzMjEwMCwiZXhwIjoyMDc3MjA4MTAwfQ.FJUlBbpVuF65hFRZN06PS4d1s54IMWFMkh-yAC8lr2I"
)
SUPABASE_POSTGRES_URL = os.getenv("SUPABASE_POSTGRES_URL")

# Table Names
SUPABASE_METRIC_TABLE = os.getenv("SUPABASE_METRIC_TABLE", "session_metrics")
SUPABASE_THREAD_TABLE = os.getenv("SUPABASE_THREAD_TABLE", "chat_threads")
SUPABASE_MESSAGE_TABLE = os.getenv("SUPABASE_MESSAGE_TABLE", "chat_messages")
SUPABASE_REFRESH_TOKEN_TABLE = "refresh_tokens"
SUPABASE_EMPLOYEES_TABLE = "employees_reference"

