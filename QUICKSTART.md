# Quick Start Guide

## Installation Steps

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the application:**
   ```bash
   python app.py
   ```

3. **Open your browser:**
   Navigate to `http://localhost:5000`

## Features Overview

### 1. Active Users Chart
- Displays month-by-month unique active users
- Data sourced from `refresh_tokens` table (filtered by unique username)

### 2. Requests Made Chart
- Shows all-time requests grouped by `metric_type`
- Data sourced from `session_metrics` table

### 3. Nasma Adoption
- Displays total count of unique active users
- Calculated from `refresh_tokens` table

### 4. Overall Satisfaction
- Editable text input field
- Click "Save Satisfaction" to persist the value
- Stored in `satisfaction_data.json`

### 5. Messages Sent to Nasma
- Shows total count of messages
- Data sourced from `chat_messages` table

### 6. Ease Comparison Chart
- Line chart comparing Nasma vs Odoo
- Click "Edit Data" button to modify data points
- Add/remove data points for both tools
- Stored in `ease_comparison_data.json`

## Troubleshooting

### If you encounter Supabase connection errors:
- Verify your Supabase credentials in `config.py` or `.env` file
- Ensure your Supabase project is active and accessible

### If charts don't load:
- Check browser console for JavaScript errors
- Verify API endpoints are responding at `http://localhost:5000/api/*`

### If data appears empty:
- Verify your Supabase tables contain data
- Check that table names match your actual Supabase schema

## API Endpoints

- `GET /` - Dashboard page
- `GET /api/active-users` - Active users data
- `GET /api/requests` - Requests data
- `GET /api/adoption` - Adoption count
- `GET /api/messages` - Messages count
- `GET /api/satisfaction` - Get satisfaction value
- `POST /api/satisfaction` - Save satisfaction value
- `GET /api/ease-comparison` - Get ease comparison data
- `POST /api/ease-comparison` - Save ease comparison data

