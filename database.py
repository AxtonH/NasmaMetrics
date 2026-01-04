"""
Database module for Supabase queries
Handles all database interactions for the Nasma Dashboard
"""
from supabase import create_client, Client
from config import (
    SUPABASE_URL,
    SUPABASE_SERVICE_ROLE,
    SUPABASE_METRIC_TABLE,
    SUPABASE_MESSAGE_TABLE,
    SUPABASE_REFRESH_TOKEN_TABLE,
    SUPABASE_EMPLOYEES_TABLE,
    SUPABASE_POSTGRES_URL,
)
from datetime import datetime
from typing import List, Dict, Any, Optional
import json

try:
    import psycopg
except ImportError:  # pragma: no cover - optional dependency
    psycopg = None


class Database:
    """Database handler for Supabase operations"""

    def __init__(self):
        """Initialize Supabase client"""
        self.client: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE)
        self._sql_conn_str: Optional[str] = SUPABASE_POSTGRES_URL if psycopg else None

    def _run_sql(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """
        Execute raw SQL against Supabase Postgres when a connection string is configured.
        """
        if not self._sql_conn_str:
            return None
        try:
            with psycopg.connect(self._sql_conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute(query)
                    columns = [desc[0] for desc in cur.description or []]
                    rows = cur.fetchall()
            result = [dict(zip(columns, row)) for row in rows]
            return result
        except Exception as exc:
            print(f"Error executing SQL query: {exc}")
            return None
    def get_active_users_by_month(
        self, start_date: str = None, end_date: str = None
    ) -> List[Dict[str, Any]]:
        """
        Get monthly active users calculated from chat_messages (role=user)
        Mirrors adoption query logic but returns month and active user counts only
        """
        try:
            # Fetch chat messages sent by users
            page_size = 1000
            start = 0
            all_messages = []

            while True:
                query = (
                    self.client.table(SUPABASE_MESSAGE_TABLE)
                    .select("metadata, created_at, role")
                    .eq("role", "user")
                )
                if start_date:
                    query = query.gte("created_at", start_date)
                if end_date:
                    # Append time to end_date to include the whole day if it's just a date
                    if len(end_date) == 10:
                        query = query.lte("created_at", f"{end_date} 23:59:59")
                    else:
                        query = query.lte("created_at", end_date)
                
                query = query.range(start, start + page_size - 1)
                response = query.execute()
                batch = response.data or []
                if not batch:
                    break
                all_messages.extend(batch)
                start += page_size

            monthly_users: Dict[str, Dict[str, Any]] = {}

            for message in all_messages:
                metadata = message.get("metadata") or {}
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except json.JSONDecodeError:
                        metadata = {}

                username = metadata.get("user_name") or metadata.get("username")
                created_at = message.get("created_at")

                if not username or not created_at:
                    continue

                if isinstance(created_at, str):
                    dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                else:
                    dt = created_at

                month_key = dt.strftime("%Y-%m")
                month_label = dt.strftime("%B %Y")

                if month_key not in monthly_users:
                    monthly_users[month_key] = {"month": month_label, "users": set()}

                monthly_users[month_key]["users"].add(username)

            result = []
            for month_key in sorted(monthly_users.keys()):
                result.append(
                    {
                        "month": monthly_users[month_key]["month"],
                        "active_users": len(monthly_users[month_key]["users"]),
                    }
                )

            return result
        except Exception as e:
            print(f"Error fetching active users: {e}")
            return []

    def get_all_time_requests(
        self, start_date: str = None, end_date: str = None
    ) -> List[Dict[str, Any]]:
        """
        Get all-time requests grouped by metric_type from session_metrics table
        Returns list of dictionaries with metric_type and count
        """
        try:
            # Fetch all session metrics with optional date filtering
            query = self.client.table(SUPABASE_METRIC_TABLE).select(
                "metric_type, created_at"
            )
            if start_date:
                query = query.gte("created_at", start_date)
            if end_date:
                if len(end_date) == 10:
                    query = query.lte("created_at", f"{end_date} 23:59:59")
                else:
                    query = query.lte("created_at", end_date)

            response = query.execute()

            # Count requests by metric_type
            request_counts = {}
            for metric in response.data:
                metric_type = metric.get("metric_type")
                if metric_type:
                    request_counts[metric_type] = request_counts.get(metric_type, 0) + 1

            # Convert to list format
            result = [
                {"attribute": key, "value": count}
                for key, count in sorted(
                    request_counts.items(), key=lambda x: x[1], reverse=True
                )
            ]

            return result
        except Exception as e:
            print(f"Error fetching requests: {e}")
            return []

    def get_nasma_adoption(self, start_date: str = None, end_date: str = None) -> int:
        """
        Get total number of active users (Nasma Adoption)
        Returns count of unique users from refresh_tokens
        """
        try:
            # Fetch all refresh tokens and count unique usernames
            query = self.client.table(SUPABASE_REFRESH_TOKEN_TABLE).select("username")
            
            if start_date:
                query = query.gte("created_at", start_date)
            if end_date:
                if len(end_date) == 10:
                    query = query.lte("created_at", f"{end_date} 23:59:59")
                else:
                    query = query.lte("created_at", end_date)
                    
            response = query.execute()

            unique_users = set()
            for token in response.data:
                if token.get("username"):
                    unique_users.add(token["username"])

            return len(unique_users)
        except Exception as e:
            print(f"Error fetching Nasma adoption: {e}")
            return 0

    def get_adoption_by_department(
        self, start_date: str = None, end_date: str = None
    ) -> List[Dict[str, Any]]:
        """
        Calculate adoption per department using Employee Name + Department columns,
        mirroring the provided SQL with case-insensitive joins and distinct counts.
        """
        def normalize_name(value: Any) -> str:
            """Lower-case and collapse whitespace to match SQL normalization."""
            if not value:
                return ""
            if not isinstance(value, str):
                value = str(value)
            return " ".join(value.split()).lower()

        sql_override = self._run_sql(
            """
            WITH employee_base AS (
              SELECT
                er."Employee Name" AS employee_name,
                er."Department"    AS department
              FROM employees_reference er
              WHERE er."Employee Name" NOT ILIKE '%omar%'
                AND er."Employee Name" NOT ILIKE '%saba%'
                AND er."Employee Name" NOT ILIKE '%sanad%'
            ),
            active_users AS (
              SELECT DISTINCT
                LOWER(sm.user_name) AS employee_name_lc
              FROM session_metrics sm
              WHERE sm.user_name IS NOT NULL
            ),
            adoption AS (
              SELECT
                eb.department,
                COUNT(DISTINCT eb.employee_name) AS total_employees,
                COUNT(
                  DISTINCT CASE
                    WHEN au.employee_name_lc = LOWER(eb.employee_name) THEN eb.employee_name
                  END
                ) AS active_users
              FROM employee_base eb
              LEFT JOIN active_users au
                ON au.employee_name_lc = LOWER(eb.employee_name)
              GROUP BY eb.department
            )
            SELECT
              department AS "Department",
              active_users AS "Active users",
              total_employees AS "Total employees",
              ROUND((active_users::numeric / NULLIF(total_employees, 0)) * 100, 1) AS "Adoption %"
            FROM adoption
            ORDER BY "Adoption %" DESC, "Active users" DESC;
            """
        )
        if sql_override is not None:
            return [
                {
                    "department": row.get("Department"),
                    "active_users": row.get("Active users", 0),
                    "total_employees": row.get("Total employees", 0),
                    "adoption_rate_percent": float(row.get("Adoption %", 0))
                    if row.get("Adoption %") is not None
                    else 0,
                }
                for row in sql_override
            ]

        try:
            excluded_terms = ("omar", "saba", "sanad")
            dept_members: Dict[str, set] = {}

            start = 0
            page_size = 1000
            while True:
                response = (
                    self.client.table(SUPABASE_EMPLOYEES_TABLE)
                    .select('"Employee Name","Department"')
                    .range(start, start + page_size - 1)
                    .execute()
                )
                batch = response.data or []
                if not batch:
                    break

                for row in batch:
                    raw_name = row.get("Employee Name")
                    name = raw_name.strip() if isinstance(raw_name, str) else raw_name
                    raw_department = row.get("Department") or "Unknown"
                    department = (
                        raw_department.strip()
                        if isinstance(raw_department, str)
                        else raw_department
                    ) or "Unknown"
                    if not name:
                        continue

                    normalized_name = normalize_name(name)
                    if not normalized_name:
                        continue
                    if any(term in normalized_name for term in excluded_terms):
                        continue

                    dept_members.setdefault(department, set()).add(name)

                if len(batch) < page_size:
                    break
                start += page_size

            # Collect active user keys from session_metrics
            active_name_keys: set = set()
            start = 0
            while True:
                query = self.client.table(SUPABASE_METRIC_TABLE).select("user_name")
                if start_date:
                    query = query.gte("created_at", start_date)
                if end_date:
                    if len(end_date) == 10:
                        query = query.lte("created_at", f"{end_date} 23:59:59")
                    else:
                        query = query.lte("created_at", end_date)

                response = query.range(start, start + page_size - 1).execute()
                batch = response.data or []
                if not batch:
                    break

                for row in batch:
                    user_name = row.get("user_name")
                    normalized = normalize_name(user_name)
                    if normalized:
                        active_name_keys.add(normalized)

                if len(batch) < page_size:
                    break
                start += page_size

            results: List[Dict[str, Any]] = []
            for department, members in dept_members.items():
                total = len(members)
                active = 0
                for name in members:
                    normalized = normalize_name(name)
                    if normalized and normalized in active_name_keys:
                        active += 1
                adoption_rate = round((active / total) * 100, 1) if total else 0
                results.append(
                    {
                        "department": department,
                        "active_users": active,
                        "total_employees": total,
                        "adoption_rate_percent": adoption_rate,
                    }
                )

            results.sort(
                key=lambda item: (-item["adoption_rate_percent"], -item["active_users"])
            )
            return results
        except Exception as e:
            print(f"Error fetching adoption by department: {e}")
            return []

    def get_monthly_messages_summary(
        self, start_date: str = None, end_date: str = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Build monthly totals and per-user message counts matching the requested SQL.
        Filters to role='user', requires user_name, and excludes specific substrings.
        """
        try:
            page_size = 1000
            start = 0
            all_messages = []

            while True:
                query = (
                    self.client.table(SUPABASE_MESSAGE_TABLE)
                    .select("metadata, created_at, role")
                    .eq("role", "user")
                )
                if start_date:
                    query = query.gte("created_at", start_date)
                if end_date:
                    if len(end_date) == 10:
                        query = query.lte("created_at", f"{end_date} 23:59:59")
                    else:
                        query = query.lte("created_at", end_date)

                response = query.range(start, start + page_size - 1).execute()
                batch = response.data or []
                if not batch:
                    break
                all_messages.extend(batch)
                start += page_size

            excluded_terms = ["omar", "saba", "sanad"]
            monthly_totals: Dict[str, Dict[str, Any]] = {}
            monthly_user_counts: Dict[str, Dict[str, Any]] = {}

            for message in all_messages:
                metadata = message.get("metadata") or {}
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except json.JSONDecodeError:
                        metadata = {}

                user_name = metadata.get("user_name") or metadata.get("username")
                if not user_name:
                    continue

                user_name_lower = user_name.lower()
                if any(term in user_name_lower for term in excluded_terms):
                    continue

                created_at = message.get("created_at")
                if not created_at:
                    continue

                if isinstance(created_at, str):
                    dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                else:
                    dt = created_at

                month_key = dt.strftime("%Y-%m")
                month_label = dt.strftime("%B %Y")

                if month_key not in monthly_totals:
                    monthly_totals[month_key] = {
                        "month": month_label,
                        "total_messages": 0,
                    }
                monthly_totals[month_key]["total_messages"] += 1

                user_key = f"{month_key}:{user_name}"
                if user_key not in monthly_user_counts:
                    monthly_user_counts[user_key] = {
                        "month": month_label,
                        "user_name": user_name,
                        "messages_sent": 0,
                    }
                monthly_user_counts[user_key]["messages_sent"] += 1

            totals_list = [
                monthly_totals[key] for key in sorted(monthly_totals.keys())
            ]
            user_list = [
                monthly_user_counts[key] for key in sorted(monthly_user_counts.keys())
            ]
            total_messages = sum(item["total_messages"] for item in totals_list)

            return {
                "monthly_totals": totals_list,
                "user_breakdown": user_list,
                "total_messages": total_messages,
            }
        except Exception as e:
            print(f"Error fetching messages summary: {e}")
            return {"monthly_totals": [], "user_breakdown": [], "total_messages": 0}

    def get_log_hours_users(self, start_date: str = None, end_date: str = None) -> List[Dict[str, str]]:
        """
        Get distinct users who asked Nasma to log their hours by mirroring the Supabase SQL.
        Uses server-side filters (content ilike + username exclusions) to ensure parity.
        """
        try:
            patterns = ["%log hours%", "%log_hours%"]
            matching_users = set()

            for pattern in patterns:
                page_size = 1000
                start = 0

                while True:
                    query = (
                        self.client.table(SUPABASE_MESSAGE_TABLE)
                        .select("metadata, content")
                        .eq("role", "user")
                        .ilike("content", pattern)
                    )
                    if start_date:
                        query = query.gte("created_at", start_date)
                    if end_date:
                        if len(end_date) == 10:
                            query = query.lte("created_at", f"{end_date} 23:59:59")
                        else:
                            query = query.lte("created_at", end_date)
                            
                    query = query.range(start, start + page_size - 1)

                    response = query.execute()
                    batch = response.data or []
                    if not batch:
                        break

                    for message in batch:
                        metadata = message.get("metadata") or {}
                        if isinstance(metadata, str):
                            try:
                                metadata = json.loads(metadata)
                            except json.JSONDecodeError:
                                metadata = {}
                        user_name = metadata.get("user_name") or metadata.get("username")
                        if not user_name:
                            continue

                        username_lower = user_name.lower()
                        if any(term in username_lower for term in ["omar", "saba", "sanad"]):
                            continue

                        matching_users.add(user_name)

                    start += page_size

            return [{"user_name": name} for name in sorted(matching_users)]
        except Exception as e:
            print(f"Error fetching log hours users: {e}")
            return []

    def get_request_success_rates(
        self, start_date: str = None, end_date: str = None
    ) -> List[Dict[str, Any]]:
        """
        Calculate success rates for high-impact request types by mirroring the SQL query.
        """
        target_metrics = [
            "log_hours",
            "timeoff_approval",
            "timeoff_refusal",
            "overtime_approval",
            "overtime_refusal",
            "reimbursement",
            "document",
        ]
        excluded_users = {
            "Omar Basem Elhasan",
            "Saba S. F. Abuhouran Dababneh",
            "Sanad Feras Khaleel Zaqtan",
        }

        def resolve_request_type(metric: str) -> str:
            if not metric:
                return ""
            if metric.startswith("timeoff_"):
                return "timeoff"
            if metric.startswith("overtime_"):
                return "overtime"
            if metric == "log_hours":
                return "log_hours"
            if metric == "reimbursement":
                return "reimbursement"
            if metric == "document":
                return "document"
            return ""

        def resolve_success(metric: str) -> int:
            if metric in ("timeoff_approval", "overtime_approval"):
                return 1
            if metric in ("timeoff_refusal", "overtime_refusal"):
                return 0
            if metric in ("log_hours", "reimbursement", "document"):
                return 1
            return -1

        try:
            query = (
                self.client.table(SUPABASE_METRIC_TABLE)
                .select("user_name, metric_type, created_at")
                .in_("metric_type", target_metrics)
            )
            if start_date:
                query = query.gte("created_at", start_date)
            if end_date:
                if len(end_date) == 10:
                    query = query.lte("created_at", f"{end_date} 23:59:59")
                else:
                    query = query.lte("created_at", end_date)

            response = query.execute()

            aggregates: Dict[str, Dict[str, int]] = {}
            for row in response.data or []:
                user = row.get("user_name")
                metric = row.get("metric_type")
                if not metric or not user:
                    continue
                if user in excluded_users:
                    continue

                request_type = resolve_request_type(metric)
                is_success = resolve_success(metric)

                if not request_type or is_success == -1:
                    continue

                bucket = aggregates.setdefault(
                    request_type, {"successes": 0, "total": 0}
                )
                bucket["total"] += 1
                if is_success == 1:
                    bucket["successes"] += 1

            ordered_types = sorted(
                aggregates.keys(),
                key=lambda typ: typ or "",
            )
            results = []
            for req_type in ordered_types:
                bucket = aggregates[req_type]
                total = bucket["total"]
                successes = bucket["successes"]
                rate = round((successes / total) * 100, 1) if total else 0.0
                results.append(
                    {
                        "request_type": req_type,
                        "success_rate_percent": rate,
                        "successes": successes,
                        "total_events": total,
                    }
                )

            return results
        except Exception as e:
            print(f"Error fetching request success rates: {e}")
            return []

    def get_satisfaction_data(self) -> Dict[str, Any]:
        """
        Get satisfaction data (stored in a simple JSON file or could be in database)
        For now, returns default structure
        """
        try:
            import os
            satisfaction_file = "satisfaction_data.json"
            if os.path.exists(satisfaction_file):
                with open(satisfaction_file, "r") as f:
                    return json.load(f)
            else:
                # Default value
                return {"overall_satisfaction": "9.62"}
        except Exception as e:
            print(f"Error fetching satisfaction data: {e}")
            return {"overall_satisfaction": "N/A"}

    def save_satisfaction(self, satisfaction_value: str) -> bool:
        """
        Save satisfaction value
        For now, stores in a simple JSON file
        """
        try:
            import os
            satisfaction_file = "satisfaction_data.json"
            data = {"overall_satisfaction": satisfaction_value}
            with open(satisfaction_file, "w") as f:
                json.dump(data, f)
            return True
        except Exception as e:
            print(f"Error saving satisfaction: {e}")
            return False

    def get_ease_comparison_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get ease comparison data for Nasma vs Odoo
        This would typically come from a survey/feedback table
        For now, returns sample structure that can be edited
        """
        try:
            # This could be stored in a database table
            # For now, return default structure stored in JSON
            import os
            ease_file = "ease_comparison_data.json"
            if os.path.exists(ease_file):
                with open(ease_file, "r") as f:
                    return json.load(f)
            else:
                # Default data structure
                default_data = {
                    "odoo": [{"period": "Week 1", "value": 6.82}],
                    "nasma": [{"period": "Week 1", "value": 9.00}],
                }
                with open(ease_file, "w") as f:
                    json.dump(default_data, f)
                return default_data
        except Exception as e:
            print(f"Error fetching ease comparison data: {e}")
            return {
                "odoo": [{"period": "Week 1", "value": 6.82}],
                "nasma": [{"period": "Week 1", "value": 9.00}],
            }

    def save_ease_comparison_data(
        self, odoo_data: List[Dict], nasma_data: List[Dict]
    ) -> bool:
        """
        Save ease comparison data
        """
        try:
            ease_file = "ease_comparison_data.json"
            data = {"odoo": odoo_data, "nasma": nasma_data}
            with open(ease_file, "w") as f:
                json.dump(data, f)
            return True
        except Exception as e:
            print(f"Error saving ease comparison data: {e}")
            return False

    def get_nasma_activities_today(
        self, start_date: str = None, end_date: str = None
    ) -> List[Dict[str, Any]]:
        """
        Get per-user request counts grouped by metric_type.
        Defaults to today's activity when no dates supplied.
        """
        try:
            query = self.client.table(SUPABASE_METRIC_TABLE).select(
                "user_name, metric_type, created_at"
            )

            if start_date or end_date:
                if start_date:
                    query = query.gte("created_at", start_date)
                if end_date:
                    if len(end_date) == 10:
                        query = query.lte("created_at", f"{end_date} 23:59:59")
                    else:
                        query = query.lte("created_at", end_date)
            else:
                utc_now = datetime.utcnow()
                start_of_day = utc_now.replace(hour=0, minute=0, second=0, microsecond=0)
                end_of_day = start_of_day.replace(hour=23, minute=59, second=59)
                query = query.gte(
                    "created_at", start_of_day.strftime("%Y-%m-%d %H:%M:%S")
                ).lte("created_at", end_of_day.strftime("%Y-%m-%d %H:%M:%S"))

            response = query.execute()

            excluded = {
                "Omar Basem Elhasan",
                "Saba S. F. Abuhouran Dababneh",
                "Sanad Feras Khaleel Zaqtan",
            }

            counts: Dict[tuple, int] = {}
            for row in response.data or []:
                user = row.get("user_name")
                metric_type = row.get("metric_type")
                if not user or not metric_type:
                    continue
                if user in excluded:
                    continue
                key = (user, metric_type)
                counts[key] = counts.get(key, 0) + 1

            result = [
                {
                    "user_name": user,
                    "metric_type": metric,
                    "actions_today": count,
                }
                for (user, metric), count in sorted(
                    counts.items(), key=lambda item: (item[0][0].lower(), -item[1])
                )
            ]
            return result
        except Exception as e:
            print(f"Error fetching today's activities: {e}")
            return []

