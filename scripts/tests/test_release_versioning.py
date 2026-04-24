from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

from bump_version import normalize_version  # noqa: E402
from validate_release import write_github_outputs  # noqa: E402
from versioning import parse_semver  # noqa: E402


class ReleaseVersioningTests(unittest.TestCase):
    def test_prerelease_suffixes_are_detected(self) -> None:
        for version in (
            "1.0.1-rc.99",
            "1.0.1-dev.1",
            "1.0.1-alpha.1",
            "1.0.1-beta.2",
        ):
            with self.subTest(version=version):
                self.assertTrue(parse_semver(version).is_prerelease)

    def test_final_version_is_not_prerelease(self) -> None:
        self.assertFalse(parse_semver("1.0.1").is_prerelease)

    def test_rc_helper_increments_current_rc(self) -> None:
        self.assertEqual(normalize_version("rc", "1.0.0-rc.2"), "1.0.0-rc.3")

    def test_rc_helper_starts_next_patch_from_final(self) -> None:
        self.assertEqual(normalize_version("rc", "1.0.0"), "1.0.1-rc.1")

    def test_final_helper_strips_prerelease_suffix(self) -> None:
        self.assertEqual(normalize_version("final", "1.0.0-rc.3"), "1.0.0")

    def test_github_outputs_keep_prereleases_out_of_latest(self) -> None:
        with tempfile.NamedTemporaryFile("r+", encoding="utf-8") as output:
            write_github_outputs(output.name, version="1.0.1-rc.99", prerelease=True)
            output.seek(0)
            contents = output.read()

        self.assertIn("version=1.0.1-rc.99\n", contents)
        self.assertIn("prerelease=true\n", contents)
        self.assertIn("make_latest=false\n", contents)

    def test_github_outputs_mark_final_release_as_latest(self) -> None:
        with tempfile.NamedTemporaryFile("r+", encoding="utf-8") as output:
            write_github_outputs(output.name, version="1.0.1", prerelease=False)
            output.seek(0)
            contents = output.read()

        self.assertIn("version=1.0.1\n", contents)
        self.assertIn("prerelease=false\n", contents)
        self.assertIn("make_latest=true\n", contents)


if __name__ == "__main__":
    unittest.main()
