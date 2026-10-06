"""Chain after celebrity fetch: tag -> meta -> embed -> faces -> sync -> verify."""
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
PY = str(BASE / ".venv" / "bin" / "python")
LOG = BASE / "logs" / "celebrity_chain.log"


def run(step, cmd):
    print(f"\n=== {step}: {' '.join(cmd)} ===", flush=True)
    t0 = time.time()
    with open(LOG, "a") as lf:
        lf.write(f"\n=== [{time.strftime('%H:%M:%S')}] {step} ===\n$ {' '.join(cmd)}\n")
        p = subprocess.run(cmd, stdout=lf, stderr=subprocess.STDOUT, cwd=str(BASE))
    rc = p.returncode
    print(f"=== {step}: rc={rc} after {(time.time()-t0)/60:.1f} min ===", flush=True)
    if rc != 0:
        print(f"FAILED: {step} (rc={rc}) — stopping chain", flush=True)
        sys.exit(1)


def main():
    run("tag_images", [PY, "code/tag_images.py", "--provider", "local", "--resume", "--workers", "8"])
    run("build_meta", [PY, "code/build_meta.py"])
    run("embed_images", [PY, "code/embed_images.py"])
    run("face_pipeline", [PY, "code/face_pipeline.py", "--resume"])
    run("sync_space_jog", [PY, "code/sync_space_jog.py"])
    run("verify", [PY, "code/verify_library.py"])
    print("CELEBRITY CHAIN COMPLETE", flush=True)


if __name__ == "__main__":
    main()
