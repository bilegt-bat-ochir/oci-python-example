from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from pathlib import Path
from typing import Callable, Iterable, List, Optional

from .dashboard import write_dashboard
from .models import Inventory
from .oci_gateway import OCIAppError, OCIInventoryClient
from .sample_data import empty_inventory, sample_inventory
from .scaling import ScaleDecision, ScaleTags
from .server import serve_inventory_dashboard


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "handler"):
        parser.print_help()
        return 2
    try:
        return args.handler(args)
    except OCIAppError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="exacc-app",
        description="Reusable OCI Exadata Cloud@Customer inventory dashboard and operations CLI",
    )
    subcommands = parser.add_subparsers(dest="command")

    inventory = subcommands.add_parser("inventory", help="Fetch and print inventory")
    add_fetch_args(inventory)
    inventory.add_argument(
        "--format",
        choices=["summary", "json", "csv"],
        default="summary",
        help="Output format",
    )
    inventory.add_argument(
        "--resource",
        choices=["infrastructures", "vm-clusters", "autonomous-vm-clusters", "versions"],
        default="vm-clusters",
        help="CSV resource view",
    )
    inventory.add_argument("-o", "--output", help="Write output to a file")
    inventory.set_defaults(handler=handle_inventory)

    dashboard = subcommands.add_parser("dashboard", help="Render a self-contained HTML app")
    add_fetch_args(dashboard)
    dashboard.add_argument(
        "-o",
        "--output",
        default="exacc-dashboard.html",
        help="HTML file to write",
    )
    dashboard.set_defaults(handler=handle_dashboard)

    serve = subcommands.add_parser("serve", help="Serve the dashboard locally")
    add_fetch_args(serve)
    serve.add_argument("--host", default="127.0.0.1", help="Bind host")
    serve.add_argument("--port", type=int, default=8000, help="Bind port")
    serve.set_defaults(handler=handle_serve)

    scale = subcommands.add_parser(
        "scale-tagged", help="Scale VM clusters from scheduled OCI defined tags"
    )
    add_profile_args(scale)
    scale.add_argument("-a", "--all-regions", action="store_true", help="Scan all subscribed regions")
    scale.add_argument("-c", "--confirm", action="store_true", help="Submit scale operations")
    scale.add_argument("-v", "--verbose", action="store_true", help="Show ignored clusters")
    scale.add_argument("--time-marker", help="Override UTC marker, for example 21:00_UTC")
    scale.add_argument("--tag-namespace", default="osc_exacc", help="Defined tag namespace")
    scale.add_argument("--scale-down-time-key", default="scale_down_time")
    scale.add_argument("--scale-up-time-key", default="scale_up_time")
    scale.add_argument("--scale-down-ocpus-key", default="scale_down_ocpus")
    scale.add_argument("--scale-up-ocpus-key", default="scale_up_ocpus")
    scale.set_defaults(handler=handle_scale_tagged)

    return parser


def add_profile_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-p", "--profile", help="OCI config profile")
    parser.add_argument(
        "--config-file",
        default="~/.oci/config",
        help="OCI config file path",
    )


def add_fetch_args(parser: argparse.ArgumentParser) -> None:
    add_profile_args(parser)
    parser.add_argument("-a", "--all-regions", action="store_true", help="Scan all subscribed regions")
    parser.add_argument("--sample", action="store_true", help="Use built-in demo data")


def handle_inventory(args: argparse.Namespace) -> int:
    inventory = load_inventory(args)
    if args.format == "json":
        body = json.dumps(inventory.to_dict(), ensure_ascii=True, indent=2)
    elif args.format == "csv":
        body = inventory_csv(inventory, args.resource)
    else:
        body = inventory_summary(inventory)

    if args.output:
        Path(args.output).write_text(body + "\n", encoding="utf-8")
    else:
        print(body)
    return 0


def handle_dashboard(args: argparse.Namespace) -> int:
    inventory = load_inventory(args)
    output = write_dashboard(inventory, args.output)
    print(f"Wrote dashboard to {output.resolve()}")
    return 0


def handle_serve(args: argparse.Namespace) -> int:
    if args.sample or args.profile:
        inventory = load_inventory(args)
    else:
        inventory = empty_inventory()
    serve_inventory_dashboard(inventory, host=args.host, port=args.port)
    return 0


def handle_scale_tagged(args: argparse.Namespace) -> int:
    require_profile(args)
    tags = ScaleTags(
        namespace=args.tag_namespace,
        scale_down_time=args.scale_down_time_key,
        scale_up_time=args.scale_up_time_key,
        scale_down_ocpus=args.scale_down_ocpus_key,
        scale_up_ocpus=args.scale_up_ocpus_key,
    )
    client = OCIInventoryClient(
        profile=args.profile,
        config_file=args.config_file,
        all_regions=args.all_regions,
    )
    decisions = client.scale_tagged_vm_clusters(
        tags=tags,
        confirm=args.confirm,
        verbose=args.verbose,
        time_marker=args.time_marker,
    )
    print(scale_decisions_table(decisions))
    return 0


def load_inventory(args: argparse.Namespace) -> Inventory:
    if getattr(args, "sample", False):
        return sample_inventory()
    require_profile(args)
    client = OCIInventoryClient(
        profile=args.profile,
        config_file=args.config_file,
        all_regions=args.all_regions,
    )
    return client.fetch_inventory()


def require_profile(args: argparse.Namespace) -> None:
    if not getattr(args, "profile", None):
        raise OCIAppError("--profile is required unless --sample is used.")


def inventory_summary(inventory: Inventory) -> str:
    summary = inventory.summary()
    lines = [
        f"Tenant: {inventory.tenant_name}",
        f"Generated: {inventory.generated_at}",
        f"Regions: {', '.join(inventory.regions) or '-'}",
        f"Infrastructures: {summary['infrastructure_count']}",
        f"VM clusters: {summary['vm_cluster_count']}",
        f"Autonomous VM clusters: {summary['autonomous_vm_cluster_count']}",
        f"OCPU capacity: {summary['total_ocpus_enabled']} / {summary['total_ocpu_capacity']} ({summary['capacity_used_pct']}%)",
        f"Resources needing attention: {summary['attention_resources']}",
    ]
    return "\n".join(lines)


def inventory_csv(inventory: Inventory, resource: str) -> str:
    output = io.StringIO()
    writer = csv.writer(output)

    if resource == "infrastructures":
        writer.writerow(
            [
                "Region",
                "Compartment",
                "Name",
                "Shape",
                "Compute Nodes",
                "Storage Nodes",
                "OCPUs Enabled",
                "OCPU Capacity",
                "Status",
                "OCID",
            ]
        )
        for item in inventory.infrastructures:
            writer.writerow(
                [
                    item.region,
                    item.compartment_path,
                    item.display_name,
                    item.shape,
                    item.compute_count,
                    item.storage_count,
                    item.cpus_enabled,
                    item.max_cpu_count,
                    item.lifecycle_state,
                    item.id,
                ]
            )
    elif resource == "autonomous-vm-clusters":
        writer.writerow(
            ["Region", "Compartment", "Name", "Status", "OCPUs", "Infrastructure", "OCID"]
        )
        for item in inventory.autonomous_vm_clusters:
            writer.writerow(
                [
                    item.region,
                    item.compartment_path,
                    item.display_name,
                    item.lifecycle_state,
                    item.cpus_enabled,
                    item.exadata_infrastructure_name,
                    item.id,
                ]
            )
    elif resource == "versions":
        writer.writerow(
            [
                "Region",
                "Compartment",
                "Name",
                "Status",
                "GI Version",
                "Exadata Image Version",
            ]
        )
        for item in inventory.vm_clusters:
            writer.writerow(
                [
                    item.region,
                    item.compartment_path,
                    item.display_name,
                    item.lifecycle_state,
                    item.gi_version,
                    item.system_version,
                ]
            )
    else:
        writer.writerow(
            [
                "Region",
                "Compartment",
                "Name",
                "Status",
                "DB Nodes",
                "OCPUs",
                "Memory GB",
                "GI Version",
                "Exadata Image Version",
                "Infrastructure",
                "OCID",
            ]
        )
        for item in inventory.vm_clusters:
            writer.writerow(
                [
                    item.region,
                    item.compartment_path,
                    item.display_name,
                    item.lifecycle_state,
                    item.db_node_count,
                    item.cpus_enabled,
                    item.memory_size_in_gbs,
                    item.gi_version,
                    item.system_version,
                    item.exadata_infrastructure_name,
                    item.id,
                ]
            )

    return output.getvalue().strip()


def scale_decisions_table(decisions: Iterable[ScaleDecision]) -> str:
    rows = list(decisions)
    if not rows:
        return "No VM clusters matched the current scaling marker."

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "Outcome",
            "Direction",
            "Region",
            "Compartment",
            "Name",
            "Current OCPUs",
            "Desired OCPUs",
            "Reason",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row.outcome,
                row.direction,
                row.region,
                row.compartment_path,
                row.display_name,
                row.current_ocpus,
                row.desired_ocpus if row.desired_ocpus is not None else "",
                row.reason,
            ]
        )
    return output.getvalue().strip()
