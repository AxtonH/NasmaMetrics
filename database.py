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
)
from datetime import datetime
from typing import List, Dict, Any
import json


class Database:
    """Database handler for Supabase operations"""

    def __init__(self):
        """Initialize Supabase client"""
        self.client: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE)

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
        Calculate adoption per department following the provided SQL logic.
        Returns list of departments with counts and adoption rate.
        """
        try:
            excluded_names = {
                "Omar Basem Elhasan",
                "Saba S. F. Abuhouran Dababneh",
                "Sanad Feras Khaleel Zaqtan",
            }

            employees_response = (
                self.client.table(SUPABASE_EMPLOYEES_TABLE)
                .select("full_name, department")
                .execute()
            )

            employees_by_name: Dict[str, str] = {}
            department_members: Dict[str, set] = {}

            for row in employees_response.data or []:
                full_name = row.get("full_name")
                department = row.get("department") or "Unknown"

                if not full_name or full_name in excluded_names:
                    continue

                employees_by_name[full_name] = department
                if department not in department_members:
                    department_members[department] = set()
                department_members[department].add(full_name)

            page_size = 1000
            start = 0
            department_active: Dict[str, set] = {}

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

                    department = employees_by_name.get(user_name)
                    if not department:
                        continue

                    if department not in department_active:
                        department_active[department] = set()
                    department_active[department].add(user_name)

                if len(batch) < page_size:
                    break

                start += page_size

            results: List[Dict[str, Any]] = []
            for department, members in department_members.items():
                total = len(members)
                active = len(department_active.get(department, set()))
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
                key=lambda item: (-item["adoption_rate_percent"], item["department"])
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

    def get_inactive_employees(self) -> List[Dict[str, Any]]:
        """
        Return employees from employees_reference who never sent a chat message (role='user').
        Mirrors provided SQL logic by comparing employee list against chat metadata user_name.
        """
        try:
            # Load all employees in batches
            employees = []
            page_size = 1000
            start = 0
            while True:
                response = (
                    self.client.table(SUPABASE_EMPLOYEES_TABLE)
                    .select("user_name, department")
                    .range(start, start + page_size - 1)
                    .execute()
                )
                batch = response.data or []
                if not batch:
                    break
                employees.extend(batch)
                start += page_size

            # Collect distinct user_name values from chat messages (role='user')
            message_users = set()
            start = 0
            while True:
                response = (
                    self.client.table(SUPABASE_MESSAGE_TABLE)
                    .select("metadata, role")
                    .eq("role", "user")
                    .range(start, start + page_size - 1)
                    .execute()
                )
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
                    username = metadata.get("user_name") or metadata.get("username")
                    if username:
                        message_users.add(username)

                start += page_size

            inactive = []
            for employee in employees:
                username = employee.get("user_name") or employee.get("username")
                department = employee.get("department") or "Unknown"
                if not username:
                    continue
                if username in message_users:
                    continue
                inactive.append(
                    {"user_name": username, "department": department}
                )

            inactive.sort(key=lambda entry: (entry["department"], entry["user_name"]))
            return inactive
        except Exception as e:
            print(f"Error fetching inactive employees: {e}")
            return []

    def get_average_request_durations(
        self, start_date: str = None, end_date: str = None
    ) -> List[Dict[str, Any]]:
        """
        Calculate average duration per request type (log_hours, timeoff, overtime).
        Duration equals the span between the first and last session_metric entry in a thread.
        Results exclude requests initiated by specific internal users.
        """
        target_metrics = ["log_hours", "timeoff", "overtime"]
        excluded_users = {
            "Omar Basem Elhasan",
            "Saba S. F. Abuhouran Dababneh",
            "Sanad Feras Khaleel Zaqtan",
        }

        try:
            page_size = 1000
            start = 0
            metrics: List[Dict[str, Any]] = []

            while True:
                query = (
                    self.client.table(SUPABASE_METRIC_TABLE)
                    .select("thread_id, metric_type, created_at")
                    .in_("metric_type", target_metrics)
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

                metrics.extend(batch)
                start += page_size

            thread_ids = sorted(
                {
                    record.get("thread_id")
                    for record in metrics
                    if record.get("thread_id")
                }
            )

            thread_users: Dict[str, str] = {}
            chunk_size = 99
            for idx in range(0, len(thread_ids), chunk_size):
                chunk = thread_ids[idx : idx + chunk_size]
                query = (
                    self.client.table(SUPABASE_MESSAGE_TABLE)
                    .select("thread_id, metadata")
                    .eq("role", "user")
                    .in_("thread_id", chunk)
                )
                message_response = query.execute()
                for message in message_response.data or []:
                    thread_id = message.get("thread_id")
                    if not thread_id or thread_id in thread_users:
                        continue
                    metadata = message.get("metadata") or {}
                    if isinstance(metadata, str):
                        try:
                            metadata = json.loads(metadata)
                        except json.JSONDecodeError:
                            metadata = {}
                    user_name = metadata.get("user_name") or metadata.get("username")
                    if user_name:
                        thread_users[thread_id] = user_name

            per_request: Dict[tuple, List[datetime]] = {}
            for record in metrics:
                metric_type = record.get("metric_type")
                thread_id = record.get("thread_id")
                created_at = record.get("created_at")

                if (
                    not metric_type
                    or metric_type not in target_metrics
                    or not thread_id
                    or not created_at
                ):
                    continue

                user_name = thread_users.get(thread_id)
                if not user_name or user_name in excluded_users:
                    continue

                if isinstance(created_at, str):
                    dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                else:
                    dt = created_at

                key = (metric_type, thread_id)
                per_request.setdefault(key, []).append(dt)

            durations_by_type: Dict[str, List[float]] = {}
            for (metric_type, _thread_id), timestamps in per_request.items():
                if not timestamps:
                    continue
                timestamps.sort()
                duration_seconds = (timestamps[-1] - timestamps[0]).total_seconds()
                durations_by_type.setdefault(metric_type, []).append(duration_seconds)

            results = []
            for metric_type in target_metrics:
                durations = durations_by_type.get(metric_type, [])
                if durations:
                    avg_seconds = round(sum(durations) / len(durations))
                else:
                    avg_seconds = 0
                results.append(
                    {
                        "metric_type": metric_type,
                        "avg_duration_seconds": avg_seconds,
                    }
                )

            return results
        except Exception as e:
            print(f"Error calculating request durations: {e}")
            return [
                {"metric_type": mt, "avg_duration_seconds": 0} for mt in target_metrics
            ]

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
                return {"overall_satisfaction": "9.48"}
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

