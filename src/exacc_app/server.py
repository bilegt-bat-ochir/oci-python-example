from __future__ import annotations

from configparser import ConfigParser
from datetime import datetime, timedelta, timezone
import json
import math
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict
from urllib.parse import parse_qs, urlparse

from .dashboard import render_dashboard
from .models import Inventory
from .oci_gateway import OCIAppError, OCIInventoryClient
from .sample_data import sample_inventory


METRIC_INTERVALS = {
    "1m": timedelta(minutes=1),
    "5m": timedelta(minutes=5),
    "15m": timedelta(minutes=15),
    "30m": timedelta(minutes=30),
    "1h": timedelta(hours=1),
    "1d": timedelta(days=1),
}
COST_GRANULARITIES = {"HOURLY", "DAILY", "MONTHLY"}
COST_QUERY_TYPES = {"COST", "USAGE"}
MAX_HOURLY_COST_RANGE = timedelta(hours=36)
DEMO_COST_SKUS = (
    ("Database Exadata Cloud at Customer - OCPU BYOL", 0.11),
    ("Database Exadata Cloud at Customer - OCPU", 0.42),
)
TREND_METHODS = {
    "least_squares": "Least-squares trend",
    "robust_median": "Robust median slope",
    "rolling_mean": "7-day rolling mean",
    "ewma": "EWMA smoothing",
    "rolling_p90": "14-day rolling P90",
}
DEFAULT_TREND_HISTORY_DAYS = 60
MAX_TREND_HISTORY_DAYS = 180


def list_oci_profiles(config_file: str = "~/.oci/config") -> list[str]:
    config_path = Path(config_file).expanduser()
    if not config_path.exists():
        raise OCIAppError(f"OCI config file was not found at {config_file}.")

    parser = ConfigParser()
    parser.optionxform = str
    parser.read(config_path)

    profiles: list[str] = []
    if parser.defaults():
        profiles.append("DEFAULT")
    profiles.extend(parser.sections())
    return sorted(set(profiles), key=lambda item: (item != "DEFAULT", item.lower()))


def parse_metric_time(value: Any, fallback: datetime) -> datetime:
    if not value:
        return fallback
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise OCIAppError(f"Invalid metric time '{value}'. Use ISO 8601 format.") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def parse_cost_time(value: Any, fallback: datetime, *, end_of_day: bool = False) -> datetime:
    if not value:
        return fallback
    raw_value = str(value).strip()
    try:
        if len(raw_value) == 10:
            parsed = datetime.fromisoformat(raw_value).replace(tzinfo=timezone.utc)
            if end_of_day:
                parsed += timedelta(days=1)
        else:
            parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise OCIAppError(f"Invalid cost date '{value}'. Use YYYY-MM-DD format.") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def default_cost_window() -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    return start, end


def sample_vm_cluster_metrics(
    *,
    vm_cluster_id: str,
    vm_cluster_name: str,
    compartment_id: str,
    region: str,
    start_time: datetime,
    end_time: datetime,
    interval: str,
) -> Dict[str, Any]:
    step = METRIC_INTERVALS.get(interval, METRIC_INTERVALS["1h"])
    points: list[datetime] = []
    cursor = start_time
    while cursor <= end_time and len(points) < 1500:
        points.append(cursor)
        cursor += step

    node_labels = [
        f"{vm_cluster_name or 'vm-cluster'}-dbnode1",
        f"{vm_cluster_name or 'vm-cluster'}-dbnode2",
    ]

    def build_series(
        metric_name: str, baseline: float, amplitude: float
    ) -> Dict[str, Any]:
        series = []
        for node_index, label in enumerate(node_labels):
            datapoints = []
            for point_index, timestamp in enumerate(points):
                wave = math.sin((point_index + 1 + node_index) / 3.0)
                trend = (point_index % 6) * 1.6
                value = max(
                    0.0,
                    min(
                        100.0,
                        baseline + amplitude * wave + trend + node_index * 4,
                    ),
                )
                datapoints.append(
                    {
                        "timestamp": timestamp.isoformat(),
                        "value": round(value, 2),
                    }
                )
            series.append(
                {
                    "label": label,
                    "dimensions": {
                        "resourceId": vm_cluster_id,
                        "resourceName": vm_cluster_name,
                        "hostName": label,
                    },
                    "points": datapoints,
                }
            )
        display_name = (
            "CPU Utilization"
            if metric_name == "CpuUtilization"
            else "Memory Utilization"
        )
        return {
            "name": metric_name,
            "display_name": display_name,
            "unit": "percent",
            "query": (
                f'sample {metric_name}[{interval}]{{resourceId = "{vm_cluster_id}"}}'
                ".groupBy(hostName).mean()"
            ),
            "series": series,
        }

    return {
        "namespace": "oci_database_cluster",
        "resource_id": vm_cluster_id,
        "resource_name": vm_cluster_name,
        "region": region,
        "compartment_id": compartment_id,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "interval": interval,
        "metrics": {
            "CpuUtilization": build_series("CpuUtilization", 34.0, 15.0),
            "MemoryUtilization": build_series("MemoryUtilization", 58.0, 8.0),
        },
    }


def sample_database_metrics(
    *,
    database_id: str,
    database_name: str,
    compartment_id: str,
    region: str,
    start_time: datetime,
    end_time: datetime,
    interval: str,
) -> Dict[str, Any]:
    metrics = sample_vm_cluster_metrics(
        vm_cluster_id=database_id,
        vm_cluster_name=database_name,
        compartment_id=compartment_id,
        region=region,
        start_time=start_time,
        end_time=end_time,
        interval=interval,
    )
    metrics["namespace"] = "oci_database"
    metrics["resource_id"] = database_id
    metrics["resource_name"] = database_name

    for metric_name, metric in metrics["metrics"].items():
        metric["query"] = (
            f'sample {metric_name}[{interval}]'
            f'{{resourceId_database = "{database_id}"}}'
            ".groupBy(instanceName,hostName).mean()"
        )
        for index, series in enumerate(metric.get("series", []), start=1):
            instance_name = f"{database_name or 'database'}{index}"
            host_name = f"{database_name or 'database'}-host{index}"
            series["label"] = f"{instance_name} / {host_name}"
            series["dimensions"] = {
                "resourceId": database_id,
                "resourceName": database_name,
                "resourceId_database": database_id,
                "resourceName_database": database_name,
                "instanceName": instance_name,
                "hostName": host_name,
            }

    return metrics


def parse_bounded_int(
    value: Any, *, default: int, minimum: int, maximum: int, label: str
) -> int:
    if value in (None, ""):
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise OCIAppError(f"{label} must be a number.") from exc
    if parsed < minimum:
        return minimum
    if parsed > maximum:
        return maximum
    return parsed


def point_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def clamp_percent(value: float) -> float:
    return max(0.0, min(100.0, value))


def average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def aggregate_metric_points(metric: Dict[str, Any] | None) -> list[Dict[str, Any]]:
    if not metric:
        return []
    buckets: dict[datetime, list[float]] = {}
    for series in metric.get("series", []) or []:
        for point in series.get("points", []) or []:
            timestamp = point_timestamp(point.get("timestamp"))
            if timestamp is None:
                continue
            try:
                value = float(point.get("value"))
            except (TypeError, ValueError):
                continue
            if not math.isfinite(value):
                continue
            buckets.setdefault(timestamp, []).append(value)
    return [
        {
            "timestamp": timestamp.isoformat(),
            "value": round(average(values), 4),
        }
        for timestamp, values in sorted(buckets.items(), key=lambda item: item[0])
        if values
    ]


def median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[midpoint]
    return (ordered[midpoint - 1] + ordered[midpoint]) / 2


def percentile(values: list[float], percentile_value: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * percentile_value
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[int(rank)]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (rank - lower)


def least_squares_parameters(values: list[float]) -> tuple[float, float]:
    if len(values) < 2:
        return 0.0, values[0] if values else 0.0
    x_mean = (len(values) - 1) / 2
    y_mean = average(values)
    denominator = sum((index - x_mean) ** 2 for index in range(len(values)))
    slope = (
        sum((index - x_mean) * (value - y_mean) for index, value in enumerate(values))
        / denominator
        if denominator
        else 0.0
    )
    intercept = y_mean - slope * x_mean
    return slope, intercept


def least_squares_trend(values: list[float]) -> list[float]:
    if not values:
        return []
    slope, intercept = least_squares_parameters(values)
    return [intercept + slope * index for index in range(len(values))]


def robust_median_trend(values: list[float]) -> list[float]:
    if not values:
        return []
    if len(values) == 1:
        return values[:]
    slopes = [
        (right_value - left_value) / (right_index - left_index)
        for left_index, left_value in enumerate(values)
        for right_index, right_value in enumerate(values[left_index + 1 :], start=left_index + 1)
    ]
    slope = median(slopes)
    intercept = median([value - slope * index for index, value in enumerate(values)])
    return [intercept + slope * index for index in range(len(values))]


def rolling_mean_trend(values: list[float], window: int = 7) -> list[float]:
    if not values:
        return []
    return [
        average(values[max(0, index - window + 1) : index + 1])
        for index in range(len(values))
    ]


def ewma_trend(values: list[float], alpha: float = 0.3) -> list[float]:
    if not values:
        return []
    trend = []
    level = values[0]
    for value in values:
        level = alpha * value + (1 - alpha) * level
        trend.append(level)
    return trend


def rolling_p90_trend(values: list[float], window: int = 14) -> list[float]:
    if not values:
        return []
    return [
        percentile(values[max(0, index - window + 1) : index + 1], 0.9)
        for index in range(len(values))
    ]


def trend_values(
    history_points: list[Dict[str, Any]], method: str
) -> list[Dict[str, Any]]:
    values = [
        float(point["value"])
        for point in history_points
        if isinstance(point.get("value"), (int, float))
    ]
    if not values:
        return []

    if method == "robust_median":
        raw_trend = robust_median_trend(values)
    elif method == "rolling_mean":
        raw_trend = rolling_mean_trend(values)
    elif method == "ewma":
        raw_trend = ewma_trend(values)
    elif method == "rolling_p90":
        raw_trend = rolling_p90_trend(values)
    else:
        raw_trend = least_squares_trend(values)

    return [
        {
            "timestamp": point["timestamp"],
            "value": round(clamp_percent(value), 4),
        }
        for point, value in zip(history_points, raw_trend)
    ]


def history_span_days(history_points: list[Dict[str, Any]]) -> float:
    if len(history_points) < 2:
        return 0.0
    first_timestamp = point_timestamp(history_points[0].get("timestamp"))
    last_timestamp = point_timestamp(history_points[-1].get("timestamp"))
    if first_timestamp is None or last_timestamp is None:
        return 0.0
    return max(0.0, (last_timestamp - first_timestamp).total_seconds() / 86400)


def build_cpu_trend(
    metrics: Dict[str, Any],
    *,
    resource_type: str,
    method: str,
    history_days: int,
) -> Dict[str, Any]:
    cpu_metric = (metrics.get("metrics") or {}).get("CpuUtilization")
    history_points = aggregate_metric_points(cpu_metric)
    span_days = history_span_days(history_points)
    if len(history_points) < DEFAULT_TREND_HISTORY_DAYS and span_days < (
        DEFAULT_TREND_HISTORY_DAYS - 1
    ):
        raise OCIAppError(
            "CPU trend requires at least 60 days of daily metric history; "
            f"received {len(history_points)} daily point(s)."
        )
    trend_points = trend_values(history_points, method)
    trend_delta = (
        trend_points[-1]["value"] - trend_points[0]["value"]
        if len(trend_points) >= 2
        else 0.0
    )
    trend_slope = trend_delta / span_days if span_days else 0.0
    if trend_delta > 0.5:
        trend_direction = "up"
    elif trend_delta < -0.5:
        trend_direction = "down"
    else:
        trend_direction = "flat"
    return {
        "namespace": metrics.get("namespace"),
        "resource_type": resource_type,
        "resource_id": metrics.get("resource_id"),
        "resource_name": metrics.get("resource_name"),
        "region": metrics.get("region"),
        "compartment_id": metrics.get("compartment_id"),
        "metric_name": "CpuUtilization",
        "display_name": "CPU Utilization",
        "unit": "percent",
        "method": method,
        "method_label": TREND_METHODS.get(method, TREND_METHODS["least_squares"]),
        "available_methods": [
            {"value": value, "label": label}
            for value, label in TREND_METHODS.items()
        ],
        "history_days": history_days,
        "history_point_count": len(history_points),
        "history_span_days": round(span_days, 2),
        "trend_delta_percent": round(trend_delta, 4),
        "trend_slope_per_day": round(trend_slope, 4),
        "trend_direction": trend_direction,
        "interval": "1d",
        "history_start_time": metrics.get("start_time"),
        "history_end_time": metrics.get("end_time"),
        "query": cpu_metric.get("query") if cpu_metric else "",
        "queries": cpu_metric.get("queries") if cpu_metric else [],
        "history_points": history_points,
        "trend_points": trend_points,
    }


def demo_cost_sources() -> list[Dict[str, Any]]:
    inventory = sample_inventory()
    sources: list[Dict[str, Any]] = []
    for index, cluster in enumerate(inventory.vm_clusters):
        sku_name, hourly_rate = DEMO_COST_SKUS[index % len(DEMO_COST_SKUS)]
        sources.append(
            {
                "sku_name": sku_name,
                "hourly_rate": hourly_rate,
                "cluster": cluster,
            }
        )
    return sources


def sample_cost_analysis(
    *,
    start_time: datetime,
    end_time: datetime,
    granularity: str,
    query_type: str,
) -> Dict[str, Any]:
    sources = demo_cost_sources()
    sku_names = [
        sku_name
        for sku_name, _rate in DEMO_COST_SKUS
        if any(source["sku_name"] == sku_name for source in sources)
    ]

    periods = []
    details = []
    cursor = start_time
    while cursor < end_time and len(periods) < 750:
        if granularity == "HOURLY":
            next_cursor = min(cursor + timedelta(hours=1), end_time)
        elif granularity == "MONTHLY":
            year = cursor.year + (1 if cursor.month == 12 else 0)
            month = 1 if cursor.month == 12 else cursor.month + 1
            next_cursor = min(cursor.replace(year=year, month=month, day=1), end_time)
        else:
            next_cursor = min(cursor + timedelta(days=1), end_time)
        period_hours = max(0.0, (next_cursor - cursor).total_seconds() / 3600)
        rows = {sku_name: 0.0 for sku_name in sku_names}
        total = 0.0
        for source in sources:
            cluster = source["cluster"]
            sku_name = source["sku_name"]
            usage_value = cluster.cpus_enabled * period_hours
            cost_value = usage_value * source["hourly_rate"]
            value = (
                usage_value
                if query_type == "USAGE"
                else cost_value
            )
            rows[sku_name] = round(rows.get(sku_name, 0.0) + value, 6)
            total += value
            details.append(
                {
                    "period_start": cursor.isoformat(),
                    "period_end": next_cursor.isoformat(),
                    "sku_name": sku_name,
                    "sku_part_number": "DEMO-SKU",
                    "service": "Database",
                    "resource_name": cluster.display_name,
                    "resource_id": cluster.id,
                    "region": cluster.region,
                    "compartment_name": cluster.compartment_path,
                    "computed_amount": round(cost_value, 6),
                    "computed_quantity": round(usage_value, 6),
                    "value": round(value, 6),
                    "unit": "OCPU Hours",
                    "currency": "USD",
                }
            )
        periods.append(
            {
                "period": cursor.isoformat(),
                "series": rows,
                "total": round(total, 6),
            }
        )
        cursor = next_cursor

    series = [
        {
            "label": sku_name,
            "total": round(sum(period["series"][sku_name] for period in periods), 6),
            "points": [
                {"period": period["period"], "value": period["series"][sku_name]}
                for period in periods
            ],
        }
        for sku_name in sku_names
    ]
    return {
        "tenant_name": "demo-tenant",
        "tenancy_id": "ocid1.tenancy.demo",
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "granularity": granularity,
        "query_type": query_type,
        "currency": "USD",
        "unit": "OCPU Hours",
        "total": round(sum(period["total"] for period in periods), 6),
        "series_names": sku_names,
        "periods": periods,
        "series": series,
        "details": sorted(
            details,
            key=lambda row: (
                row.get("period_start", ""),
                row.get("resource_name", ""),
            ),
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "filter": "Database Exadata Cloud@Customer OCPU and OCPU BYOL",
    }


def sample_budgets() -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    cycle_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    next_month = cycle_start.replace(
        year=cycle_start.year + (1 if cycle_start.month == 12 else 0),
        month=1 if cycle_start.month == 12 else cycle_start.month + 1,
    )
    hourly_cost = sum(
        source["cluster"].cpus_enabled * source["hourly_rate"]
        for source in demo_cost_sources()
    )
    elapsed_hours = max(0.0, (now - cycle_start).total_seconds() / 3600)
    cycle_hours = max(1.0, (next_month - cycle_start).total_seconds() / 3600)
    actual_spend = round(hourly_cost * elapsed_hours, 2)
    forecasted_spend = round(hourly_cost * cycle_hours, 2)
    amount = round(forecasted_spend * 1.15, 2)
    percent_used = round((actual_spend / amount) * 100, 2) if amount else 0.0
    return {
        "tenant_name": "demo-tenant",
        "tenancy_id": "ocid1.tenancy.demo",
        "generated_at": now.isoformat(),
        "budgets": [
            {
                "id": "ocid1.budget.demo.exacc",
                "display_name": "ExaCC monthly guardrail",
                "description": "Demo budget from sample VM cluster enabled OCPUs.",
                "amount": amount,
                "actual_spend": actual_spend,
                "forecasted_spend": forecasted_spend,
                "percent_used": percent_used,
                "reset_period": "MONTHLY",
                "target_type": "COMPARTMENT",
                "targets": ["ocid1.compartment.demo.exacc"],
                "lifecycle_state": "ACTIVE",
                "alert_rule_count": 2,
                "time_spend_computed": now.isoformat(),
                "time_created": "2026-01-01T00:00:00+00:00",
            }
        ],
    }


def serve_inventory_dashboard(
    inventory: Inventory, *, host: str = "127.0.0.1", port: int = 8000
) -> None:
    html = render_dashboard(inventory).encode("utf-8")
    payload = json.dumps(inventory.to_dict(), ensure_ascii=True, indent=2).encode("utf-8")

    class DashboardHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path in {"/", "/index.html"}:
                self._send(200, "text/html; charset=utf-8", html)
                return
            if parsed.path == "/inventory.json":
                self._send(200, "application/json; charset=utf-8", payload)
                return
            if parsed.path == "/api/profiles":
                self._handle_profiles(parsed.query)
                return
            self._send(404, "text/plain; charset=utf-8", b"Not found")

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/api/inventory":
                self._handle_inventory_load()
                return
            if parsed.path == "/api/vm-cluster-metrics":
                self._handle_vm_cluster_metrics()
                return
            if parsed.path == "/api/database-metrics":
                self._handle_database_metrics()
                return
            if parsed.path == "/api/cpu-trend":
                self._handle_cpu_trend()
                return
            if parsed.path == "/api/cost-analysis":
                self._handle_cost_analysis()
                return
            if parsed.path == "/api/budgets":
                self._handle_budgets()
                return
            self._send_json(404, {"error": "Not found"})

        def log_message(self, format: str, *args: object) -> None:
            return

        def _handle_profiles(self, query: str) -> None:
            params = parse_qs(query)
            config_file = params.get("config_file", ["~/.oci/config"])[0]
            try:
                profiles = list_oci_profiles(config_file)
            except OCIAppError as exc:
                self._send_json(400, {"error": str(exc), "profiles": []})
                return
            self._send_json(200, {"profiles": profiles})

        def _handle_inventory_load(self) -> None:
            try:
                data = self._read_json()
                if data.get("sample"):
                    loaded = sample_inventory()
                else:
                    profile = str(data.get("profile", "")).strip()
                    if not profile:
                        raise OCIAppError("OCI profile is required.")
                    client = OCIInventoryClient(
                        profile=profile,
                        config_file=str(data.get("config_file") or "~/.oci/config"),
                        all_regions=bool(data.get("all_regions")),
                    )
                    loaded = client.fetch_inventory()
            except OCIAppError as exc:
                self._send_json(400, {"error": str(exc)})
                return
            except Exception as exc:
                self._send_json(500, {"error": f"Could not load inventory: {exc}"})
                return
            self._send_json(200, loaded.to_dict())

        def _handle_vm_cluster_metrics(self) -> None:
            try:
                data = self._read_json()
                vm_cluster_id = str(data.get("vm_cluster_id") or "").strip()
                vm_cluster_name = str(data.get("vm_cluster_name") or "").strip()
                compartment_id = str(data.get("compartment_id") or "").strip()
                region = str(data.get("region") or "").strip()
                if not vm_cluster_id:
                    raise OCIAppError("VM cluster OCID is required.")
                if not compartment_id:
                    raise OCIAppError("VM cluster compartment OCID is required.")
                if not region:
                    raise OCIAppError("VM cluster region is required.")

                interval = str(data.get("interval") or "1h").strip()
                if interval not in METRIC_INTERVALS:
                    raise OCIAppError(
                        "Metric interval must be one of "
                        f"{', '.join(METRIC_INTERVALS)}."
                    )

                now = datetime.now(timezone.utc)
                end_time = parse_metric_time(data.get("end_time"), now)
                start_time = parse_metric_time(
                    data.get("start_time"), end_time - timedelta(days=1)
                )
                if start_time >= end_time:
                    raise OCIAppError("Metric start time must be before end time.")

                if data.get("sample"):
                    metrics = sample_vm_cluster_metrics(
                        vm_cluster_id=vm_cluster_id,
                        vm_cluster_name=vm_cluster_name,
                        compartment_id=compartment_id,
                        region=region,
                        start_time=start_time,
                        end_time=end_time,
                        interval=interval,
                    )
                else:
                    profile = str(data.get("profile", "")).strip()
                    if not profile:
                        raise OCIAppError("OCI profile is required.")
                    client = OCIInventoryClient(
                        profile=profile,
                        config_file=str(data.get("config_file") or "~/.oci/config"),
                    )
                    metrics = client.fetch_vm_cluster_metrics(
                        vm_cluster_id=vm_cluster_id,
                        vm_cluster_name=vm_cluster_name,
                        compartment_id=compartment_id,
                        region=region,
                        start_time=start_time,
                        end_time=end_time,
                        interval=interval,
                    )
            except OCIAppError as exc:
                self._send_json(400, {"error": str(exc)})
                return
            except Exception as exc:
                self._send_json(
                    500, {"error": f"Could not load VM cluster metrics: {exc}"}
                )
                return
            self._send_json(200, metrics)

        def _handle_database_metrics(self) -> None:
            try:
                data = self._read_json()
                database_id = str(data.get("database_id") or "").strip()
                database_name = str(data.get("database_name") or "").strip()
                compartment_id = str(data.get("compartment_id") or "").strip()
                region = str(data.get("region") or "").strip()
                if not database_id:
                    raise OCIAppError("Database OCID is required.")
                if not compartment_id:
                    raise OCIAppError("Database compartment OCID is required.")
                if not region:
                    raise OCIAppError("Database region is required.")

                interval = str(data.get("interval") or "1h").strip()
                if interval not in METRIC_INTERVALS:
                    raise OCIAppError(
                        "Metric interval must be one of "
                        f"{', '.join(METRIC_INTERVALS)}."
                    )

                now = datetime.now(timezone.utc)
                end_time = parse_metric_time(data.get("end_time"), now)
                start_time = parse_metric_time(
                    data.get("start_time"), end_time - timedelta(days=1)
                )
                if start_time >= end_time:
                    raise OCIAppError("Metric start time must be before end time.")

                if data.get("sample"):
                    metrics = sample_database_metrics(
                        database_id=database_id,
                        database_name=database_name,
                        compartment_id=compartment_id,
                        region=region,
                        start_time=start_time,
                        end_time=end_time,
                        interval=interval,
                    )
                else:
                    profile = str(data.get("profile", "")).strip()
                    if not profile:
                        raise OCIAppError("OCI profile is required.")
                    client = OCIInventoryClient(
                        profile=profile,
                        config_file=str(data.get("config_file") or "~/.oci/config"),
                    )
                    metrics = client.fetch_database_metrics(
                        database_id=database_id,
                        database_name=database_name,
                        compartment_id=compartment_id,
                        region=region,
                        start_time=start_time,
                        end_time=end_time,
                        interval=interval,
                    )
            except OCIAppError as exc:
                self._send_json(400, {"error": str(exc)})
                return
            except Exception as exc:
                self._send_json(
                    500, {"error": f"Could not load database metrics: {exc}"}
                )
                return
            self._send_json(200, metrics)

        def _handle_cpu_trend(self) -> None:
            try:
                data = self._read_json()
                resource_type = str(data.get("resource_type") or "").strip()
                if resource_type not in {"vm_cluster", "database"}:
                    raise OCIAppError(
                        "Trend resource type must be vm_cluster or database."
                    )
                compartment_id = str(data.get("compartment_id") or "").strip()
                region = str(data.get("region") or "").strip()
                if not compartment_id:
                    raise OCIAppError("Resource compartment OCID is required.")
                if not region:
                    raise OCIAppError("Resource region is required.")

                method = str(data.get("method") or "least_squares").strip()
                if method not in TREND_METHODS:
                    raise OCIAppError(
                        "Trend method must be one of "
                        f"{', '.join(TREND_METHODS)}."
                    )
                history_days = parse_bounded_int(
                    data.get("history_days"),
                    default=DEFAULT_TREND_HISTORY_DAYS,
                    minimum=DEFAULT_TREND_HISTORY_DAYS,
                    maximum=MAX_TREND_HISTORY_DAYS,
                    label="Trend history days",
                )

                now = datetime.now(timezone.utc)
                end_time = parse_metric_time(data.get("end_time"), now)
                start_time = end_time - timedelta(days=history_days)

                if resource_type == "database":
                    database_id = str(data.get("database_id") or "").strip()
                    database_name = str(data.get("database_name") or "").strip()
                    if not database_id:
                        raise OCIAppError("Database OCID is required.")
                    if data.get("sample"):
                        metrics = sample_database_metrics(
                            database_id=database_id,
                            database_name=database_name,
                            compartment_id=compartment_id,
                            region=region,
                            start_time=start_time,
                            end_time=end_time,
                            interval="1d",
                        )
                    else:
                        profile = str(data.get("profile", "")).strip()
                        if not profile:
                            raise OCIAppError("OCI profile is required.")
                        client = OCIInventoryClient(
                            profile=profile,
                            config_file=str(data.get("config_file") or "~/.oci/config"),
                        )
                        metrics = client.fetch_database_metrics(
                            database_id=database_id,
                            database_name=database_name,
                            compartment_id=compartment_id,
                            region=region,
                            start_time=start_time,
                            end_time=end_time,
                            interval="1d",
                        )
                else:
                    vm_cluster_id = str(data.get("vm_cluster_id") or "").strip()
                    vm_cluster_name = str(data.get("vm_cluster_name") or "").strip()
                    if not vm_cluster_id:
                        raise OCIAppError("VM cluster OCID is required.")
                    if data.get("sample"):
                        metrics = sample_vm_cluster_metrics(
                            vm_cluster_id=vm_cluster_id,
                            vm_cluster_name=vm_cluster_name,
                            compartment_id=compartment_id,
                            region=region,
                            start_time=start_time,
                            end_time=end_time,
                            interval="1d",
                        )
                    else:
                        profile = str(data.get("profile", "")).strip()
                        if not profile:
                            raise OCIAppError("OCI profile is required.")
                        client = OCIInventoryClient(
                            profile=profile,
                            config_file=str(data.get("config_file") or "~/.oci/config"),
                        )
                        metrics = client.fetch_vm_cluster_metrics(
                            vm_cluster_id=vm_cluster_id,
                            vm_cluster_name=vm_cluster_name,
                            compartment_id=compartment_id,
                            region=region,
                            start_time=start_time,
                            end_time=end_time,
                            interval="1d",
                        )
                trend = build_cpu_trend(
                    metrics,
                    resource_type=resource_type,
                    method=method,
                    history_days=history_days,
                )
            except OCIAppError as exc:
                self._send_json(400, {"error": str(exc)})
                return
            except Exception as exc:
                self._send_json(500, {"error": f"Could not calculate CPU trend: {exc}"})
                return
            self._send_json(200, trend)

        def _handle_cost_analysis(self) -> None:
            try:
                data = self._read_json()
                default_start, default_end = default_cost_window()
                start_time = parse_cost_time(data.get("start_date"), default_start)
                end_time = parse_cost_time(
                    data.get("end_date"), default_end, end_of_day=True
                )
                if start_time >= end_time:
                    raise OCIAppError("Cost start date must be before end date.")

                granularity = str(data.get("granularity") or "DAILY").upper()
                if granularity not in COST_GRANULARITIES:
                    raise OCIAppError("Granularity must be HOURLY, DAILY, or MONTHLY.")
                if granularity == "HOURLY" and end_time - start_time > MAX_HOURLY_COST_RANGE:
                    raise OCIAppError(
                        "Hourly cost analysis supports up to 36 hours. "
                        "Choose a single-day range or use daily/monthly granularity."
                    )
                query_type = str(data.get("query_type") or "COST").upper()
                if query_type not in COST_QUERY_TYPES:
                    raise OCIAppError("Cost view must be COST or USAGE.")

                if data.get("sample"):
                    analysis = sample_cost_analysis(
                        start_time=start_time,
                        end_time=end_time,
                        granularity=granularity,
                        query_type=query_type,
                    )
                else:
                    profile = str(data.get("profile", "")).strip()
                    if not profile:
                        raise OCIAppError("OCI profile is required.")
                    client = OCIInventoryClient(
                        profile=profile,
                        config_file=str(data.get("config_file") or "~/.oci/config"),
                    )
                    analysis = client.fetch_cost_analysis(
                        start_time=start_time,
                        end_time=end_time,
                        granularity=granularity,
                        query_type=query_type,
                    )
            except OCIAppError as exc:
                self._send_json(400, {"error": str(exc)})
                return
            except Exception as exc:
                self._send_json(500, {"error": f"Could not load cost analysis: {exc}"})
                return
            self._send_json(200, analysis)

        def _handle_budgets(self) -> None:
            try:
                data = self._read_json()
                if data.get("sample"):
                    budgets = sample_budgets()
                else:
                    profile = str(data.get("profile", "")).strip()
                    if not profile:
                        raise OCIAppError("OCI profile is required.")
                    client = OCIInventoryClient(
                        profile=profile,
                        config_file=str(data.get("config_file") or "~/.oci/config"),
                    )
                    budgets = client.fetch_budgets()
            except OCIAppError as exc:
                self._send_json(400, {"error": str(exc)})
                return
            except Exception as exc:
                self._send_json(500, {"error": f"Could not load budgets: {exc}"})
                return
            self._send_json(200, budgets)

        def _read_json(self) -> Dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0") or "0")
            if length <= 0:
                return {}
            body = self.rfile.read(length)
            return json.loads(body.decode("utf-8"))

        def _send_json(self, status: int, data: Dict[str, Any]) -> None:
            body = json.dumps(data, ensure_ascii=True).encode("utf-8")
            self._send(status, "application/json; charset=utf-8", body)

        def _send(self, status: int, content_type: str, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer((host, port), DashboardHandler)
    print(f"Serving ExaCC dashboard at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped dashboard server")
    finally:
        server.server_close()
