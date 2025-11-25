from dotenv import load_dotenv
load_dotenv()

import os
import requests

ODOO_URL = os.getenv("ODOO_URL").rstrip("/")
ODOO_DB = os.getenv("ODOO_DB")
ODOO_USERNAME = os.getenv("ODOO_USERNAME")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD")

session = requests.Session()

# Disable SSL verify only for staging
session.verify = False

login_url = f"{ODOO_URL}/web/login"

print("Logging in to:", login_url)

payload = {
    "login": ODOO_USERNAME,
    "password": ODOO_PASSWORD,
    "db": ODOO_DB
}

headers = {
    "Content-Type": "application/x-www-form-urlencoded"
}

try:
    response = session.post(login_url, data=payload, headers=headers)
    print("\nLogin status code:", response.status_code)

    # Successful login redirects to /web
    if "/web" in response.url or response.status_code == 200:
        print("✅ Logged in successfully!")
        print("Session cookies:", session.cookies)
    else:
        print("❌ Login failed. Server response URL:", response.url)
        print("HTML returned:\n", response.text[:500])

except Exception as e:
    print("\n❌ Error:", type(e).__name__, "->", e)
