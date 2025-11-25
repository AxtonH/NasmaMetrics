from dotenv import load_dotenv
load_dotenv()

import os
import requests
import urllib3
from datetime import datetime, date, timedelta

# Ignore SSL warnings for Odoo staging
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---- ENV VARS ----
ODOO_URL = os.getenv("ODOO_URL", "").rstrip("/")
ODOO_DB = os.getenv("ODOO_DB")
ODOO_USERNAME = os.getenv("ODOO_USERNAME")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD")

if not all([ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD]):
    raise RuntimeError("One or more Odoo env vars are missing. Check your .env file.")


# --------------------------------------------------------------------
#  AUTH HELPERS
# --------------------------------------------------------------------
def _login_session() -> requests.Session:
    """
    Create a logged-in session to Odoo using /web/session/authenticate (JSON-RPC).
    """
    session = requests.Session()
    session.verify = False  # staging cert

    auth_url = f"{ODOO_URL}/web/session/authenticate"
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "db": ODOO_DB,
            "login": ODOO_USERNAME,
            "password": ODOO_PASSWORD,
        },
    }
    headers = {"Content-Type": "application/json"}

    print(f"[auth] POST {auth_url}")
    resp = session.post(auth_url, json=payload, headers=headers)
    print("[auth] HTTP status:", resp.status_code)

    print("\n----------- AUTH RAW RESPONSE (first 300 chars) -----------")
    print(resp.text[:300])
    print("-----------------------------------------------------------\n")

    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"Odoo auth error: {data['error']}")

    result = data.get("result") or {}
    uid = result.get("uid")
    if not uid:
        raise RuntimeError(f"Odoo auth failed, uid is {uid}")

    print(f"[auth] ✅ Authenticated as UID {uid}")
    print("[auth] Session cookies:", session.cookies)
    return session


def _json_call(
    session: requests.Session,
    model: str,
    method: str,
    args: list | None = None,
    kwargs: dict | None = None,
):
    """
    Helper to call /web/dataset/call_kw with consistent error handling.
    """
    dataset_url = f"{ODOO_URL}/web/dataset/call_kw"
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "model": model,
            "method": method,
            "args": args or [],
            "kwargs": kwargs or {},
        },
        "id": 1,
    }

    print(f"[json_call] {model}.{method} args={len(payload['params']['args'])}")
    resp = session.post(
        dataset_url,
        json=payload,
        headers={"Content-Type": "application/json"},
    )
    resp.raise_for_status()

    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"Odoo error calling {model}.{method}: {data['error']}")

    return data.get("result")


# --------------------------------------------------------------------
#  UTIL: MONTH PARSING / LABELS
# --------------------------------------------------------------------
def _month_label_from_row(row: dict) -> str | None:
    """
    Given a read_group row, extract a canonical month label 'YYYY-MM'.

    Your Odoo rows look like:
      'date:month': 'September 2024',
      '__range': {'date:month': {'from': '2024-09-01', 'to': '2024-10-01'}}

    We'll first try the __range.from value, then fall back to date:month string.
    """
    # 1) Try to use the __range -> 'from' date
    range_info = row.get("__range", {}).get("date:month")
    if isinstance(range_info, dict):
        from_str = range_info.get("from")
        if isinstance(from_str, str):
            try:
                dt = datetime.strptime(from_str, "%Y-%m-%d")
                return dt.strftime("%Y-%m")  # '2024-09'
            except Exception:
                pass

    # 2) Fallback: parse the 'date:month' string itself
    month_str = row.get("date:month")
    if isinstance(month_str, str):
        for fmt in ("%Y-%m-%d", "%B %Y", "%b %Y"):  # '2024-09-01', 'September 2024', 'Sep 2024'
            try:
                dt = datetime.strptime(month_str, fmt)
                return dt.strftime("%Y-%m")
            except Exception:
                continue

    return None


def _daterange(start: date, end: date):
    """
    Yield each date between start and end (inclusive).
    """
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def _to_date(dt_str: str) -> date | None:
    """
    Parse an Odoo datetime string into a date.
    """
    if not dt_str or not isinstance(dt_str, str):
        return None

    normalized = dt_str.replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(normalized, fmt).date()
        except ValueError:
            continue
    return None


def _get_time_off_task_ids(session: requests.Session) -> list[int]:
    """
    Fetch IDs of tasks whose name matches 'Time Off'.
    These tasks should be excluded from logged-hours aggregation.
    """
    dataset_url = f"{ODOO_URL}/web/dataset/call_kw"
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "model": "project.task",
            "method": "search",
            "args": [
                [["name", "ilike", "Time Off"]],
            ],
            "kwargs": {},
        },
        "id": 1,
    }

    try:
        resp = session.post(
            dataset_url,
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        data = resp.json()
    except Exception as exc:
        print(f"[time_off] Failed to fetch 'Time Off' task IDs: {exc}")
        return []

    if "error" in data:
        print("[time_off] Odoo returned an error when fetching task IDs:")
        print(data["error"])
        return []

    task_ids = data.get("result") or []
    if not isinstance(task_ids, list):
        return []

    print(f"[time_off] Found {len(task_ids)} time-off task IDs: {task_ids}")
    return task_ids


# --------------------------------------------------------------------
#  PLANNING COVERAGE
# --------------------------------------------------------------------
def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def get_planning_coverage_by_month(
    start_date: str,
    end_date: str,
) -> dict:
    """
    Compute planning coverage between planning.slot and account.analytic.line.

    - Only planning slots with a subtask (x_studio_sub_task_1) are counted.
    - Each day in a planning span counts as 1 planned "task-day".
    - A planned task-day is "logged" if there is at least one timesheet entry
      for the same (date, employee, subtask) combination.
    - Returns dict with "monthly" and "weekly" lists of dicts:
      {"period": "YYYY-MM" or "YYYY-Www", "planned_days": int, "logged_days": int, "coverage_pct": float}
    """
    global_start = _parse_date(start_date)
    global_end = _parse_date(end_date)
    if global_end < global_start:
        raise ValueError("end_date must be on or after start_date")

    session = _login_session()

    # --- Planning slots ---
    planning_domain = [
        ["start_datetime", "<=", f"{end_date} 23:59:59"],
        ["end_datetime", ">=", f"{start_date} 00:00:00"],
        ["x_studio_sub_task_1", "!=", False],
    ]
    planning_fields = [
        "id",
        "start_datetime",
        "end_datetime",
        "employee_id",
        "x_studio_sub_task_1",
    ]
    planning_slots = _json_call(
        session,
        "planning.slot",
        "search_read",
        args=[planning_domain, planning_fields],
        kwargs={"limit": 0},
    ) or []
    print(f"[planning_coverage] Planning slots fetched: {len(planning_slots)}")

    # --- Timesheets ---
    ts_domain = [
        ["date", ">=", start_date],
        ["date", "<=", end_date],
        ["task_id", "!=", False],
    ]
    ts_fields = ["date", "employee_id", "task_id"]
    timesheets = _json_call(
        session,
        "account.analytic.line",
        "search_read",
        args=[ts_domain, ts_fields],
        kwargs={"limit": 0},
    ) or []

    logged_keys = set()
    for line in timesheets:
        day_str = line.get("date")
        employee = line.get("employee_id") or []
        task = line.get("task_id") or []

        if not (day_str and employee and task):
            continue

        try:
            day = datetime.strptime(day_str, "%Y-%m-%d").date()
        except ValueError:
            continue

        employee_id = employee[0] if isinstance(employee, list) else None
        task_id = task[0] if isinstance(task, list) else None

        if not (employee_id and task_id):
            continue

        logged_keys.add((day, employee_id, task_id))

    planned_keys = set()
    coverage_by_month: dict[str, dict] = {}
    coverage_by_week: dict[str, dict] = {}

    for slot in planning_slots:
        slot_id = slot.get("id")
        start_str = slot.get("start_datetime")
        end_str = slot.get("end_datetime")
        employee = slot.get("employee_id") or []
        subtask = slot.get("x_studio_sub_task_1") or []

        slot_start = _to_date(start_str)
        slot_end = _to_date(end_str)
        employee_id = employee[0] if isinstance(employee, list) and employee else None
        subtask_id = subtask[0] if isinstance(subtask, list) and subtask else None

        if not all([slot_id, slot_start, slot_end, employee_id, subtask_id]):
            continue

        clamped_start = max(slot_start, global_start)
        clamped_end = min(slot_end, global_end)
        if clamped_end < clamped_start:
            continue

        for day in _daterange(clamped_start, clamped_end):
            key = (day, employee_id, subtask_id)
            month_key = day.strftime("%Y-%m")
            entry = coverage_by_month.setdefault(
                month_key,
                {
                    "period": month_key,
                    "planned_days": 0,
                    "logged_days": 0,
                    "planned_slot_ids": set(),
                    "logged_slot_ids": set(),
                },
            )
            entry["planned_slot_ids"].add(slot_id)
            if key in logged_keys:
                entry["logged_slot_ids"].add(slot_id)

            iso_year, iso_week, _ = day.isocalendar()
            week_key = f"{iso_year}-W{iso_week:02d}"
            week_entry = coverage_by_week.setdefault(
                week_key,
                {"period": week_key, "planned_days": 0, "logged_days": 0},
            )

            if key in planned_keys:
                continue

            planned_keys.add(key)
            entry["planned_days"] += 1
            if key in logged_keys:
                entry["logged_days"] += 1

            week_entry["planned_days"] += 1
            if key in logged_keys:
                week_entry["logged_days"] += 1

    print(
        "[planning_coverage] Planned keys:",
        len(planned_keys),
        "| Logged keys:",
        len(logged_keys),
    )

    def finalize(entries_map: dict[str, dict], include_slots: bool = False) -> list[dict]:
        results = []
        for entry in entries_map.values():
            planned = entry["planned_days"]
            logged = entry["logged_days"]
            entry["coverage_pct"] = (logged / planned * 100.0) if planned else 0.0
            if include_slots:
                planned_slots = len(entry.get("planned_slot_ids", set()))
                logged_slots = len(entry.get("logged_slot_ids", set()))
                entry["planned_slots"] = planned_slots
                entry["logged_slots"] = logged_slots
                entry.pop("planned_slot_ids", None)
                entry.pop("logged_slot_ids", None)
            results.append(entry)
        results.sort(key=lambda item: item["period"])
        return results

    monthly_results = finalize(coverage_by_month, include_slots=True)
    weekly_results = finalize(coverage_by_week)

    print(
        "[planning_coverage] Monthly periods:",
        [item["period"] for item in monthly_results],
    )
    print(
        "[planning_coverage] Weekly periods:",
        [item["period"] for item in weekly_results],
    )

    return {"monthly": monthly_results, "weekly": weekly_results}


# --------------------------------------------------------------------
#  CORE FUNCTION
# --------------------------------------------------------------------
def get_monthly_hours(start_date: str = "2024-01-01"):
    """
    Return a list of {month: 'YYYY-MM', total_hours: float}
    from account.analytic.line, excluding time-off tasks,
    starting from the given start_date (inclusive).
    """
    session = _login_session()
    dataset_url = f"{ODOO_URL}/web/dataset/call_kw"

    time_off_task_ids = _get_time_off_task_ids(session)

    # Filter: date >= start_date AND not a time-off task
    domain = [
        ["date", ">=", start_date],
        ["task_id.is_timeoff_task", "=", False],
    ]

    if time_off_task_ids:
        domain.append(["task_id", "not in", time_off_task_ids])

    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "model": "account.analytic.line",
            "method": "read_group",
            "args": [
                domain,
                ["unit_amount"],         # field to sum
                ["date:month"],          # group by month
            ],
            "kwargs": {"lazy": False},
        },
        "id": 1,
    }

    print(f"[read_group] POST {dataset_url}")
    resp = session.post(
        dataset_url,
        json=payload,
        headers={"Content-Type": "application/json"},
    )

    print("[read_group] HTTP status:", resp.status_code)

    print("\n----------- ODOO RAW RESPONSE (first 400 chars) -----------")
    print(resp.text[:400])
    print("-----------------------------------------------------------\n")

    try:
        data = resp.json()
    except Exception as e:
        print("[read_group] ❌ Failed to decode JSON:", e)
        return []

    if "error" in data:
        print("[read_group] ❌ Odoo returned an error:")
        print(data["error"])
        return []

    rows = data.get("result", [])
    print(f"[read_group] Got {len(rows)} grouped rows from Odoo")

    # Aggregate per month
    month_totals: dict[str, float] = {}

    for row in rows:
        month_key = _month_label_from_row(row)
        if not month_key:
            continue

        hours = row.get("unit_amount") or 0.0
        try:
            hours = float(hours)
        except Exception:
            continue

        month_totals[month_key] = month_totals.get(month_key, 0.0) + hours

    # Convert to sorted list of dicts
    results = [
        {"month": month, "total_hours": total}
        for month, total in sorted(month_totals.items())
    ]

    print("[read_group] Final month totals:")
    for r in results:
        print("  ", r)

    return results


# --------------------------------------------------------------------
#  COMPAT WRAPPER (what your Flask route uses)
# --------------------------------------------------------------------
def get_monthly_hours_from_september():
    """
    Convenience wrapper for your Flask route.
    Hard-codes start date to 1st September 2024.
    """
    return get_monthly_hours(start_date="2024-09-01")


# --------------------------------------------------------------------
#  MANUAL TEST
# --------------------------------------------------------------------
if __name__ == "__main__":
    data = get_monthly_hours_from_september()
    print("\nMonthly hours (excluding time off):")
    for row in data:
        print(row)
