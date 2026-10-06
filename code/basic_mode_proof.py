"""
Purpose: D11 BASIC-MODE PROOF - remove the three LIVE_LLM_* Space secrets,
         restart the Space, run the browser test (app must work with ZERO LLM),
         restore the secrets, restart, and re-test (AI mode badge returns).
Inputs : BASE/.env (HF_TOKEN + LIVE_LLM_*), the deployed Space.
Outputs: logs/basic_mode_proof.log; screenshots in figures/screens/discovery_basic_proof/
         and figures/screens/discovery_ai_restored/; printed PASS/FAIL per phase.
Safety: secret values are never printed.
Usage  : .venv/bin/python code/basic_mode_proof.py [--name photo-retrieval-discovery] [--wait-min 25]
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
LOG = BASE / "logs" / "basic_mode_proof.log"
SECRET_KEYS = ["LIVE_LLM_BASE_URL", "LIVE_LLM_API_KEY", "LIVE_LLM_MODEL"]


def log(msg):
    line = time.strftime("%Y-%m-%dT%H:%M:%S%z") + " " + msg
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def load_env():
    env = {}
    for line in (BASE / ".env").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def wait_running(api, space_id, wait_min):
    t0 = time.time()
    while time.time() - t0 < wait_min * 60:
        try:
            rt = api.get_space_runtime(space_id)
            st = str(getattr(rt, "status", ""))
            log(f"  runtime: {st}")
            if st == "RUNNING":
                return True
            if st in ("FAILED", "ERROR"):
                return False
        except Exception as e:
            log(f"  poll error: {type(e).__name__}: {str(e)[:200]}")
        time.sleep(20)
    return False


def run_browser_test(url, outdir):
    outdir.mkdir(parents=True, exist_ok=True)
    cmd = [str(BASE / ".venv/bin/python"), str(BASE / "code/test_discovery_app.py"),
           "--url", url, "--out", str(outdir)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1200)
    tail = "\n".join(r.stdout.strip().splitlines()[-8:])
    log("browser test output:\n" + tail)
    return r.returncode == 0, tail


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="photo-retrieval-discovery")
    ap.add_argument("--wait-min", type=int, default=25)
    args = ap.parse_args()

    env = load_env()
    from huggingface_hub import HfApi
    api = HfApi(token=env["HF_TOKEN"])
    user = api.whoami()["name"]
    space_id = f"{user}/{args.name}"
    url = f"https://{user}--{args.name}.hf.space"
    log(f"START basic-mode proof for {space_id} ({url})")

    # PHASE 1: delete secrets, restart, test basic mode
    log("PHASE 1: deleting LIVE_LLM_* secrets")
    for k in SECRET_KEYS:
        try:
            api.delete_space_secret(space_id, k)
            log(f"  deleted {k}")
        except Exception as e:
            log(f"  {k}: {type(e).__name__} (may not exist - ok)")
    api.restart_space(space_id)
    log("  restarted space")
    ok = wait_running(api, space_id, args.wait_min)
    log(f"  phase1 runtime ready: {ok}")
    basic_ok, tail1 = run_browser_test(url, BASE / "figures" / "screens" / "discovery_basic_proof")
    log(f"PHASE 1 browser test (basic mode): {'PASS' if basic_ok else 'FAIL'}")

    # PHASE 2: restore secrets, restart, retest (AI badge back)
    log("PHASE 2: restoring secrets")
    for k in SECRET_KEYS:
        if env.get(k):
            api.add_space_secret(space_id, k, env[k])
            log(f"  restored {k}")
    api.restart_space(space_id)
    log("  restarted space")
    ok = wait_running(api, space_id, args.wait_min)
    log(f"  phase2 runtime ready: {ok}")
    ai_ok, tail2 = run_browser_test(url, BASE / "figures" / "screens" / "discovery_ai_restored")
    log(f"PHASE 2 browser test (AI mode): {'PASS' if ai_ok else 'FAIL'}")

    log(f"RESULT: basic_mode={'PASS' if basic_ok else 'FAIL'}, ai_restored={'PASS' if ai_ok else 'FAIL'}")
    return 0 if (basic_ok and ai_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
