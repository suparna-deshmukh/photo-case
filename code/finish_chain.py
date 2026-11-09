"""Autonomous finish chain: wait for celebrity fetch -> data pipeline ->
server restart -> full test suite -> QA screenshots. All logged."""
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
PY = str(BASE / ".venv" / "bin" / "python")
LOG = BASE / "logs" / "finish_chain.log"


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def wait_fetch(timeout_s=6 * 3600):
    log("waiting for celebrity fetch (logs/celeb_final4.log FINAL DONE)…")
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        try:
            tail = (BASE / "logs" / "celeb_final4.log").read_text()[-4000:]
        except FileNotFoundError:
            tail = ""
        if "FINAL DONE" in tail:
            log("celebrity fetch done")
            return
        if not subprocess.run(["pgrep", "-f", "fetch_celebs_final.py"],
                              capture_output=True).stdout.strip():
            log("WARN: fetch process gone without FINAL DONE marker")
            return
        time.sleep(60)
    log("WARN: fetch wait timed out")


def run(step, cmd, cwd=None):
    log(f"STEP {step}: {' '.join(cmd)}")
    t0 = time.time()
    with open(LOG, "a") as lf:
        lf.write(f"\n=== [{time.strftime('%H:%M:%S')}] {step} ===\n$ {' '.join(cmd)}\n")
        p = subprocess.run(cmd, stdout=lf, stderr=subprocess.STDOUT,
                           cwd=str(cwd or BASE))
    log(f"STEP {step}: rc={p.returncode} after {(time.time()-t0)/60:.1f} min")
    return p.returncode


def restart_jog():
    log("restarting jog server :8502")
    subprocess.run(["pkill", "-f", "streamlit run app.py --server.headless true --server.port 8502"],
                   capture_output=True)
    time.sleep(5)
    env = dict(os.environ)
    for line in (BASE / ".env").read_text().splitlines():
        if line.strip() and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    logf = open(BASE / "logs" / "streamlit_jog_8502_final.log", "a")
    proc = subprocess.Popen(
        [PY, "-m", "streamlit", "run", "app.py",
         "--server.headless", "true", "--server.port", "8502",
         "--server.fileWatcherType", "none"],
        cwd=str(BASE / "space_jog"), env=env,
        stdout=logf, stderr=subprocess.STDOUT, start_new_session=True)
    time.sleep(25)
    import urllib.request
    ok = False
    for _ in range(12):
        try:
            code = urllib.request.urlopen("http://localhost:8502", timeout=5).status
            if code == 200:
                ok = True
                break
        except Exception:
            pass
        time.sleep(5)
    log(f"jog server restarted: pid={proc.pid} up={ok}")
    return ok


def main():
    wait_fetch()
    if run("pipeline", [PY, "code/celebrity_chain.py"]) != 0:
        log("CHAIN ABORTED: pipeline failed (see logs/celebrity_chain.log)")
        return
    if not restart_jog():
        log("CHAIN ABORTED: server did not come up")
        return
    time.sleep(20)
    run("people_qa", [PY, "code/test_jog_people.py"])
    run("repro", [PY, "code/repro_jog_widget.py"])
    run("m7", [PY, "code/test_jog_app.py"])
    run("classic", [PY, "code/test_jog_app.py", "--classic"])
    run("testmode", [PY, "code/test_jog_testmode.py"])
    run("verify_final", [PY, "code/verify_library.py"])
    log("FINISH CHAIN COMPLETE")


if __name__ == "__main__":
    main()
