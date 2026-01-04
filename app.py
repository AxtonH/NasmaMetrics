from dotenv import load_dotenv
load_dotenv()

import os

import os
from datetime import date, timedelta
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from database import Database
from odoo_client import get_planning_coverage_by_month

import json
ODOO_URL = os.getenv("ODOO_URL")
ODOO_DB = os.getenv("ODOO_DB")
ODOO_USERNAME = os.getenv("ODOO_USERNAME")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD")


app = Flask(__name__)
CORS(app)

# Initialize database connection
db = Database()


@app.route("/")
def index():
    """Render the main dashboard page"""
    return render_template("index.html")


@app.route("/api/active-users")
def get_active_users():
    """API endpoint for active users by month"""
    try:
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        data = db.get_active_users_by_month(start_date, end_date)
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/requests")
def get_requests():
    """API endpoint for all-time requests"""
    try:
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        data = db.get_all_time_requests(start_date, end_date)
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/adoption")
def get_adoption():
    """API endpoint for Nasma adoption count"""
    try:
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        count = db.get_nasma_adoption(start_date, end_date)
        return jsonify({"success": True, "data": {"count": count}})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/adoption-by-department")
def get_adoption_by_department():
    """API endpoint for adoption metrics per department"""
    try:
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        data = db.get_adoption_by_department(start_date, end_date)
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/messages")
def get_messages():
    """API endpoint for messages count"""
    try:
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        summary = db.get_monthly_messages_summary(start_date, end_date)
        return jsonify({"success": True, "data": summary})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/log-hours")
def get_log_hours_users():
    """API endpoint for users who logged hours via Nasma"""
    try:
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        data = db.get_log_hours_users(start_date, end_date)
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/request-success-rates")
def get_request_success_rates():
    """API endpoint for per-request success percentages"""
    try:
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        data = db.get_request_success_rates(start_date, end_date)
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/satisfaction", methods=["GET", "POST"])
def satisfaction():
    """API endpoint for overall satisfaction (GET and POST)"""
    try:
        if request.method == "POST":
            data = request.get_json()
            satisfaction_value = data.get("value", "")
            success = db.save_satisfaction(satisfaction_value)
            if success:
                return jsonify({"success": True, "message": "Satisfaction updated"})
            else:
                return jsonify({"success": False, "error": "Failed to save"}), 500
        else:
            data = db.get_satisfaction_data()
            return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/ease-comparison", methods=["GET", "POST"])
def ease_comparison():
    """API endpoint for ease comparison data (GET and POST)"""
    try:
        if request.method == "POST":
            data = request.get_json()
            odoo_data = data.get("odoo", [])
            nasma_data = data.get("nasma", [])
            success = db.save_ease_comparison_data(odoo_data, nasma_data)
            if success:
                return jsonify({"success": True, "message": "Ease comparison updated"})
            else:
                return jsonify({"success": False, "error": "Failed to save"}), 500
        else:
            data = db.get_ease_comparison_data()
            return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/activities-today")
def get_activities_today():
    """API endpoint for Nasma activities today"""
    try:
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        data = db.get_nasma_activities_today(start_date, end_date)
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
        
@app.route("/api/odoo/planning-coverage")
def api_odoo_planning_coverage():
    """
    Return planning coverage (monthly + weekly) for roughly the last 12 months.
    """
    try:
        today = date.today()
        first_of_current = today.replace(day=1)

        months_back = 11
        year = first_of_current.year
        month = first_of_current.month - months_back
        while month <= 0:
            month += 12
            year -= 1
        start_date_dt = date(year, month, 1)

        next_month = (first_of_current.replace(day=28) + timedelta(days=4)).replace(day=1)
        end_date_dt = next_month - timedelta(days=1)

        start_date_str = start_date_dt.strftime("%Y-%m-%d")
        end_date_str = end_date_dt.strftime("%Y-%m-%d")

        data = get_planning_coverage_by_month(start_date_str, end_date_str)
        return jsonify({"ok": True, "data": data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/planning-coverage")
def planning_coverage_page():
    """Dedicated page for enlarged planning coverage chart."""
    return render_template("planning.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug_env = os.environ.get("FLASK_DEBUG", "True")
    debug = debug_env.lower() in ("1", "true", "yes")
    app.run(debug=debug, host="0.0.0.0", port=port)

