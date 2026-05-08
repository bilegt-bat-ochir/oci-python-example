import tempfile
import unittest
from pathlib import Path

from exacc_app.oci_gateway import OCIAppError
from exacc_app.server import list_oci_profiles


class ServerProfileTests(unittest.TestCase):
    def test_list_oci_profiles_returns_default_first(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Path(tmpdir) / "config"
            config.write_text(
                "\n".join(
                    [
                        "[DEFAULT]",
                        "user=ocid1.user.oc1..demo",
                        "region=eu-frankfurt-1",
                        "[ADMIN]",
                        "region=uk-london-1",
                        "[billing]",
                        "region=us-ashburn-1",
                    ]
                ),
                encoding="utf-8",
            )

            profiles = list_oci_profiles(str(config))

        self.assertEqual(profiles, ["DEFAULT", "ADMIN", "billing"])

    def test_list_oci_profiles_reports_missing_config(self):
        with self.assertRaises(OCIAppError):
            list_oci_profiles("/missing/oci/config")


if __name__ == "__main__":
    unittest.main()
