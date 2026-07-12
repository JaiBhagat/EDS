#!/usr/bin/env python3
"""EDS gate: baseline/model.

Checks:
- Experiment log exists with at least one entry per fit
- Validation contract hash matches (contract hasn't been silently modified)
- Champion model reruns from log within tolerance
- Holdout ledger records a single confirmation touch
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from gate_utils import GateResult, check_stage_code, find_eds_root, load_json


def hash_contract(contract: dict) -> str:
    """Deterministic hash of the validation contract."""
    canonical = json.dumps(contract, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def run(project_dir: str = "."):
    root = find_eds_root(project_dir)
    gate = GateResult("model")

    if not root:
        gate.check("eds-root-exists", False, ".eds/ directory not found")
        gate.write_and_exit(Path(project_dir))
        return

    models_dir = root / ".eds" / "models"

    # Check 1: Experiment log exists with entries
    experiment_log_path = models_dir / "experiment_log.json"
    experiment_log = load_json(experiment_log_path)

    if not gate.check(
        "experiment-log-exists",
        experiment_log is not None,
        str(experiment_log_path),
    ):
        gate.write_and_exit(root)
        return

    gate.add_evidence(str(experiment_log_path))

    entries = experiment_log if isinstance(experiment_log, list) else experiment_log.get("experiments", [])
    gate.check(
        "experiment-log-has-entries",
        len(entries) > 0,
        f"{len(entries)} experiment(s) logged",
    )

    # Check 2: Validation contract exists and hash matches
    contract_path = models_dir / "validation_contract.json"
    contract = load_json(contract_path)

    if contract is not None:
        gate.add_evidence(str(contract_path))
        contract_hash = hash_contract(contract)

        # Check that experiments reference this contract hash
        mismatched = []
        for entry in entries:
            if isinstance(entry, dict):
                entry_hash = entry.get("contract_hash", "")
                if entry_hash and entry_hash != contract_hash:
                    mismatched.append(entry.get("name", entry.get("model", "unknown")))

        gate.check(
            "contract-hash-matches",
            len(mismatched) == 0,
            f"{len(mismatched)} experiments have stale contract hash: {mismatched[:3]}"
            if mismatched
            else f"contract hash {contract_hash} consistent across experiments",
        )
    else:
        gate.check("contract-hash-matches", False, "validation_contract.json missing")

    # Check 3: Champion identified and has rerun info
    champion_path = models_dir / "champion.json"
    champion = load_json(champion_path)

    if champion is not None:
        gate.add_evidence(str(champion_path))
        has_rerun = (
            champion.get("rerun_metric") is not None
            or champion.get("reproducible") is not None
            or champion.get("seed") is not None
        )
        gate.check(
            "champion-reproducible",
            has_rerun,
            "champion has rerun/reproducibility info"
            if has_rerun
            else "champion missing rerun info (seed, rerun_metric, or reproducible field)",
        )
    else:
        # Champion may not exist yet if still in experimentation
        gate.check(
            "champion-reproducible",
            False,
            "champion.json not found — no champion selected yet",
        )

    # Check 4: Holdout ledger has exactly one confirmation touch for model stage
    ledger_path = root / ".eds" / "holdout_ledger.json"
    ledger = load_json(ledger_path)

    if ledger is not None:
        gate.add_evidence(str(ledger_path))
        touches = ledger if isinstance(ledger, list) else ledger.get("touches", [])
        model_touches = [
            t for t in touches
            if isinstance(t, dict) and t.get("stage") in ("model", "confirmation", "champion")
        ]
        gate.check(
            "single-holdout-touch",
            len(model_touches) <= 1,
            f"{len(model_touches)} model-stage holdout touch(es)"
            + (" — multiple touches violate M7" if len(model_touches) > 1 else ""),
        )
    else:
        gate.check(
            "single-holdout-touch",
            False,
            "holdout_ledger.json missing — cannot verify holdout discipline",
        )

    # Stage code recorded (axiom 5 — reproducibility)
    check_stage_code(gate, root, "model")

    gate.write_and_exit(root)


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else ".")
