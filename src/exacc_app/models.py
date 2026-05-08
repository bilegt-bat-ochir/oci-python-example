from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Type, TypeVar


HEALTHY_STATES = {"ACTIVE", "AVAILABLE"}
ATTENTION_STATES = {
    "BACKUP_IN_PROGRESS",
    "MAINTENANCE_IN_PROGRESS",
    "PROVISIONING",
    "SCALE_IN_PROGRESS",
    "TERMINATING",
    "UPDATING",
}
CRITICAL_STATES = {
    "FAILED",
    "INACTIVE",
    "REQUIRES_ACTIVATION",
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
        )

    def summary(self) -> Dict[str, Any]:
        infrastructure_count = len(self.infrastructures)
        vm_cluster_count = len(self.vm_clusters)
        autonomous_vm_cluster_count = len(self.autonomous_vm_clusters)
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
            ]
            if status_tone(item.lifecycle_state) == "healthy"
        )
        resource_count = (
            infrastructure_count + vm_cluster_count + autonomous_vm_cluster_count
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
