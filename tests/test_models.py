import unittest

from exacc_app.models import (
    Compartment,
    ExadataInfrastructure,
    Inventory,
    VmCluster,
    status_tone,
)


class InventoryModelTests(unittest.TestCase):
    def test_summary_counts_capacity_and_attention(self):
        inventory = Inventory(
            tenant_name="tenant",
            home_region="eu-frankfurt-1",
            generated_at="2026-01-01 00:00:00 UTC",
            regions=["eu-frankfurt-1", "uk-london-1"],
            compartments=[
                Compartment(
                    id="root",
                    name="root",
                    parent_id="",
                    path="root",
                    lifecycle_state="ACTIVE",
                )
            ],
            infrastructures=[
                ExadataInfrastructure(
                    id="infra1",
                    region="eu-frankfurt-1",
                    compartment_id="root",
                    compartment_path="root",
                    display_name="infra",
                    lifecycle_state="ACTIVE",
                    cpus_enabled=25,
                    max_cpu_count=100,
                )
            ],
            vm_clusters=[
                VmCluster(
                    id="vm1",
                    region="eu-frankfurt-1",
                    compartment_id="c1",
                    compartment_path="root:c1",
                    display_name="vm",
                    lifecycle_state="UPDATING",
                    cpus_enabled=8,
                    memory_size_in_gbs=256,
                )
            ],
        )

        summary = inventory.summary()

        self.assertEqual(summary["resource_count"], 2)
        self.assertEqual(summary["healthy_resources"], 1)
        self.assertEqual(summary["attention_resources"], 1)
        self.assertEqual(summary["compartment_count"], 1)
        self.assertEqual(summary["capacity_used_pct"], 25.0)
        self.assertEqual(summary["total_memory_gbs"], 256)

    def test_status_tone_maps_operational_states(self):
        self.assertEqual(status_tone("AVAILABLE"), "healthy")
        self.assertEqual(status_tone("TERMINATING"), "attention")
        self.assertEqual(status_tone("REQUIRES_ACTIVATION"), "critical")
        self.assertEqual(status_tone("SOMETHING_NEW"), "neutral")


if __name__ == "__main__":
    unittest.main()
