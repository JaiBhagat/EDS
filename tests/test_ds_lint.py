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


class TestJoinNoAssert:
    def test_comment_assert_does_not_satisfy(self, tmp_path):
        """P1.5: 'assert' inside a comment should NOT satisfy the join check."""
        bait = tmp_path / "bait.py"
        bait.write_text(
            "import pandas as pd\n"
            "df = left.merge(right, on='id')\n"
            "# unasserted join — this comment mentions assert but isn't one\n"
            "print(df.head())\n"
        )
        _, stderr, _ = run_lint(str(bait))
        assert "join" in stderr.lower()

    def test_real_assert_satisfies(self, tmp_path):
        bait = tmp_path / "bait.py"
        bait.write_text(
            "import pandas as pd\n"
            "df = left.merge(right, on='id')\n"
            "assert len(df) == len(left)\n"
        )
        _, stderr, _ = run_lint(str(bait))
        assert "join" not in stderr.lower()


class TestStageDrift:
    def test_stages_json_matches_gate_scripts(self):
        """stages.json gate entries must correspond to actual gate scripts or 'user-signoff'."""
        stages_path = os.path.join(os.path.dirname(__file__), "..", "scripts", "lib", "stages.json")
        gates_dir = os.path.join(os.path.dirname(__file__), "..", "scripts", "gates")
        with open(stages_path) as f:
            import json as _json
            stages = _json.load(f)["stages"]

        for s in stages:
            gate = s["gate"]
            if gate == "user-signoff":
                continue
            gate_path = os.path.join(gates_dir, gate)
            assert os.path.exists(gate_path), f"stages.json references gate '{gate}' but {gate_path} does not exist"

    def test_stages_json_ids_unique(self):
        stages_path = os.path.join(os.path.dirname(__file__), "..", "scripts", "lib", "stages.json")
        with open(stages_path) as f:
            import json as _json
            stages = _json.load(f)["stages"]
        ids = [s["id"] for s in stages]
        assert len(ids) == len(set(ids)), f"duplicate stage IDs: {[x for x in ids if ids.count(x) > 1]}"


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
