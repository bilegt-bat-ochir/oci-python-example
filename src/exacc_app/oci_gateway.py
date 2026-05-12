from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import quote

from .models import (
    AutonomousVmCluster,
    Compartment,
    Database,
    DbHome,
    ExadataInfrastructure,
    Inventory,
    PluggableDatabase,
    VmCluster,
    safe_int,
)
from .scaling import ScaleDecision, ScaleTags, current_utc_hour_marker, decide_scale_action


class OCIAppError(RuntimeError):
    """Raised when OCI configuration or SDK access prevents the app from running."""


EXACC_COST_SKU_TERMS = ("database", "exadata", "cloud", "customer", "ocpu")


class CompartmentResolver:
    def __init__(self, root_compartment_id: str, compartments: Iterable[Any]) -> None:
        self.root_compartment_id = root_compartment_id
        self.compartments_by_id = {item.id: item for item in compartments}
        self.cache = {root_compartment_id: "root"}

    def path_for(self, compartment_id: str) -> str:
        if not compartment_id:
            return "unknown"
        if compartment_id in self.cache:
            return self.cache[compartment_id]

        compartment = self.compartments_by_id.get(compartment_id)
        if compartment is None:
            return compartment_id

        parent_path = self.path_for(getattr(compartment, "compartment_id", ""))
        name = getattr(compartment, "name", compartment_id)
        if parent_path == "root":
            path = name
        else:
            path = f"{parent_path}:{name}"
        self.cache[compartment_id] = path
        return path


class OCIInventoryClient:
    def __init__(
        self,
        *,
        profile: str,
        config_file: str = "~/.oci/config",
        all_regions: bool = False,
    ) -> None:
        self.profile = profile
        self.config_file = config_file
        self.all_regions = all_regions
        try:
            import oci  # type: ignore
        except ImportError as exc:
            raise OCIAppError(
                "The OCI Python SDK is not installed. Install dependencies with "
                "`python3 -m pip install -r requirements.txt`."
            ) from exc
        self.oci = oci
        self.retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY

    def fetch_inventory(self) -> Inventory:
        context = self._load_context()
        compartments = self._to_compartments(context)
        infrastructures = self._fetch_infrastructures(context)
        infrastructure_by_id = {item.id: item for item in infrastructures}
        vm_clusters = self._fetch_vm_clusters(context, infrastructure_by_id)
        autonomous_vm_clusters = self._fetch_autonomous_vm_clusters(
            context, infrastructure_by_id
        )
        vm_cluster_by_id = {item.id: item for item in vm_clusters}
        db_homes = self._fetch_db_homes(context, vm_cluster_by_id)
        db_home_by_id = {item.id: item for item in db_homes}
        databases = self._fetch_databases(context, db_home_by_id)
        database_by_id = {item.id: item for item in databases}
        pluggable_databases = self._fetch_pluggable_databases(context, database_by_id)

        return Inventory(
            tenant_name=context["tenant_name"],
            home_region=context["home_region"],
            generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            regions=context["scan_regions"],
            compartments=compartments,
            infrastructures=infrastructures,
            vm_clusters=vm_clusters,
            autonomous_vm_clusters=autonomous_vm_clusters,
            db_homes=db_homes,
            databases=databases,
            pluggable_databases=pluggable_databases,
        )

    def scale_tagged_vm_clusters(
        self,
        *,
        tags: ScaleTags,
        confirm: bool,
        verbose: bool = False,
        time_marker: Optional[str] = None,
    ) -> List[ScaleDecision]:
        context = self._load_context()
        marker = time_marker or current_utc_hour_marker()
        decisions: List[ScaleDecision] = []
        seen: set[str] = set()

        for region in context["scan_regions"]:
            config = self._region_config(context["config"], region)
            database_client = self.oci.database.DatabaseClient(config)
            for item in self._list_database_resources(
                context, database_client, "list_vm_clusters"
            ):
                item_id = getattr(item, "id", "")
                if not item_id or item_id in seen:
                    continue
                seen.add(item_id)
                try:
                    vmcluster = database_client.get_vm_cluster(
                        vm_cluster_id=item_id,
                        retry_strategy=self.retry_strategy,
                    ).data
                except Exception:
                    vmcluster = item
                compartment_path = context["compartments"].path_for(
                    getattr(vmcluster, "compartment_id", "")
                )
                decision = decide_scale_action(
                    cluster_id=vmcluster.id,
                    display_name=getattr(vmcluster, "display_name", vmcluster.id),
                    region=region,
                    compartment_path=compartment_path,
                    lifecycle_state=getattr(vmcluster, "lifecycle_state", ""),
                    cpus_enabled=safe_int(getattr(vmcluster, "cpus_enabled", 0)),
                    defined_tags=getattr(vmcluster, "defined_tags", {}) or {},
                    time_marker=marker,
                    tags=tags,
                    confirm=confirm,
                    verbose=verbose,
                )
                if decision is None:
                    continue
                if decision.should_submit and decision.desired_ocpus is not None:
                    details = self.oci.database.models.UpdateVmClusterDetails(
                        cpu_core_count=decision.desired_ocpus
                    )
                    database_client.update_vm_cluster(
                        vmcluster.id,
                        details,
                        retry_strategy=self.retry_strategy,
                    )
                decisions.append(decision)

        return decisions

    def fetch_vm_cluster_metrics(
        self,
        *,
        vm_cluster_id: str,
        vm_cluster_name: str,
        compartment_id: str,
        region: str,
        start_time: datetime,
        end_time: datetime,
        interval: str = "1h",
    ) -> Dict[str, Any]:
        config = self.oci.config.from_file(self.config_file, self.profile)
        config = self._region_config(config, region)
        monitoring_client = self.oci.monitoring.MonitoringClient(config)
        namespace = "oci_database_cluster"
        metrics = [
            ("CpuUtilization", "CPU Utilization", "percent"),
            ("MemoryUtilization", "Memory Utilization", "percent"),
        ]
        return {
            "namespace": namespace,
            "resource_id": vm_cluster_id,
            "resource_name": vm_cluster_name,
            "region": region,
            "compartment_id": compartment_id,
            "start_time": self._stringify_time(start_time),
            "end_time": self._stringify_time(end_time),
            "interval": interval,
            "metrics": {
                metric_name: self._fetch_metric_series(
                    monitoring_client=monitoring_client,
                    compartment_id=compartment_id,
                    namespace=namespace,
                    metric_name=metric_name,
                    display_name=display_name,
                    unit=unit,
                    resource_id=vm_cluster_id,
                    filter_dimension_names=("resourceId",),
                    group_by="hostName",
                    start_time=start_time,
                    end_time=end_time,
                    interval=interval,
                )
                for metric_name, display_name, unit in metrics
            },
        }

    def fetch_database_metrics(
        self,
        *,
        database_id: str,
        database_name: str,
        compartment_id: str,
        region: str,
        start_time: datetime,
        end_time: datetime,
        interval: str = "1h",
    ) -> Dict[str, Any]:
        config = self.oci.config.from_file(self.config_file, self.profile)
        config = self._region_config(config, region)
        monitoring_client = self.oci.monitoring.MonitoringClient(config)
        namespace = "oci_database"
        metrics = [
            ("CpuUtilization", "CPU Utilization", "percent"),
            ("MemoryUtilization", "Memory Utilization", "percent"),
        ]
        return {
            "namespace": namespace,
            "resource_id": database_id,
            "resource_name": database_name,
            "region": region,
            "compartment_id": compartment_id,
            "start_time": self._stringify_time(start_time),
            "end_time": self._stringify_time(end_time),
            "interval": interval,
            "metrics": {
                metric_name: self._fetch_metric_series(
                    monitoring_client=monitoring_client,
                    compartment_id=compartment_id,
                    namespace=namespace,
                    metric_name=metric_name,
                    display_name=display_name,
                    unit=unit,
                    resource_id=database_id,
                    filter_dimension_names=("resourceId_database", "resourceId"),
                    group_by="instanceName,hostName",
                    start_time=start_time,
                    end_time=end_time,
                    interval=interval,
                )
                for metric_name, display_name, unit in metrics
            },
        }

    def fetch_cost_analysis(
        self,
        *,
        start_time: datetime,
        end_time: datetime,
        granularity: str,
        query_type: str,
    ) -> Dict[str, Any]:
        context = self._load_account_context()
        config = self._region_config(
            context["config"], context["home_region"] or context["config"].get("region", "")
        )
        usage_client = self.oci.usage_api.UsageapiClient(config)
        details = self.oci.usage_api.models.RequestSummarizedUsagesDetails(
            tenant_id=context["tenancy_id"],
            time_usage_started=start_time,
            time_usage_ended=end_time,
            granularity=granularity,
            query_type=query_type,
            is_aggregate_by_time=False,
            group_by=["skuName"],
        )
        response = usage_client.request_summarized_usages(
            request_summarized_usages_details=details,
            retry_strategy=self.retry_strategy,
        )
        items = getattr(response.data, "items", []) or []
        rows = [self._to_cost_row(item, query_type) for item in items]
        rows = [row for row in rows if self._is_exacc_ocpu_sku(row.get("sku_name", ""))]
        return self._to_cost_analysis_payload(
            context=context,
            start_time=start_time,
            end_time=end_time,
            granularity=granularity,
            query_type=query_type,
            rows=rows,
        )

    def fetch_budgets(self) -> Dict[str, Any]:
        context = self._load_account_context()
        config = self._region_config(
            context["config"], context["home_region"] or context["config"].get("region", "")
        )
        budget_client = self.oci.budget.BudgetClient(config)
        response = self.oci.pagination.list_call_get_all_results(
            budget_client.list_budgets,
            compartment_id=context["tenancy_id"],
            target_type="ALL",
            retry_strategy=self.retry_strategy,
        )
        budgets = [self._to_budget_row(item) for item in response.data]
        return {
            "tenant_name": context["tenant_name"],
            "tenancy_id": context["tenancy_id"],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "budgets": budgets,
        }

    def _load_context(self) -> Dict[str, Any]:
        try:
            config = self.oci.config.from_file(self.config_file, self.profile)
        except Exception as exc:
            raise OCIAppError(
                f"OCI profile '{self.profile}' was not found in {self.config_file}."
            ) from exc

        identity_client = self.oci.identity.IdentityClient(config)
        user = identity_client.get_user(
            config["user"], retry_strategy=self.retry_strategy
        ).data
        root_compartment_id = user.compartment_id

        regions = self.oci.pagination.list_call_get_all_results(
            identity_client.list_region_subscriptions,
            tenancy_id=root_compartment_id,
            retry_strategy=self.retry_strategy,
        ).data

        home_region = next(
            (
                region.region_name
                for region in regions
                if getattr(region, "is_home_region", False)
            ),
            config.get("region", ""),
        )
        scan_regions = (
            [region.region_name for region in regions]
            if self.all_regions
            else [config.get("region", "")]
        )

        tenancy = identity_client.get_tenancy(
            root_compartment_id, retry_strategy=self.retry_strategy
        ).data

        compartments = self.oci.pagination.list_call_get_all_results(
            identity_client.list_compartments,
            compartment_id=root_compartment_id,
            compartment_id_in_subtree=True,
            access_level="ANY",
            retry_strategy=self.retry_strategy,
        ).data
        resolver = CompartmentResolver(root_compartment_id, compartments)
        compartment_ids = [root_compartment_id]
        compartment_ids.extend(
            compartment.id for compartment in compartments if getattr(compartment, "id", "")
        )

        return {
            "config": config,
            "root_compartment_id": root_compartment_id,
            "home_region": home_region,
            "tenant_name": tenancy.name,
            "scan_regions": [region for region in scan_regions if region],
            "compartments": resolver,
            "raw_compartments": compartments,
            "compartment_ids": compartment_ids,
        }

    def _load_account_context(self) -> Dict[str, Any]:
        try:
            config = self.oci.config.from_file(self.config_file, self.profile)
        except Exception as exc:
            raise OCIAppError(
                f"OCI profile '{self.profile}' was not found in {self.config_file}."
            ) from exc

        identity_client = self.oci.identity.IdentityClient(config)
        user = identity_client.get_user(
            config["user"], retry_strategy=self.retry_strategy
        ).data
        tenancy_id = user.compartment_id
        tenancy = identity_client.get_tenancy(
            tenancy_id, retry_strategy=self.retry_strategy
        ).data
        regions = self.oci.pagination.list_call_get_all_results(
            identity_client.list_region_subscriptions,
            tenancy_id=tenancy_id,
            retry_strategy=self.retry_strategy,
        ).data
        home_region = next(
            (
                region.region_name
                for region in regions
                if getattr(region, "is_home_region", False)
            ),
            config.get("region", ""),
        )
        return {
            "config": config,
            "tenancy_id": tenancy_id,
            "tenant_name": getattr(tenancy, "name", "") or tenancy_id,
            "home_region": home_region,
        }

    def _to_compartments(self, context: Dict[str, Any]) -> List[Compartment]:
        root = Compartment(
            id=context["root_compartment_id"],
            name="root",
            parent_id="",
            path="root",
            lifecycle_state="ACTIVE",
            description=context["tenant_name"],
        )
        compartments = [root]
        for item in context["raw_compartments"]:
            item_id = getattr(item, "id", "")
            compartments.append(
                Compartment(
                    id=item_id,
                    name=getattr(item, "name", item_id),
                    parent_id=getattr(item, "compartment_id", ""),
                    path=context["compartments"].path_for(item_id),
                    lifecycle_state=getattr(item, "lifecycle_state", "") or "",
                    description=getattr(item, "description", "") or "",
                )
            )
        return sorted(
            compartments,
            key=lambda item: (item.path != "root", item.path.lower()),
        )

    def _fetch_infrastructures(self, context: Dict[str, Any]) -> List[ExadataInfrastructure]:
        infrastructures: List[ExadataInfrastructure] = []
        seen: set[str] = set()
        for region in context["scan_regions"]:
            config = self._region_config(context["config"], region)
            database_client = self.oci.database.DatabaseClient(config)
            for item in self._list_database_resources(
                context, database_client, "list_exadata_infrastructures"
            ):
                item_id = getattr(item, "id", "")
                if not item_id or item_id in seen:
                    continue
                seen.add(item_id)
                try:
                    response = database_client.get_exadata_infrastructure(
                        exadata_infrastructure_id=item_id,
                        retry_strategy=self.retry_strategy,
                    )
                    item = response.data
                except Exception:
                    pass
                infrastructures.append(
                    self._to_infrastructure(context, region, item)
                )
        return infrastructures

    def _fetch_vm_clusters(
        self,
        context: Dict[str, Any],
        infrastructure_by_id: Dict[str, ExadataInfrastructure],
    ) -> List[VmCluster]:
        vm_clusters: List[VmCluster] = []
        seen: set[str] = set()
        for region in context["scan_regions"]:
            config = self._region_config(context["config"], region)
            database_client = self.oci.database.DatabaseClient(config)
            for item in self._list_database_resources(
                context, database_client, "list_vm_clusters"
            ):
                item_id = getattr(item, "id", "")
                if not item_id or item_id in seen:
                    continue
                seen.add(item_id)
                try:
                    response = database_client.get_vm_cluster(
                        vm_cluster_id=item_id,
                        retry_strategy=self.retry_strategy,
                    )
                    item = response.data
                except Exception:
                    pass
                vm_clusters.append(
                    self._to_vm_cluster(
                        context, region, item, infrastructure_by_id
                    )
                )
        return vm_clusters

    def _fetch_autonomous_vm_clusters(
        self,
        context: Dict[str, Any],
        infrastructure_by_id: Dict[str, ExadataInfrastructure],
    ) -> List[AutonomousVmCluster]:
        clusters: List[AutonomousVmCluster] = []
        seen: set[str] = set()
        for region in context["scan_regions"]:
            config = self._region_config(context["config"], region)
            database_client = self.oci.database.DatabaseClient(config)
            for item in self._list_database_resources(
                context, database_client, "list_autonomous_vm_clusters"
            ):
                item_id = getattr(item, "id", "")
                if not item_id or item_id in seen:
                    continue
                if getattr(item, "lifecycle_state", "") == "TERMINATED":
                    continue
                seen.add(item_id)
                try:
                    response = database_client.get_autonomous_vm_cluster(
                        autonomous_vm_cluster_id=item_id,
                        retry_strategy=self.retry_strategy,
                    )
                    item = response.data
                except Exception:
                    pass
                clusters.append(
                    self._to_autonomous_vm_cluster(
                        context, region, item, infrastructure_by_id
                    )
                )
        return clusters

    def _fetch_db_homes(
        self,
        context: Dict[str, Any],
        vm_cluster_by_id: Dict[str, VmCluster],
    ) -> List[DbHome]:
        db_homes: List[DbHome] = []
        seen: set[str] = set()
        vm_cluster_ids = set(vm_cluster_by_id)
        for region in context["scan_regions"]:
            config = self._region_config(context["config"], region)
            database_client = self.oci.database.DatabaseClient(config)
            for item in self._list_database_resources(
                context, database_client, "list_db_homes"
            ):
                item_id = getattr(item, "id", "")
                vm_cluster_id = getattr(item, "vm_cluster_id", "") or ""
                if not item_id or item_id in seen or vm_cluster_id not in vm_cluster_ids:
                    continue
                seen.add(item_id)
                db_homes.append(
                    self._to_db_home(context, region, item, vm_cluster_by_id)
                )
        return db_homes

    def _fetch_databases(
        self,
        context: Dict[str, Any],
        db_home_by_id: Dict[str, DbHome],
    ) -> List[Database]:
        databases: List[Database] = []
        seen: set[str] = set()
        for region in context["scan_regions"]:
            config = self._region_config(context["config"], region)
            database_client = self.oci.database.DatabaseClient(config)
            for db_home in db_home_by_id.values():
                if db_home.region != region:
                    continue
                try:
                    response = self.oci.pagination.list_call_get_all_results(
                        database_client.list_databases,
                        compartment_id=db_home.compartment_id,
                        db_home_id=db_home.id,
                        retry_strategy=self.retry_strategy,
                    )
                except Exception:
                    continue
                for item in response.data:
                    item_id = getattr(item, "id", "")
                    if not item_id or item_id in seen:
                        continue
                    seen.add(item_id)
                    databases.append(
                        self._to_database(context, region, item, db_home_by_id)
                    )
        return databases

    def _fetch_pluggable_databases(
        self,
        context: Dict[str, Any],
        database_by_id: Dict[str, Database],
    ) -> List[PluggableDatabase]:
        pluggable_databases: List[PluggableDatabase] = []
        seen: set[str] = set()
        for region in context["scan_regions"]:
            config = self._region_config(context["config"], region)
            database_client = self.oci.database.DatabaseClient(config)
            for database in database_by_id.values():
                if database.region != region:
                    continue
                try:
                    response = self.oci.pagination.list_call_get_all_results(
                        database_client.list_pluggable_databases,
                        database_id=database.id,
                        retry_strategy=self.retry_strategy,
                    )
                except Exception:
                    continue
                for item in response.data:
                    item_id = getattr(item, "id", "")
                    if not item_id or item_id in seen:
                        continue
                    seen.add(item_id)
                    pluggable_databases.append(
                        self._to_pluggable_database(
                            context, region, item, database_by_id
                        )
                    )
        return pluggable_databases

    def _list_database_resources(
        self, context: Dict[str, Any], database_client: Any, method_name: str
    ) -> List[Any]:
        resources: List[Any] = []
        list_method = getattr(database_client, method_name)
        for compartment_id in context["compartment_ids"]:
            try:
                response = self.oci.pagination.list_call_get_all_results(
                    list_method,
                    compartment_id=compartment_id,
                    retry_strategy=self.retry_strategy,
                )
            except Exception:
                continue
            resources.extend(response.data)
        return resources

    def _fetch_metric_series(
        self,
        *,
        monitoring_client: Any,
        compartment_id: str,
        namespace: str,
        metric_name: str,
        display_name: str,
        unit: str,
        resource_id: str,
        filter_dimension_names: Iterable[str],
        group_by: str,
        start_time: datetime,
        end_time: datetime,
        interval: str,
    ) -> Dict[str, Any]:
        escaped_id = self._mql_value(resource_id)
        query = ""
        queries = []
        response_data = []
        last_error: Exception | None = None
        received_response = False

        for dimension_name in filter_dimension_names:
            query = (
                f'{metric_name}[{interval}]{{{dimension_name} = "{escaped_id}"}}'
                f".groupBy({group_by}).mean()"
            )
            queries.append(query)
            details = self.oci.monitoring.models.SummarizeMetricsDataDetails(
                namespace=namespace,
                query=query,
                start_time=start_time,
                end_time=end_time,
                resolution=interval,
            )
            try:
                response = monitoring_client.summarize_metrics_data(
                    compartment_id=compartment_id,
                    summarize_metrics_data_details=details,
                    retry_strategy=self.retry_strategy,
                )
            except Exception as exc:
                last_error = exc
                continue
            received_response = True
            response_data = list(response.data)
            if response_data:
                break

        if not received_response and last_error is not None:
            raise last_error

        series = []
        for item in response_data:
            dimensions = getattr(item, "dimensions", {}) or {}
            instance_name = dimensions.get("instanceName")
            host_name = dimensions.get("hostName")
            label = (
                f"{instance_name} / {host_name}"
                if instance_name and host_name
                else instance_name
                or host_name
                or dimensions.get("resourceName_database")
                or dimensions.get("resourceName_pdb")
                or dimensions.get("resourceName_dbnode")
                or dimensions.get("resourceName")
                or metric_name
            )
            datapoints = []
            for datapoint in getattr(item, "aggregated_datapoints", []) or []:
                datapoints.append(
                    {
                        "timestamp": self._stringify_time(
                            getattr(datapoint, "timestamp", "")
                        ),
                        "value": getattr(datapoint, "value", None),
                    }
                )
            series.append(
                {
                    "label": label,
                    "dimensions": dimensions,
                    "points": sorted(
                        datapoints, key=lambda point: point.get("timestamp", "")
                    ),
                }
            )
        return {
            "name": metric_name,
            "display_name": display_name,
            "unit": unit,
            "query": query,
            "queries": queries,
            "series": sorted(series, key=lambda item: item.get("label", "")),
        }

    def _to_cost_row(self, item: Any, query_type: str) -> Dict[str, Any]:
        computed_amount = self._safe_float(getattr(item, "computed_amount", None))
        computed_quantity = self._safe_float(getattr(item, "computed_quantity", None))
        attributed_cost = self._safe_float(getattr(item, "attributed_cost", None))
        attributed_usage = self._safe_float(getattr(item, "attributed_usage", None))
        value = (
            computed_quantity if query_type == "USAGE" else computed_amount
        )
        if value == 0 and query_type == "USAGE":
            value = attributed_usage
        if value == 0 and query_type == "COST":
            value = attributed_cost
        return {
            "period_start": self._stringify_time(
                getattr(item, "time_usage_started", "")
            ),
            "period_end": self._stringify_time(getattr(item, "time_usage_ended", "")),
            "sku_name": getattr(item, "sku_name", "") or "",
            "sku_part_number": getattr(item, "sku_part_number", "") or "",
            "service": getattr(item, "service", "") or "",
            "resource_name": getattr(item, "resource_name", "") or "",
            "resource_id": getattr(item, "resource_id", "") or "",
            "region": getattr(item, "region", "") or "",
            "compartment_name": getattr(item, "compartment_name", "") or "",
            "computed_amount": computed_amount,
            "computed_quantity": computed_quantity,
            "value": value,
            "unit": getattr(item, "unit", "") or "",
            "currency": getattr(item, "currency", "") or "",
        }

    def _to_cost_analysis_payload(
        self,
        *,
        context: Dict[str, Any],
        start_time: datetime,
        end_time: datetime,
        granularity: str,
        query_type: str,
        rows: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        series_names = sorted({row["sku_name"] or "Unknown SKU" for row in rows})
        period_map: Dict[str, Dict[str, Any]] = {}
        totals_by_sku = {name: 0.0 for name in series_names}
        total = 0.0
        for row in rows:
            period = row["period_start"] or self._stringify_time(start_time)
            sku_name = row["sku_name"] or "Unknown SKU"
            bucket = period_map.setdefault(
                period,
                {"period": period, "series": {name: 0.0 for name in series_names}},
            )
            value = self._safe_float(row.get("value"))
            bucket["series"][sku_name] = bucket["series"].get(sku_name, 0.0) + value
            bucket["total"] = bucket.get("total", 0.0) + value
            totals_by_sku[sku_name] = totals_by_sku.get(sku_name, 0.0) + value
            total += value

        periods = sorted(period_map.values(), key=lambda item: item["period"])
        series = [
            {
                "label": name,
                "total": round(totals_by_sku.get(name, 0.0), 6),
                "points": [
                    {
                        "period": period["period"],
                        "value": round(period["series"].get(name, 0.0), 6),
                    }
                    for period in periods
                ],
            }
            for name in series_names
        ]
        currency = next((row["currency"] for row in rows if row.get("currency")), "")
        unit = next((row["unit"] for row in rows if row.get("unit")), "")
        return {
            "tenant_name": context["tenant_name"],
            "tenancy_id": context["tenancy_id"],
            "start_time": self._stringify_time(start_time),
            "end_time": self._stringify_time(end_time),
            "granularity": granularity,
            "query_type": query_type,
            "currency": currency,
            "unit": unit,
            "total": round(total, 6),
            "series_names": series_names,
            "periods": periods,
            "series": series,
            "details": sorted(
                rows,
                key=lambda row: (
                    row.get("period_start", ""),
                    row.get("sku_name", ""),
                ),
            ),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "filter": "Database Exadata Cloud@Customer OCPU and OCPU BYOL",
        }

    def _to_budget_row(self, item: Any) -> Dict[str, Any]:
        amount = self._safe_float(getattr(item, "amount", None))
        actual_spend = self._safe_float(getattr(item, "actual_spend", None))
        forecasted_spend = self._safe_float(getattr(item, "forecasted_spend", None))
        return {
            "id": getattr(item, "id", "") or "",
            "display_name": getattr(item, "display_name", "") or "",
            "description": getattr(item, "description", "") or "",
            "amount": amount,
            "actual_spend": actual_spend,
            "forecasted_spend": forecasted_spend,
            "percent_used": round((actual_spend / amount) * 100, 2)
            if amount > 0
            else 0.0,
            "reset_period": getattr(item, "reset_period", "") or "",
            "target_type": getattr(item, "target_type", "") or "",
            "targets": list(getattr(item, "targets", []) or []),
            "lifecycle_state": getattr(item, "lifecycle_state", "") or "",
            "alert_rule_count": safe_int(getattr(item, "alert_rule_count", 0)),
            "time_spend_computed": self._stringify_time(
                getattr(item, "time_spend_computed", "")
            ),
            "time_created": self._stringify_time(getattr(item, "time_created", "")),
        }

    @staticmethod
    def _safe_float(value: Any) -> float:
        try:
            if value in (None, ""):
                return 0.0
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _is_exacc_ocpu_sku(sku_name: str) -> bool:
        normalized = str(sku_name or "").lower().replace("@", " at ")
        return all(term in normalized for term in EXACC_COST_SKU_TERMS)

    def _to_infrastructure(
        self, context: Dict[str, Any], region: str, item: Any
    ) -> ExadataInfrastructure:
        return ExadataInfrastructure(
            id=item.id,
            region=region,
            compartment_id=getattr(item, "compartment_id", ""),
            compartment_path=context["compartments"].path_for(
                getattr(item, "compartment_id", "")
            ),
            display_name=getattr(item, "display_name", item.id),
            lifecycle_state=getattr(item, "lifecycle_state", ""),
            shape=getattr(item, "shape", ""),
            compute_count=safe_int(getattr(item, "compute_count", 0)),
            storage_count=safe_int(getattr(item, "storage_count", 0)),
            cpus_enabled=safe_int(getattr(item, "cpus_enabled", 0)),
            max_cpu_count=safe_int(getattr(item, "max_cpu_count", 0)),
            console_url=self._console_url(
                context, "exacc/infrastructures", item.id, region
            ),
        )

    def _to_vm_cluster(
        self,
        context: Dict[str, Any],
        region: str,
        item: Any,
        infrastructure_by_id: Dict[str, ExadataInfrastructure],
    ) -> VmCluster:
        infrastructure_id = getattr(item, "exadata_infrastructure_id", "")
        infrastructure = infrastructure_by_id.get(infrastructure_id)
        db_servers = getattr(item, "db_servers", []) or []
        return VmCluster(
            id=item.id,
            region=region,
            compartment_id=getattr(item, "compartment_id", ""),
            compartment_path=context["compartments"].path_for(
                getattr(item, "compartment_id", "")
            ),
            display_name=getattr(item, "display_name", item.id),
            lifecycle_state=getattr(item, "lifecycle_state", ""),
            exadata_infrastructure_id=infrastructure_id,
            exadata_infrastructure_name=(
                infrastructure.display_name if infrastructure else ""
            ),
            db_node_count=len(db_servers),
            cpus_enabled=safe_int(getattr(item, "cpus_enabled", 0)),
            memory_size_in_gbs=safe_int(getattr(item, "memory_size_in_gbs", 0)),
            gi_version=getattr(item, "gi_version", "") or "",
            system_version=getattr(item, "system_version", "") or "",
            console_url=self._console_url(context, "exacc/clusters", item.id, region),
        )

    def _to_autonomous_vm_cluster(
        self,
        context: Dict[str, Any],
        region: str,
        item: Any,
        infrastructure_by_id: Dict[str, ExadataInfrastructure],
    ) -> AutonomousVmCluster:
        infrastructure_id = getattr(item, "exadata_infrastructure_id", "")
        infrastructure = infrastructure_by_id.get(infrastructure_id)
        return AutonomousVmCluster(
            id=item.id,
            region=region,
            compartment_id=getattr(item, "compartment_id", ""),
            compartment_path=context["compartments"].path_for(
                getattr(item, "compartment_id", "")
            ),
            display_name=getattr(item, "display_name", item.id),
            lifecycle_state=getattr(item, "lifecycle_state", ""),
            exadata_infrastructure_id=infrastructure_id,
            exadata_infrastructure_name=(
                infrastructure.display_name if infrastructure else ""
            ),
            cpus_enabled=safe_int(getattr(item, "cpus_enabled", 0)),
            console_url=self._console_url(context, "exacc/clusters", item.id, region),
        )

    def _to_db_home(
        self,
        context: Dict[str, Any],
        region: str,
        item: Any,
        vm_cluster_by_id: Dict[str, VmCluster],
    ) -> DbHome:
        vm_cluster_id = getattr(item, "vm_cluster_id", "") or ""
        vm_cluster = vm_cluster_by_id.get(vm_cluster_id)
        display_name = (
            getattr(item, "display_name", "")
            or getattr(item, "db_home_location", "")
            or getattr(item, "id", "")
        )
        return DbHome(
            id=item.id,
            region=region,
            compartment_id=getattr(item, "compartment_id", ""),
            compartment_path=context["compartments"].path_for(
                getattr(item, "compartment_id", "")
            ),
            display_name=display_name,
            lifecycle_state=getattr(item, "lifecycle_state", ""),
            vm_cluster_id=vm_cluster_id,
            vm_cluster_name=vm_cluster.display_name if vm_cluster else "",
            db_version=getattr(item, "db_version", "") or "",
            db_home_location=getattr(item, "db_home_location", "") or "",
            lifecycle_details=getattr(item, "lifecycle_details", "") or "",
            time_created=self._stringify_time(getattr(item, "time_created", "")),
            database_software_image_id=getattr(
                item, "database_software_image_id", ""
            )
            or "",
            last_patch_history_entry_id=getattr(
                item, "last_patch_history_entry_id", ""
            )
            or "",
            console_url=self._console_url(context, "db/db-homes", item.id, region),
        )

    def _to_database(
        self,
        context: Dict[str, Any],
        region: str,
        item: Any,
        db_home_by_id: Dict[str, DbHome],
    ) -> Database:
        db_home_id = getattr(item, "db_home_id", "") or ""
        db_home = db_home_by_id.get(db_home_id)
        compartment_id = getattr(item, "compartment_id", "") or (
            db_home.compartment_id if db_home else ""
        )
        db_name = getattr(item, "db_name", "") or ""
        display_name = (
            getattr(item, "display_name", "")
            or db_name
            or getattr(item, "db_unique_name", "")
            or getattr(item, "id", "")
        )
        return Database(
            id=item.id,
            region=region,
            compartment_id=compartment_id,
            compartment_path=context["compartments"].path_for(compartment_id),
            display_name=display_name,
            lifecycle_state=getattr(item, "lifecycle_state", ""),
            db_home_id=db_home_id,
            db_home_name=db_home.display_name if db_home else "",
            vm_cluster_id=db_home.vm_cluster_id if db_home else "",
            vm_cluster_name=db_home.vm_cluster_name if db_home else "",
            db_name=db_name,
            db_unique_name=getattr(item, "db_unique_name", "") or "",
            pdb_name=getattr(item, "pdb_name", "") or "",
            db_workload=getattr(item, "db_workload", "") or "",
            lifecycle_details=getattr(item, "lifecycle_details", "") or "",
            time_created=self._stringify_time(getattr(item, "time_created", "")),
            last_backup_timestamp=self._stringify_time(
                getattr(item, "last_backup_timestamp", "")
            ),
            patch_version=getattr(item, "patch_version", "") or "",
            is_cdb=bool(getattr(item, "is_cdb", False)),
            sid_prefix=getattr(item, "sid_prefix", "") or "",
            database_software_image_id=getattr(
                item, "database_software_image_id", ""
            )
            or "",
            character_set=getattr(item, "character_set", "") or "",
            ncharacter_set=getattr(item, "ncharacter_set", "") or "",
            console_url=self._console_url(context, "db/databases", item.id, region),
        )

    def _to_pluggable_database(
        self,
        context: Dict[str, Any],
        region: str,
        item: Any,
        database_by_id: Dict[str, Database],
    ) -> PluggableDatabase:
        database_id = getattr(item, "container_database_id", "") or ""
        database = database_by_id.get(database_id)
        compartment_id = getattr(item, "compartment_id", "") or (
            database.compartment_id if database else ""
        )
        pdb_name = getattr(item, "pdb_name", "") or ""
        display_name = pdb_name or getattr(item, "id", "")
        return PluggableDatabase(
            id=item.id,
            region=region,
            compartment_id=compartment_id,
            compartment_path=context["compartments"].path_for(compartment_id),
            display_name=display_name,
            lifecycle_state=getattr(item, "lifecycle_state", ""),
            database_id=database_id,
            database_name=database.display_name if database else "",
            db_home_id=database.db_home_id if database else "",
            db_home_name=database.db_home_name if database else "",
            vm_cluster_id=database.vm_cluster_id if database else "",
            vm_cluster_name=database.vm_cluster_name if database else "",
            pdb_name=pdb_name,
            open_mode=getattr(item, "open_mode", "") or "",
            is_restricted=bool(getattr(item, "is_restricted", False)),
            lifecycle_details=getattr(item, "lifecycle_details", "") or "",
            time_created=self._stringify_time(getattr(item, "time_created", "")),
            patch_version=getattr(item, "patch_version", "") or "",
            console_url=self._console_url(
                context, "db/pluggable-databases", item.id, region
            ),
        )

    def _search(self, search_client: Any, resource_type: str) -> Iterable[Any]:
        details = self.oci.resource_search.models.StructuredSearchDetails(
            type="Structured", query=f"query {resource_type} resources"
        )
        response = self.oci.pagination.list_call_get_all_results(
            search_client.search_resources,
            details,
            retry_strategy=self.retry_strategy,
        )
        return getattr(response.data, "items", [])

    @staticmethod
    def _region_config(config: Dict[str, Any], region: str) -> Dict[str, Any]:
        region_config = dict(config)
        region_config["region"] = region
        return region_config

    @staticmethod
    def _stringify_time(value: Any) -> str:
        if not value:
            return ""
        isoformat = getattr(value, "isoformat", None)
        if callable(isoformat):
            return isoformat()
        return str(value)

    @staticmethod
    def _mql_value(value: str) -> str:
        return str(value).replace("\\", "\\\\").replace('"', '\\"')

    @staticmethod
    def _console_url(
        context: Dict[str, Any], resource_path: str, resource_id: str, region: str
    ) -> str:
        tenant = quote(str(context["tenant_name"]).lower())
        home_region = context["home_region"]
        return (
            f"https://console.{home_region}.oraclecloud.com/{resource_path}/"
            f"{resource_id}?tenant={tenant}&region={region}"
        )
