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
