"""Compare baseline tests with one deliberately faulty cart subtotal."""

import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
import xml.etree.ElementTree as ET
import zipfile


ROOT = Path(__file__).resolve().parents[1]

ORIGINAL = (
    "subtotal_cents=sum(item.line_total_cents for item in items)"
)
FAULTY = (
    "subtotal_cents=sum(item.unit_price_cents for item in items)"
)


def run_tests(source, label, output, environment):
    report = output / f"{label}.xml"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "cartiva/backend/tests",
            "-v",
            f"--junitxml={report}",
        ],
        cwd=source,
        env=environment,
        capture_output=True,
        text=True,
        timeout=120,
    )

    (output / f"{label}.log").write_text(
        result.stdout + "\n" + result.stderr,
        encoding="utf-8",
    )

    if not report.exists():
        raise RuntimeError(f"{label}: no report; inspect {label}.log")

    cases = {}
    for case in ET.parse(report).getroot().iter("testcase"):
        identity = f"{case.get('classname')}::{case.get('name')}"
        if identity in cases:
            raise RuntimeError(f"Duplicate test identity: {identity}")

        outcome = "passed"
        for tag in ("error", "failure", "skipped"):
            if case.find(tag) is not None:
                outcome = tag
                break

        cases[identity] = outcome

    return result.returncode, cases


def main():
    changes = subprocess.check_output(
        ["git", "status", "--porcelain", "--", "cartiva"],
        cwd=ROOT,
        text=True,
    )
    if changes.strip():
        raise RuntimeError(
            "Cartiva has uncommitted files. Commit or review them first; "
            "this experiment uses the committed version."
        )

    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = ROOT / "reports" / "regression-demo" / stamp
    output.mkdir(parents=True)
    print(f"Reports: {output}", flush=True)

    archive = subprocess.check_output(
        ["git", "archive", "--format=zip", commit], cwd=ROOT
    )

    environment = os.environ.copy()
    environment.pop("PYTEST_ADDOPTS", None)
    environment.pop("PYTHONPATH", None)
    environment.update(
        {
            "CARTIVA_DB_HOST": "127.0.0.1",
            "CARTIVA_DB_PORT": "1",
            "CARTIVA_DB_NAME": "unused_regression_demo",
            "CARTIVA_DB_USER": "unused",
            "CARTIVA_DB_PASSWORD": "unused",
        }
    )

    with tempfile.TemporaryDirectory(prefix="cartiva-regression-") as temp:
        baseline = Path(temp) / "baseline"
        candidate = Path(temp) / "candidate"

        with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
            bundle.extractall(baseline)

        shutil.copytree(baseline, candidate)

        target = candidate / "cartiva/backend/cart.py"
        source = target.read_text(encoding="utf-8")
        if source.count(ORIGINAL) != 1:
            raise RuntimeError(
                "Expected subtotal expression not found exactly once. "
                "No experiment was run."
            )

        target.write_text(
            source.replace(ORIGINAL, FAULTY, 1),
            encoding="utf-8",
        )

        print("Running baseline...", flush=True)
        base_code, base_cases = run_tests(
            baseline, "baseline", output, environment
        )
        if (
            base_code != 0
            or not base_cases
            or any(value != "passed" for value in base_cases.values())
        ):
            raise RuntimeError(
                "Baseline did not fully pass. Inspect baseline.log."
            )

        print("Running faulty candidate...", flush=True)
        candidate_code, candidate_cases = run_tests(
            candidate, "candidate", output, environment
        )

        if base_cases.keys() != candidate_cases.keys():
            raise RuntimeError("Baseline and candidate collected different tests.")

        failures = sorted(
            name
            for name, outcome in candidate_cases.items()
            if outcome == "failure"
        )
        if (
            candidate_code != 1
            or not failures
            or any(
                outcome not in {"passed", "failure"}
                for outcome in candidate_cases.values()
            )
        ):
            raise RuntimeError(
                "Expected assertion failures were not obtained cleanly. "
                "Inspect candidate.log."
            )

        summary = {
            "baseline_commit": commit,
            "defect": "Cart subtotal ignores item quantities",
            "original_expression": ORIGINAL,
            "faulty_expression": FAULTY,
            "baseline_passed": len(base_cases),
            "candidate_passed": sum(
                outcome == "passed" for outcome in candidate_cases.values()
            ),
            "candidate_failed": len(failures),
            "newly_failing_tests": failures,
            "injected_defects": 1,
            "detected_defects": 1,
        }

        (output / "summary.json").write_text(
            json.dumps(summary, indent=2) + "\n",
            encoding="utf-8",
        )

        print(json.dumps(summary, indent=2))
        print("PASS: unchanged tests detected the injected subtotal defect.")
        print("The working application's source files were not modified.")


if __name__ == "__main__":
    main()