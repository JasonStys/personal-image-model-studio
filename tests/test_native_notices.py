"""Jason Stys: mandatory isolated actual Tcl notice contracts with exact-case receipt. Symbol locations: generated source index."""
# Index: declarations module.test_all_thirteen_actual_notice_contracts_in_one_fresh_owned_interpreter@L14; variables root@L16, cases@L17, temporary@L18, result_path@L19, result@L20, records@L38, item@L40, item@L41, receipt@L42, item@L44, target@L55. Purposes/parameters: docs/code-map.json.

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from defusedxml import ElementTree as ET


def test_all_thirteen_actual_notice_contracts_in_one_fresh_owned_interpreter():
    """No retries/skips: preserve every real case, propagate failures and retain its source-bound JUnit identity."""
    root = Path(__file__).resolve().parents[1]
    cases = root / "tests/native_notice_cases.py"
    with tempfile.TemporaryDirectory(prefix="notice-contract-results-") as temporary:
        result_path = Path(temporary) / "results.xml"
        result = subprocess.run(  # noqa: S603 -- fixed owned interpreter and literal test module, no caller-supplied code
            [
                sys.executable,
                "-m",
                "pytest",
                str(cases),
                "--capture=sys",
                "-q",
                "-o",
                "cache_dir=" + str(Path(temporary) / "pytest-cache"),
                "--junitxml=" + str(result_path),
            ],
            cwd=root,
            text=True,
            capture_output=True,
            timeout=30,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        records = list(ET.parse(result_path).getroot().iter("testcase"))
        assert len(records) == 13
        assert len({item.attrib["name"] for item in records}) == 13
        assert not any(list(item) for item in records), result.stdout + result.stderr
        receipt = {
            "passed": True,
            "actual_cases": [item.attrib["name"] for item in records],
            "case_count": len(records),
            "interpreter": sys.version.split()[0],
            "capture": "sys; stable native descriptors",
            "retries": 0,
            "skipped": 0,
            "case_source_sha256": hashlib.sha256(cases.read_bytes()).hexdigest(),
            "reader_source_sha256": hashlib.sha256(
                (root / "scripts/native_notices.py").read_bytes()
            ).hexdigest(),
        }
        target = root / ".runtime/notices-contract.json"
        target.parent.mkdir(exist_ok=True)
        target.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        print("All13 actual isolated Tcl/Tk notice cases passed; no retries or skips.")
