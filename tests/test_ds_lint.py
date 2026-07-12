"""Tests for the ds-lint.js PostToolUse hook.

Covers existing lint checks (fit-before-split, time-shuffle, etc.) and
the new H3 (stage-done-without-gate) and H4 (scope-guard) checks.
"""
import json
import os
import subprocess
import tempfile

import pytest

LINT_SCRIPT = os.path.join(
    os.path.dirname(__file__), "..", "hooks", "scripts", "ds-lint.js"
)


def run_lint(file_path: str, env_extra: dict | None = None) -> tuple[str, str, int]:
    """Run ds-lint with a synthetic PostToolUse input. Returns (stdout, stderr, exit_code)."""
    input_json = json.dumps({"tool_input": {"file_path": file_path}})
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    result = subprocess.run(
        ["node", LINT_SCRIPT],
        input=input_json,
        capture_output=True,
        text=True,
        env=env,
    )
    return result.stdout, result.stderr, result.returncode


class TestCodeLint:
    def test_catches_fit_before_split(self, tmp_path):
        bait = tmp_path / "bait.py"
        bait.write_text(
            "from sklearn.preprocessing import StandardScaler\n"
            "from sklearn.model_selection import train_test_split\n"
            "scaler = StandardScaler()\n"
            "X_scaled = scaler.fit_transform(X)\n"
            "X_train, X_test = train_test_split(X_scaled)\n"
        )
        _, stderr, _ = run_lint(str(bait))
        assert "fit" in stderr.lower() and "split" in stderr.lower()

    def test_catches_missing_seed(self, tmp_path):
        bait = tmp_path / "bait.py"
        bait.write_text(
            "from sklearn.model_selection import train_test_split\n"
            "X_train, X_test = train_test_split(X)\n"
        )
        _, stderr, _ = run_lint(str(bait))
        assert "seed" in stderr.lower() or "random_state" in stderr.lower()

    def test_clean_file_no_findings(self, tmp_path):
        clean = tmp_path / "clean.py"
        clean.write_text("x = 1 + 2\nprint(x)\n")
        _, stderr, code = run_lint(str(clean))
        assert code == 0
        assert stderr == ""


class TestH3StageWithoutGate:
    def test_catches_done_without_gate_ref(self, tmp_path):
        eds_dir = tmp_path / ".eds"
        eds_dir.mkdir()
        brief = eds_dir / "BRIEF.md"
        brief.write_text(
            "# Problem Brief\n\n## Status\nconfirmed\n\n## Plan\n"
            "- audit · data-audit · done · no gate ref\n"
            "- eda · eda-workflow · pending\n"
        )
        _, stderr, _ = run_lint(str(brief))
        assert "stage marked" in stderr.lower() or "H3" in stderr

    def test_passes_with_gate_ref(self, tmp_path):
        eds_dir = tmp_path / ".eds"
        eds_dir.mkdir()
        brief = eds_dir / "BRIEF.md"
        brief.write_text(
            "# Problem Brief\n\n## Status\nconfirmed\n\n## Plan\n"
            "- audit · data-audit · done · gate-record: verification/data-audit-20260710.json\n"
            "- eda · eda-workflow · pending\n"
        )
        _, stderr, _ = run_lint(str(brief))
        assert "H3" not in stderr

    def test_blocks_in_strict_mode(self, tmp_path):
        eds_dir = tmp_path / ".eds"
        eds_dir.mkdir()
        brief = eds_dir / "BRIEF.md"
        brief.write_text(
            "# Problem Brief\n\n## Status\nconfirmed\n\n## Plan\n"
            "- audit · data-audit · done · no gate ref\n"
        )
        _, stderr, code = run_lint(str(brief), env_extra={"EDS_HOOK_PROFILE": "strict"})
        assert code == 2


class TestH4ScopeGuard:
    def test_warns_on_out_of_scope_write(self, tmp_path):
        # Set up a project with a Plan showing eda as in-progress
        eds_dir = tmp_path / ".eds"
        eds_dir.mkdir()
        brief = eds_dir / "BRIEF.md"
        brief.write_text(
            "# Problem Brief\n\n## Status\nconfirmed\n\n## Plan\n"
            "- audit · data-audit · done · gate-record: verification/x.json\n"
            "- eda · eda-workflow · in-progress\n"
        )

        # Write to a model file while EDA is in-progress
        model_file = tmp_path / "train_model.py"
        model_file.write_text("from sklearn.ensemble import RandomForestClassifier\n")

        _, stderr, _ = run_lint(str(model_file))
        assert "scope-guard" in stderr.lower() or "H4" in stderr

    def test_no_warning_for_in_scope_write(self, tmp_path):
        eds_dir = tmp_path / ".eds"
        eds_dir.mkdir()
        brief = eds_dir / "BRIEF.md"
        brief.write_text(
            "# Problem Brief\n\n## Status\nconfirmed\n\n## Plan\n"
            "- eda · eda-workflow · in-progress\n"
        )

        # Write to an EDA notebook while EDA is in-progress
        eda_file = tmp_path / "eda_analysis.py"
        eda_file.write_text("import pandas as pd\ndf.describe()\n")

        _, stderr, _ = run_lint(str(eda_file))
        assert "H4" not in stderr
