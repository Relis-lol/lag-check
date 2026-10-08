"""Only synthetic fixtures; no user's diagnostics data."""

import csv
import datetime as dt
import json
from pathlib import Path
import tempfile
import unittest

from lagcheck.analysis import analyze, safe_export, network_state, coverage
from scripts.check_publish import violations


class AnalysisTests(unittest.TestCase):
    def fixture(
        self,
        kind="FREEZE",
        bad=None,
        hardware=False,
        missing=False,
        blocked=False,
        drop=False,
        escaped=False,
    ):
        start = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)

        def timestamp(i):
            return (start + dt.timedelta(seconds=i)).isoformat()

        with tempfile.TemporaryDirectory(prefix="lagcheck-synthetic-") as tmp:
            folder = Path(tmp)
            (folder / "session_info.json").write_text(
                json.dumps(
                    {
                        "start": timestamp(0),
                        "end": timestamp(60),
                        "options": {"network": True, "events": False, "alt_tab": True},
                    }
                )
            )

            def write(name, rows):
                with (folder / name).open("w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=list(rows[0]))
                    writer.writeheader()
                    writer.writerows(rows)

            write("lag_markers.csv", [{"timestamp": timestamp(30), "kind": kind}])
            write(
                "system_metrics.csv",
                [
                    {
                        "timestamp": timestamp(i),
                        "cpu_pct": 99 if hardware and i == 30 else 20,
                        "gpu_pct": 10 if drop and i == 21 else 80,
                        "counter_errors_json": "{}",
                    }
                    for i in range(61)
                    if not (missing and 20 <= i <= 40)
                ],
            )
            for key in ("gateway", "cloudflare", "google"):
                write(
                    f"network_{key}.csv",
                    [
                        {
                            "timestamp": timestamp(i),
                            "target": "synthetic-target",
                            "status": "TIMEOUT"
                            if blocked or (key == bad and i == 30)
                            else "SUCCESS",
                            "rtt_ms": ""
                            if blocked or (key == bad and i == 30)
                            else "10",
                        }
                        for i in range(61)
                        if not (missing and 20 <= i <= 40)
                    ],
                )
            result = analyze(folder)
            if escaped:
                self.assertNotIn(
                    "<script>", (folder / "report.html").read_text(encoding="utf-8")
                )
            return result

    def test_local(self):
        self.assertEqual(
            self.fixture(bad="gateway")["markers"][0]["category"], "NETWORK_LOCAL"
        )

    def test_internet(self):
        self.assertEqual(
            self.fixture(bad="google")["markers"][0]["category"], "NETWORK_INTERNET"
        )

    def test_hardware(self):
        self.assertEqual(
            self.fixture(hardware=True)["markers"][0]["category"],
            "CLIENT_OR_HARDWARE_STUTTER",
        )

    def test_route_is_only_possibility(self):
        self.assertEqual(
            self.fixture(kind="RUBBERBAND")["markers"][0]["category"],
            "NETWORK_GAME_ROUTE_OR_SERVER",
        )

    def test_unknown(self):
        self.assertEqual(self.fixture()["markers"][0]["category"], "UNKNOWN")

    def test_missing_never_clean(self):
        self.assertEqual(
            self.fixture(kind="RUBBERBAND", missing=True)["markers"][0]["category"],
            "UNKNOWN",
        )

    def test_always_blocked_never_local_fault(self):
        self.assertEqual(
            self.fixture(blocked=True)["markers"][0]["category"], "UNKNOWN"
        )

    def test_alt_tab_drop_does_not_blame_hardware(self):
        r = self.fixture(drop=True)["markers"][0]
        self.assertEqual(r["category"], "UNKNOWN")
        self.assertTrue(any("Alt-Tab" in n for n in r["notes"]))

    def test_missing_baseline(self):
        self.assertFalse(network_state([], 0, None)["clean"])
        self.assertFalse(coverage([], 0))

    def test_html_escaping(self):
        self.fixture(kind="<script>alert(1)</script>", escaped=True)

    def test_export_allowlist(self):
        secret = "PRIVATE_TEST_VALUE_DO_NOT_EXPORT"
        result = self.fixture(hardware=True)
        result["secret"] = secret
        result["start"] = secret
        result["network"]["gateway"]["target"] = secret
        result["markers"][0]["notes"] = [secret]
        result["markers"][0]["findings"][0]["text"] = secret
        exported = json.dumps(safe_export(result))
        self.assertNotIn(secret, exported)
        self.assertNotIn("timestamp", exported)
        self.assertNotIn("target", exported)

    def test_export_rejects_non_numeric_values(self):
        result = self.fixture()
        result["network"]["gateway"]["median"] = "private-string"
        result["network"]["gateway"]["max"] = float("nan")
        exported = safe_export(result)
        self.assertNotIn("median", exported["network"]["gateway"])
        self.assertNotIn("max", exported["network"]["gateway"])

    def test_secret_scanner(self):
        self.assertTrue(violations("anything.txt", ("gh" + "p_" + "a" * 30).encode()))
        self.assertTrue(violations("sessions/test.csv", b"timestamp,value"))
        self.assertFalse(violations("readme.md", b"No personal data here."))


if __name__ == "__main__":
    unittest.main()
