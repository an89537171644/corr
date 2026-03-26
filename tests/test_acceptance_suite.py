from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_acceptance_suite_script_runs_end_to_end(tmp_path: Path) -> None:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "run_acceptance_suite.py"
    output_dir = tmp_path / "acceptance"

    completed = subprocess.run(
        [sys.executable, str(script_path), "--output-dir", str(output_dir)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "ACCEPTANCE OK" in completed.stdout
    assert (output_dir / "demo_case_c4" / "summary.json").exists()
    assert (output_dir / "demo_case_c3_column" / "report.md").exists()
    assert (output_dir / "demo_case_c5_tube" / "report.pdf").exists()
