"""
Flask application for Nasma Dashboard
Provides API endpoints for dashboard data
"""
import os
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from database import Database
import json

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
        data = db.get_active_users_by_month()
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/requests")
def get_requests():
    """API endpoint for all-time requests"""
    try:
        data = db.get_all_time_requests()
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/adoption")
def get_adoption():
    """API endpoint for Nasma adoption count"""
    try:
        count = db.get_nasma_adoption()
        return jsonify({"success": True, "data": {"count": count}})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/messages")
def get_messages():
    """API endpoint for messages count"""
    try:
        summary = db.get_monthly_messages_summary()
        return jsonify({"success": True, "data": summary})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/log-hours")
def get_log_hours_users():
    """API endpoint for users who logged hours via Nasma"""
    try:
        data = db.get_log_hours_users()
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
        data = db.get_nasma_activities_today()
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug_env = os.environ.get("FLASK_DEBUG", "True")
    debug = debug_env.lower() in ("1", "true", "yes")
    app.run(debug=debug, host="0.0.0.0", port=port)

