from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Type, TypeVar


HEALTHY_STATES = {"ACTIVE", "AVAILABLE"}
ATTENTION_STATES = {
    "BACKUP_IN_PROGRESS",
    "CONVERTING",
    "DISABLED",
    "MAINTENANCE_IN_PROGRESS",
    "PROVISIONING",
    "REFRESHING",
    "RELOCATING",
    "RELOCATED",
    "RESTORE_IN_PROGRESS",
    "SCALE_IN_PROGRESS",
    "TERMINATING",
    "UPDATING",
    "UPGRADING",
}
CRITICAL_STATES = {
    "FAILED",
    "INACTIVE",
    "REQUIRES_ACTIVATION",
    "RESTORE_FAILED",
    "TERMINATED",
    "UNAVAILABLE",
}


def status_tone(status: str | None) -> str:
    normalized = (status or "").upper()
    if normalized in HEALTHY_STATES:
        return "healthy"
    if normalized in ATTENTION_STATES:
        return "attention"
    if normalized in CRITICAL_STATES:
        return "critical"
    return "neutral"


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


@dataclass
class Compartment:
    id: str
    name: str
    parent_id: str
    path: str
    lifecycle_state: str = ""
    description: str = ""


@dataclass
class ExadataInfrastructure:
    id: str
    region: str
    compartment_id: str
    compartment_path: str
    display_name: str
    lifecycle_state: str
    shape: str = ""
    compute_count: int = 0
    storage_count: int = 0
    cpus_enabled: int = 0
    max_cpu_count: int = 0
    console_url: str = ""

    @property
    def cpu_utilization(self) -> float:
        if self.max_cpu_count <= 0:
            return 0.0
        return min(100.0, round((self.cpus_enabled / self.max_cpu_count) * 100, 1))


@dataclass
class VmCluster:
    id: str
    region: str
    compartment_id: str
    compartment_path: str
    display_name: str
    lifecycle_state: str
    exadata_infrastructure_id: str = ""
    exadata_infrastructure_name: str = ""
    db_node_count: int = 0
    cpus_enabled: int = 0
    memory_size_in_gbs: int = 0
    gi_version: str = ""
    system_version: str = ""
    console_url: str = ""


@dataclass
class AutonomousVmCluster:
    id: str
    region: str
    compartment_id: str
    compartment_path: str
    display_name: str
    lifecycle_state: str
    exadata_infrastructure_id: str = ""
    exadata_infrastructure_name: str = ""
    cpus_enabled: int = 0
    console_url: str = ""


@dataclass
class DbHome:
    id: str
    region: str
    compartment_id: str
    compartment_path: str
    display_name: str
    lifecycle_state: str
    vm_cluster_id: str = ""
    vm_cluster_name: str = ""
    db_version: str = ""
    db_home_location: str = ""
    lifecycle_details: str = ""
    time_created: str = ""
    database_software_image_id: str = ""
    last_patch_history_entry_id: str = ""
    console_url: str = ""


@dataclass
class Database:
    id: str
    region: str
    compartment_id: str
    compartment_path: str
    display_name: str
    lifecycle_state: str
    db_home_id: str = ""
    db_home_name: str = ""
    vm_cluster_id: str = ""
    vm_cluster_name: str = ""
    db_name: str = ""
    db_unique_name: str = ""
    pdb_name: str = ""
    db_workload: str = ""
    lifecycle_details: str = ""
    time_created: str = ""
    last_backup_timestamp: str = ""
    patch_version: str = ""
    is_cdb: bool = False
    sid_prefix: str = ""
    database_software_image_id: str = ""
    character_set: str = ""
    ncharacter_set: str = ""
    console_url: str = ""


@dataclass
class PluggableDatabase:
    id: str
    region: str
    compartment_id: str
    compartment_path: str
    display_name: str
    lifecycle_state: str
    database_id: str = ""
    database_name: str = ""
    db_home_id: str = ""
    db_home_name: str = ""
    vm_cluster_id: str = ""
    vm_cluster_name: str = ""
    pdb_name: str = ""
    open_mode: str = ""
    is_restricted: bool = False
    lifecycle_details: str = ""
    time_created: str = ""
    patch_version: str = ""
    console_url: str = ""


T = TypeVar("T")


def _load_many(cls: Type[T], rows: Iterable[Dict[str, Any]]) -> List[T]:
    return [cls(**row) for row in rows]


@dataclass
class Inventory:
    tenant_name: str
    home_region: str
    generated_at: str
    regions: List[str] = field(default_factory=list)
    compartments: List[Compartment] = field(default_factory=list)
    infrastructures: List[ExadataInfrastructure] = field(default_factory=list)
    vm_clusters: List[VmCluster] = field(default_factory=list)
    autonomous_vm_clusters: List[AutonomousVmCluster] = field(default_factory=list)
    db_homes: List[DbHome] = field(default_factory=list)
    databases: List[Database] = field(default_factory=list)
    pluggable_databases: List[PluggableDatabase] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["summary"] = self.summary()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Inventory":
        return cls(
            tenant_name=data.get("tenant_name", ""),
            home_region=data.get("home_region", ""),
            generated_at=data.get("generated_at", ""),
            regions=list(data.get("regions", [])),
            compartments=_load_many(Compartment, data.get("compartments", [])),
            infrastructures=_load_many(
                ExadataInfrastructure, data.get("infrastructures", [])
            ),
            vm_clusters=_load_many(VmCluster, data.get("vm_clusters", [])),
            autonomous_vm_clusters=_load_many(
                AutonomousVmCluster, data.get("autonomous_vm_clusters", [])
            ),
            db_homes=_load_many(DbHome, data.get("db_homes", [])),
            databases=_load_many(Database, data.get("databases", [])),
            pluggable_databases=_load_many(
                PluggableDatabase, data.get("pluggable_databases", [])
            ),
        )

    def summary(self) -> Dict[str, Any]:
        infrastructure_count = len(self.infrastructures)
        vm_cluster_count = len(self.vm_clusters)
        autonomous_vm_cluster_count = len(self.autonomous_vm_clusters)
        db_home_count = len(self.db_homes)
        database_count = len(self.databases)
        pluggable_database_count = len(self.pluggable_databases)
        total_cluster_count = vm_cluster_count + autonomous_vm_cluster_count
        total_ocpus_enabled = sum(i.cpus_enabled for i in self.infrastructures)
        total_ocpu_capacity = sum(i.max_cpu_count for i in self.infrastructures)
        total_memory_gbs = sum(c.memory_size_in_gbs for c in self.vm_clusters)
        healthy_resources = sum(
            1
            for item in [
                *self.infrastructures,
                *self.vm_clusters,
                *self.autonomous_vm_clusters,
                *self.db_homes,
                *self.databases,
                *self.pluggable_databases,
            ]
            if status_tone(item.lifecycle_state) == "healthy"
        )
        resource_count = (
            infrastructure_count
            + vm_cluster_count
            + autonomous_vm_cluster_count
            + db_home_count
            + database_count
            + pluggable_database_count
        )
        attention_resources = resource_count - healthy_resources

        if total_ocpu_capacity > 0:
            capacity_used_pct = round((total_ocpus_enabled / total_ocpu_capacity) * 100, 1)
        else:
            capacity_used_pct = 0.0

        return {
            "infrastructure_count": infrastructure_count,
            "vm_cluster_count": vm_cluster_count,
            "autonomous_vm_cluster_count": autonomous_vm_cluster_count,
            "db_home_count": db_home_count,
            "database_count": database_count,
            "pluggable_database_count": pluggable_database_count,
            "total_cluster_count": total_cluster_count,
            "region_count": len(set(self.regions)),
            "compartment_count": len(self.compartments),
            "total_ocpus_enabled": total_ocpus_enabled,
            "total_ocpu_capacity": total_ocpu_capacity,
            "capacity_used_pct": capacity_used_pct,
            "total_memory_gbs": total_memory_gbs,
            "resource_count": resource_count,
            "healthy_resources": healthy_resources,
            "attention_resources": attention_resources,
        }
