import unittest

from exacc_app.scaling import ScaleTags, decide_scale_action


class ScalingDecisionTests(unittest.TestCase):
    def test_missing_tags_are_silent_without_verbose(self):
        decision = decide_scale_action(
            cluster_id="cluster1",
            display_name="cluster",
            region="eu-frankfurt-1",
            compartment_path="root",
            lifecycle_state="AVAILABLE",
            cpus_enabled=8,
            defined_tags={},
            time_marker="10:00_UTC",
            tags=ScaleTags(),
            confirm=False,
            verbose=False,
        )

        self.assertIsNone(decision)

    def test_matching_down_time_returns_dry_run(self):
        decision = decide_scale_action(
            cluster_id="cluster1",
            display_name="cluster",
            region="eu-frankfurt-1",
            compartment_path="root",
            lifecycle_state="AVAILABLE",
            cpus_enabled=8,
            defined_tags={
                "osc_exacc": {
                    "scale_down_time": "10:00_UTC",
                    "scale_up_time": "18:00_UTC",
                    "scale_down_ocpus": "4",
                    "scale_up_ocpus": "12",
                }
            },
            time_marker="10:00_UTC",
            tags=ScaleTags(),
            confirm=False,
        )

        self.assertIsNotNone(decision)
        self.assertEqual(decision.outcome, "dry-run")
        self.assertEqual(decision.direction, "down")
        self.assertEqual(decision.desired_ocpus, 4)

    def test_confirm_marks_matching_action_for_submission(self):
        decision = decide_scale_action(
            cluster_id="cluster1",
            display_name="cluster",
            region="eu-frankfurt-1",
            compartment_path="root",
            lifecycle_state="AVAILABLE",
            cpus_enabled=8,
            defined_tags={
                "osc_exacc": {
                    "scale_down_time": "10:00_UTC",
                    "scale_up_time": "18:00_UTC",
                    "scale_down_ocpus": "4",
                    "scale_up_ocpus": "12",
                }
            },
            time_marker="18:00_UTC",
            tags=ScaleTags(),
            confirm=True,
        )

        self.assertTrue(decision.should_submit)
        self.assertEqual(decision.direction, "up")
        self.assertEqual(decision.desired_ocpus, 12)

    def test_non_available_cluster_is_ignored(self):
        decision = decide_scale_action(
            cluster_id="cluster1",
            display_name="cluster",
            region="eu-frankfurt-1",
            compartment_path="root",
            lifecycle_state="UPDATING",
            cpus_enabled=8,
            defined_tags={},
            time_marker="10:00_UTC",
            tags=ScaleTags(),
            confirm=True,
        )

        self.assertEqual(decision.outcome, "ignored")
        self.assertEqual(decision.reason, "cluster is not AVAILABLE")


if __name__ == "__main__":
    unittest.main()
