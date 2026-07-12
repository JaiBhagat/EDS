#!/usr/bin/env python3
"""Model handoff — serialize champion model into a loadable bundle.

Usage:
    python bundle_model.py \
        --model-path fitted_model.joblib \
        --champion-path .eds/models/champion.json \
        --contract-path .eds/models/validation_contract.json \
        [--calibrator-path calibrator.joblib] \
        [--features-path .eds/features/feature_spec.json] \
        [--threshold-path .eds/models/threshold.json] \
        [--metrics-path .eds/models/bootstrap_ci.json] \
        [--out-dir .eds/models/bundle/]
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def sha256_file(path: str) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def get_package_versions() -> dict:
    """Get versions of key ML packages."""
    versions = {}
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "freeze"],
            capture_output=True, text=True, timeout=30
        )
        key_packages = {
            "scikit-learn", "numpy", "pandas", "joblib",
            "xgboost", "lightgbm", "scipy",
        }
        for line in result.stdout.strip().split("\n"):
            if "==" in line:
                pkg, ver = line.split("==", 1)
                if pkg.lower().replace("-", "_") in {p.replace("-", "_") for p in key_packages}:
                    versions[pkg] = ver
    except (subprocess.TimeoutExpired, FileNotFoundError):
        versions["error"] = "pip freeze failed"
    return versions


def generate_inference_py(out_dir: str, feature_spec: dict | None,
                          has_calibrator: bool, threshold: dict | None) -> str:
    """Generate inference.py that loads and scores with the bundle."""
    features_import = ""
    feature_transform = ""

    if feature_spec and feature_spec.get("feature_names"):
        feature_names = feature_spec["feature_names"]
        feature_transform = f"""
    # Select and order features
    feature_names = {feature_names}
    missing = set(feature_names) - set(df.columns)
    if missing:
        raise ValueError(f"Missing features: {{missing}}")
    X = df[feature_names]
"""
    else:
        feature_transform = """
    # Load feature spec
    spec_path = Path(bundle_dir) / "feature_spec.json"
    if spec_path.exists():
        with open(spec_path) as f:
            spec = json.load(f)
        feature_names = spec.get("feature_names", list(df.columns))
        X = df[feature_names]
    else:
        X = df
"""

    # Check if features.py exists for engineered features
    features_py_section = """
    # Apply feature engineering if features.py exists
    features_py = Path(bundle_dir).parent.parent.parent / "features.py"
    if features_py.exists():
        import importlib.util
        spec_mod = importlib.util.spec_from_file_location("features", features_py)
        features_mod = importlib.util.module_from_spec(spec_mod)
        spec_mod.loader.exec_module(features_mod)
        if hasattr(features_mod, "build_features"):
            df = features_mod.build_features(df)
"""

    calibration_section = ""
    if has_calibrator:
        calibration_section = """
    # Apply calibration
    calibrator_path = Path(bundle_dir) / "calibrator.joblib"
    if calibrator_path.exists():
        calibrator = joblib.load(calibrator_path)
        if hasattr(calibrator, "predict"):
            scores = calibrator.predict(scores)
        elif hasattr(calibrator, "predict_proba"):
            scores = calibrator.predict_proba(scores.reshape(-1, 1))[:, 1]
"""

    threshold_section = ""
    if threshold:
        default_threshold = threshold.get("operating_threshold", 0.5)
        threshold_section = f"""
    # Apply threshold
    threshold_path = Path(bundle_dir) / "threshold.json"
    if threshold_path.exists():
        with open(threshold_path) as f:
            thresh_config = json.load(f)
        threshold_val = thresh_config.get("operating_threshold", {default_threshold})
    else:
        threshold_val = {default_threshold}
    return pd.Series((scores >= threshold_val).astype(int), index=df.index)
"""
    else:
        threshold_section = """
    # Apply default threshold
    threshold_path = Path(bundle_dir) / "threshold.json"
    if threshold_path.exists():
        with open(threshold_path) as f:
            thresh_config = json.load(f)
        threshold_val = thresh_config.get("operating_threshold", 0.5)
    else:
        threshold_val = 0.5
    return pd.Series((scores >= threshold_val).astype(int), index=df.index)
"""

    code = f'''#!/usr/bin/env python3
"""Auto-generated inference script for the model bundle.

Load the bundle and score raw DataFrames end-to-end:
    raw df -> feature engineering -> model scoring -> calibration -> threshold

Generated: {datetime.now(timezone.utc).isoformat()}
"""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd


def load_bundle(bundle_dir: str = ".eds/models/bundle/") -> dict:
    """Load all bundle components."""
    bundle_dir = Path(bundle_dir)
    bundle = {{"model": joblib.load(bundle_dir / "model.joblib")}}

    calibrator_path = bundle_dir / "calibrator.joblib"
    if calibrator_path.exists():
        bundle["calibrator"] = joblib.load(calibrator_path)

    spec_path = bundle_dir / "feature_spec.json"
    if spec_path.exists():
        with open(spec_path) as f:
            bundle["feature_spec"] = json.load(f)

    threshold_path = bundle_dir / "threshold.json"
    if threshold_path.exists():
        with open(threshold_path) as f:
            bundle["threshold"] = json.load(f)

    return bundle


def score(df: pd.DataFrame, bundle_dir: str = ".eds/models/bundle/") -> pd.Series:
    """Raw DataFrame -> calibrated probability scores."""
    bundle_dir = Path(bundle_dir)
{features_py_section}
{feature_transform}
    # Score with model
    model = joblib.load(bundle_dir / "model.joblib")
    if hasattr(model, "predict_proba"):
        scores = model.predict_proba(X)[:, 1]
    else:
        scores = model.predict(X)
{calibration_section}
    return pd.Series(scores, index=df.index)


def predict(df: pd.DataFrame, bundle_dir: str = ".eds/models/bundle/") -> pd.Series:
    """Raw DataFrame -> binary predictions at the operating threshold."""
    scores = score(df, bundle_dir).values
{threshold_section}


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python inference.py <input.csv> [--bundle-dir .eds/models/bundle/]")
        sys.exit(1)
    input_path = sys.argv[1]
    bundle_dir = sys.argv[3] if len(sys.argv) > 3 and sys.argv[2] == "--bundle-dir" else ".eds/models/bundle/"
    df = pd.read_csv(input_path)
    result = score(df, bundle_dir)
    print(f"Scored {{len(result)}} rows. Mean score: {{result.mean():.4f}}")
'''
    return code


def main():
    ap = argparse.ArgumentParser(description="Bundle a champion model for handoff")
    ap.add_argument("--model-path", required=True,
                    help="Path to fitted model (.joblib or .pkl)")
    ap.add_argument("--champion-path", default=".eds/models/champion.json")
    ap.add_argument("--contract-path", default=".eds/models/validation_contract.json")
    ap.add_argument("--calibrator-path", default=None,
                    help="Path to fitted calibrator (.joblib)")
    ap.add_argument("--features-path", default=None,
                    help="Path to feature_spec.json")
    ap.add_argument("--threshold-path", default=None,
                    help="Path to threshold.json")
    ap.add_argument("--metrics-path", default=None,
                    help="Path to bootstrap_ci.json or metrics file")
    ap.add_argument("--out-dir", default=".eds/models/bundle/")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Validate prerequisites
    if not os.path.exists(args.model_path):
        print(f"FAILED: model not found at {args.model_path}", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(args.champion_path):
        print(f"FAILED: champion.json not found at {args.champion_path}", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(args.contract_path):
        print(f"FAILED: validation_contract.json not found at {args.contract_path}", file=sys.stderr)
        sys.exit(1)

    import shutil

    # 1. Copy model
    model_dest = out_dir / "model.joblib"
    shutil.copy2(args.model_path, model_dest)
    print(f"  model.joblib: copied from {args.model_path}")

    # 2. Copy calibrator (or create placeholder)
    has_calibrator = False
    if args.calibrator_path and os.path.exists(args.calibrator_path):
        shutil.copy2(args.calibrator_path, out_dir / "calibrator.joblib")
        has_calibrator = True
        print(f"  calibrator.joblib: copied from {args.calibrator_path}")

    # 3. Feature spec
    feature_spec = None
    if args.features_path and os.path.exists(args.features_path):
        shutil.copy2(args.features_path, out_dir / "feature_spec.json")
        with open(args.features_path) as f:
            feature_spec = json.load(f)
        print(f"  feature_spec.json: copied from {args.features_path}")
    else:
        # Create minimal spec from champion info
        with open(args.champion_path) as f:
            champion = json.load(f)
        feature_spec = {
            "feature_names": champion.get("feature_set", []),
            "source": "champion.json",
        }
        with open(out_dir / "feature_spec.json", "w") as f:
            json.dump(feature_spec, f, indent=2)
        print("  feature_spec.json: generated from champion.json")

    # 4. Threshold
    threshold = None
    if args.threshold_path and os.path.exists(args.threshold_path):
        shutil.copy2(args.threshold_path, out_dir / "threshold.json")
        with open(args.threshold_path) as f:
            threshold = json.load(f)
        print(f"  threshold.json: copied from {args.threshold_path}")

    # 5. Metrics
    if args.metrics_path and os.path.exists(args.metrics_path):
        shutil.copy2(args.metrics_path, out_dir / "metrics.json")
        print(f"  metrics.json: copied from {args.metrics_path}")

    # 6. Generate inference.py
    inference_code = generate_inference_py(
        str(out_dir), feature_spec, has_calibrator, threshold
    )
    inference_path = out_dir / "inference.py"
    with open(inference_path, "w") as f:
        f.write(inference_code)
    print("  inference.py: generated")

    # 7. Build MANIFEST
    with open(args.contract_path) as f:
        contract = json.load(f)

    manifest_files = {}
    for p in out_dir.iterdir():
        if p.name != "MANIFEST.json" and p.is_file():
            manifest_files[p.name] = sha256_file(str(p))

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "files": manifest_files,
        "contract_hash": contract.get("hash", "unknown"),
        "seed": contract.get("seed"),
        "packages": get_package_versions(),
    }
    with open(out_dir / "MANIFEST.json", "w") as f:
        json.dump(manifest, f, indent=2)
    print("  MANIFEST.json: generated")

    manifest_hash = sha256_file(str(out_dir / "MANIFEST.json"))
    print(f"\nBundle complete: {out_dir}")
    print(f"MANIFEST hash: {manifest_hash}")
    print("Record this hash in the Brief's Plan row as evidence.")


if __name__ == "__main__":
    main()
