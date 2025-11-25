from dotenv import load_dotenv
import os

load_dotenv()

print("ODOO_USERNAME:", os.getenv("ODOO_USERNAME"))
print("ODOO_PASSWORD:", os.getenv("ODOO_PASSWORD"))

