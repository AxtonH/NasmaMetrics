# Nasma Metrics Dashboard

A Python Flask dashboard application that visualizes metrics from the Nasma application stored in Supabase.

## Features

1. **Active Users Chart** - Month-by-month bar chart showing unique active users from the `refresh_tokens` table
2. **Requests Made Chart** - Bar chart displaying all-time requests grouped by `metric_type` from `session_metrics`
3. **Nasma Adoption** - Card displaying the total number of active users
4. **Overall Satisfaction** - Editable text input for overall satisfaction score
5. **Messages Sent** - Card showing total count of messages from `chat_messages` table
6. **Ease Comparison** - Line chart comparing Nasma vs Odoo ease of use with editable data points

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. (Optional) Create a `.env` file with your Supabase credentials:
```bash
cp .env.example .env
```

The application will use default values from `config.py` if `.env` is not present.

## Running the Application

Start the Flask development server:
```bash
python app.py
```

The dashboard will be available at `http://localhost:5000`

## Project Structure

```
NasmaDash/
├── app.py                 # Flask application with API endpoints
├── config.py              # Configuration and Supabase credentials
├── database.py            # Database queries and operations
├── requirements.txt       # Python dependencies
├── templates/
│   └── index.html         # Main dashboard HTML template
└── static/
    ├── css/               # Custom CSS (if needed)
    └── js/
        └── dashboard.js   # JavaScript for charts and interactivity
```

## Database Schema

The application expects the following Supabase tables:
- `refresh_tokens` - For active users tracking
- `session_metrics` - For requests tracking
- `chat_messages` - For messages count
- `employees_reference` - Employee reference data
- `chat_threads` - Chat thread data

## API Endpoints

- `GET /` - Render dashboard page
- `GET /api/active-users` - Get active users by month
- `GET /api/requests` - Get all-time requests
- `GET /api/adoption` - Get Nasma adoption count
- `GET /api/messages` - Get messages count
- `GET /api/satisfaction` - Get overall satisfaction
- `POST /api/satisfaction` - Save overall satisfaction
- `GET /api/ease-comparison` - Get ease comparison data
- `POST /api/ease-comparison` - Save ease comparison data

## Technologies Used

- **Backend**: Python Flask
- **Frontend**: HTML5, Tailwind CSS, Chart.js
- **Database**: Supabase (PostgreSQL)
- **Styling**: Tailwind CSS CDN

