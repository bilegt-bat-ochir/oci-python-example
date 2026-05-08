from __future__ import annotations

from datetime import datetime, timezone

from .models import (
    AutonomousVmCluster,
    Compartment,
    ExadataInfrastructure,
    Inventory,
    VmCluster,
)


def empty_inventory() -> Inventory:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    return Inventory(
        tenant_name="No profile loaded",
        home_region="",
        generated_at=generated_at,
        regions=[],
        compartments=[
            Compartment(
                id="root",
                name="root",
                parent_id="",
                path="root",
                lifecycle_state="ACTIVE",
            )
        ],
        infrastructures=[],
        vm_clusters=[],
        autonomous_vm_clusters=[],
    )


def sample_inventory() -> Inventory:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    home_region = "eu-frankfurt-1"
    tenant = "demo-tenant"
    compartments = [
        Compartment(
            id="ocid1.tenancy.demo",
            name="root",
            parent_id="",
            path="root",
            lifecycle_state="ACTIVE",
            description=tenant,
        ),
        Compartment(
            id="ocid1.compartment.demo.exacc",
            name="ExaCC",
            parent_id="ocid1.tenancy.demo",
            path="ExaCC",
            lifecycle_state="ACTIVE",
        ),
        Compartment(
            id="ocid1.compartment.demo.production",
            name="production",
            parent_id="ocid1.compartment.demo.exacc",
            path="ExaCC:production",
            lifecycle_state="ACTIVE",
        ),
        Compartment(
            id="ocid1.compartment.demo.billing",
            name="billing",
            parent_id="ocid1.compartment.demo.production",
            path="ExaCC:production:billing",
            lifecycle_state="ACTIVE",
        ),
        Compartment(
            id="ocid1.compartment.demo.warehouse",
            name="warehouse",
            parent_id="ocid1.compartment.demo.production",
            path="ExaCC:production:warehouse",
            lifecycle_state="ACTIVE",
        ),
        Compartment(
            id="ocid1.compartment.demo.autonomous",
            name="autonomous",
            parent_id="ocid1.compartment.demo.production",
            path="ExaCC:production:autonomous",
            lifecycle_state="ACTIVE",
        ),
        Compartment(
            id="ocid1.compartment.demo.nonproduction",
            name="nonproduction",
            parent_id="ocid1.compartment.demo.exacc",
            path="ExaCC:nonproduction",
            lifecycle_state="ACTIVE",
        ),
    ]

    infrastructures = [
        ExadataInfrastructure(
            id="ocid1.exadatainfrastructure.demo.infra1",
            region="uk-london-1",
            compartment_id="ocid1.compartment.demo.infrastructure",
            compartment_path="ExaCC:production",
            display_name="prod-x10m-infra",
            lifecycle_state="ACTIVE",
            shape="ExadataCC.X10M",
            compute_count=4,
            storage_count=6,
            cpus_enabled=144,
            max_cpu_count=760,
            console_url=(
                f"https://console.{home_region}.oraclecloud.com/exacc/"
                f"infrastructures/ocid1.exadatainfrastructure.demo.infra1"
                f"?tenant={tenant}&region=uk-london-1"
            ),
        ),
        ExadataInfrastructure(
            id="ocid1.exadatainfrastructure.demo.infra2",
            region="eu-frankfurt-1",
            compartment_id="ocid1.compartment.demo.infrastructure",
            compartment_path="ExaCC:nonproduction",
            display_name="test-x9m-infra",
            lifecycle_state="REQUIRES_ACTIVATION",
            shape="ExadataCC.X9M",
            compute_count=4,
            storage_count=6,
            cpus_enabled=16,
            max_cpu_count=248,
            console_url=(
                f"https://console.{home_region}.oraclecloud.com/exacc/"
                f"infrastructures/ocid1.exadatainfrastructure.demo.infra2"
                f"?tenant={tenant}&region=eu-frankfurt-1"
            ),
        ),
    ]

    vm_clusters = [
        VmCluster(
            id="ocid1.vmcluster.demo.cluster1",
            region="uk-london-1",
            compartment_id="ocid1.compartment.demo.cluster1",
            compartment_path="ExaCC:production:billing",
            display_name="billing-vm1",
            lifecycle_state="AVAILABLE",
            exadata_infrastructure_id=infrastructures[0].id,
            exadata_infrastructure_name=infrastructures[0].display_name,
            db_node_count=2,
            cpus_enabled=24,
            memory_size_in_gbs=768,
            gi_version="19.23.0.0.0",
            system_version="24.1.3.0.0",
            console_url=(
                f"https://console.{home_region}.oraclecloud.com/exacc/"
                f"clusters/ocid1.vmcluster.demo.cluster1"
                f"?tenant={tenant}&region=uk-london-1"
            ),
        ),
        VmCluster(
            id="ocid1.vmcluster.demo.cluster2",
            region="uk-london-1",
            compartment_id="ocid1.compartment.demo.cluster2",
            compartment_path="ExaCC:production:warehouse",
            display_name="warehouse-vm1",
            lifecycle_state="UPDATING",
            exadata_infrastructure_id=infrastructures[0].id,
            exadata_infrastructure_name=infrastructures[0].display_name,
            db_node_count=2,
            cpus_enabled=12,
            memory_size_in_gbs=512,
            gi_version="19.22.0.0.0",
            system_version="23.1.9.0.0",
            console_url=(
                f"https://console.{home_region}.oraclecloud.com/exacc/"
                f"clusters/ocid1.vmcluster.demo.cluster2"
                f"?tenant={tenant}&region=uk-london-1"
            ),
        ),
    ]

    autonomous = [
        AutonomousVmCluster(
            id="ocid1.autonomousvmcluster.demo.avmc1",
            region="uk-london-1",
            compartment_id="ocid1.compartment.demo.autonomous",
            compartment_path="ExaCC:production:autonomous",
            display_name="prod-autonomous-vm",
            lifecycle_state="AVAILABLE",
            exadata_infrastructure_id=infrastructures[0].id,
            exadata_infrastructure_name=infrastructures[0].display_name,
            cpus_enabled=108,
            console_url=(
                f"https://console.{home_region}.oraclecloud.com/exacc/"
                f"clusters/ocid1.autonomousvmcluster.demo.avmc1"
                f"?tenant={tenant}&region=uk-london-1"
            ),
        )
    ]

    return Inventory(
        tenant_name=tenant,
        home_region=home_region,
        generated_at=generated_at,
        regions=["uk-london-1", "eu-frankfurt-1"],
        compartments=compartments,
        infrastructures=infrastructures,
        vm_clusters=vm_clusters,
        autonomous_vm_clusters=autonomous,
    )
