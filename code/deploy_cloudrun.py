"""M10/D11 fallback - deploy the Streamlit apps to Google Cloud Run (used when HF
dynamic spaces are unavailable). Requires a valid interactive `gcloud auth login`
by the user (all stored credentials on this machine are expired).
Usage: .venv/bin/python code/deploy_cloudrun.py [--only discovery|jog]
"""
import argparse
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "code"))
from deploy_space import load_env  # noqa: E402

PROJECT = "prior-auth-portal-dev"
REGION = "us-central1"
APPS = {
    "discovery": ("space_discovery", "photo-retrieval-discovery-app"),
    "jog": ("space_jog", "jog-memory-retrieval-app"),
}


def run(cmd, input_bytes=None):
    print("$", " ".join(cmd[:7]), "...", flush=True)
    return subprocess.run(cmd, input=input_bytes, capture_output=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=list(APPS))
    args = ap.parse_args()

    r = run(["gcloud", "auth", "list", "--quiet"])
    ok = r.returncode == 0 and b"ACTIVE" in (r.stdout or b"")
    if not ok:
        print("BLOCKED: no valid gcloud credentials. Run interactively:  gcloud auth login")
        print("then re-run this script. (Service-account keys in ~/.config/gcloud are stale - 'account not found'.)")
        return 1

    r = run(["gcloud", "services", "enable", "run.googleapis.com", "cloudbuild.googleapis.com",
             "secretmanager.googleapis.com", "--project", PROJECT, "--quiet"])
    print(("apis enabled" if r.returncode == 0 else "WARN: api enable failed (may already be enabled): "
           + (r.stderr.decode() or "")[:200]))

    env = load_env()
    secrets = {k: env[k] for k in ("LIVE_LLM_BASE_URL", "LIVE_LLM_API_KEY", "LIVE_LLM_MODEL") if env.get(k)}
    secret_ids = {}
    for k, v in secrets.items():
        sid = "live-llm-" + k.lower().replace("_", "-")
        r = run(["gcloud", "secrets", "describe", sid, "--project", PROJECT, "--quiet"])
        if r.returncode != 0:
            r = run(["gcloud", "secrets", "create", sid, "--project", PROJECT, "--quiet"],
                    input_bytes=v.encode())
            if r.returncode != 0:
                print(f"WARN: could not create secret {sid}: {(r.stderr.decode() or '')[:200]}")
                continue
        secret_ids[k] = sid
    print(f"secrets ready: {sorted(secret_ids)} (values never printed)")

    targets = [args.only] if args.only else list(APPS)
    rc = 0
    for name in targets:
        folder, svc = APPS[name]
        cmd = ["gcloud", "run", "deploy", svc, "--project", PROJECT, "--region", REGION,
               "--source", str(BASE / folder), "--allow-unauthenticated", "--memory", "2Gi",
               "--cpu", "2", "--max-instances", "2", "--start-period", "300", "--quiet"]
        if secret_ids:
            cmd += ["--set-secrets", ",".join(f"{k}={s}:latest" for k, s in secret_ids.items())]
        r = run(cmd)
        if r.returncode == 0:
            out = (r.stdout.decode() or "").strip().splitlines()
            print(f"DEPLOYED {name}: {out[-1] if out else svc}")
        else:
            rc = 1
            print(f"FAILED {name}: {(r.stderr.decode() or '')[:500]}")
            print("tip: if the Cloud Build step times out, re-run (build is resumable) or split torch install.")
    return rc


if __name__ == "__main__":
    sys.exit(main())
