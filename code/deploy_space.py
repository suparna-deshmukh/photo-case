"""
Purpose: D11 (shared with M10) - deploy a Hugging Face Space (Streamlit) from a
         local folder using huggingface_hub. Creates the Space if missing
         (public, sdk streamlit), uploads the folder, sets LIVE_LLM_* secrets.
Inputs : folder (default BASE/space_discovery), name (default photo-retrieval-
         discovery; -lab suffix fallback), BASE/.env (HF_TOKEN, LIVE_LLM_*).
Outputs: running public Space; printed URL; never prints secrets.
Usage  : .venv/bin/python code/deploy_space.py [--folder path] [--name name]
"""
import argparse
import os
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "code"))


def load_env():
    env = {}
    p = BASE / ".env"
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--folder", default=str(BASE / "space_discovery"))
    ap.add_argument("--name", default="photo-retrieval-discovery")
    ap.add_argument("--sync-data", action="store_true",
                    help="replace <folder>/data with BASE/data/app (discovery bundle only)")
    args = ap.parse_args()

    env = load_env()
    hf_token = env.get("HF_TOKEN") or os.environ.get("HF_TOKEN")
    if not hf_token:
        print("BLOCKED: HF_TOKEN empty in .env")
        return
    folder = Path(args.folder)
    if not (folder / "app.py").exists():
        print(f"BLOCKED: no app.py in {folder}")
        return
    # sync data bundle (discovery app only; jog ships its own data/)
    if args.sync_data:
        import shutil
        datadir = folder / "data"
        src = BASE / "data" / "app"
        if not src.exists():
            print(f"BLOCKED: --sync-data but {src} missing")
            return
        if datadir.exists():
            shutil.rmtree(datadir)
        shutil.copytree(src, datadir)
        print(f"synced {src} -> {datadir}")

    from huggingface_hub import HfApi, upload_folder, get_space_runtime
    from huggingface_hub.errors import RepositoryNotFoundError
    api = HfApi(token=hf_token)
    try:
        info = api.whoami()
        user = info.get("name")
    except Exception as e:
        print(f"BLOCKED: whoami failed: {type(e).__name__}: {str(e)[:300]}")
        return
    print(f"HF user: {user}")

    space_id = f"{user}/{args.name}"
    try:
        api.create_repo(repo_id=space_id, repo_type="space", exist_ok=True,
                        private=False, space_sdk="docker")
        print(f"ensured space {space_id}")
    except Exception as e:
        msg = str(e)
        if "409" in msg or "exists" in msg.lower():
            alt = f"{user}/{args.name}-lab"
            print(f"{space_id} unusable; trying {alt}")
            try:
                api.create_repo(repo_id=alt, repo_type="space", exist_ok=True,
                                private=False, space_sdk="docker")
                space_id = alt
                print(f"ensured space {alt}")
            except Exception as e2:
                if "409" in str(e2) or "exists" in str(e2).lower():
                    print(f"{alt} also exists - using it")
                    space_id = alt
                else:
                    print(f"BLOCKED: create failed: {type(e2).__name__}: {str(e2)[:300]}")
                    return
        else:
            print(f"BLOCKED: create failed: {type(e).__name__}: {msg[:300]}")
            return

    print(f"uploading {folder} ...")
    try:
        upload_folder(folder_path=str(folder), repo_id=space_id, repo_type="space",
                      ignore_patterns=[".git", ".DS_Store", "*.pyc", "__pycache__"])
        print("upload done")
    except Exception as e:
        print(f"BLOCKED: upload failed: {type(e).__name__}: {str(e)[:300]}")
        return

    # secrets: only the three LIVE_LLM_* names
    secrets = {k: env[k] for k in ("LIVE_LLM_BASE_URL", "LIVE_LLM_API_KEY", "LIVE_LLM_MODEL") if env.get(k)}
    if secrets:
        try:
            for k, v in secrets.items():
                api.add_space_secret(space_id=space_id, key=k, value=v, repo_type="space")
            print(f"set {len(secrets)} secrets (values never printed)")
        except Exception as e:
            print(f"WARNING setting secrets: {type(e).__name__}: {str(e)[:300]} (retry via Space UI if needed)")
    else:
        print("hosted layer skipped (no LIVE_LLM_* in .env)")

    # canonical URL from runtime
    url = f"https://{space_id.replace('/', '--')}.hf.space"
    try:
        import requests
        info = requests.get(f"https://huggingface.co/api/spaces/{space_id}", timeout=15).json()
        if info.get("host"):
            url = info["host"]
    except Exception:
        pass
    print(f"waiting for runtime of {space_id} (up to ~40 min) ...")
    last = None
    for i in range(160):
        try:
            rt = get_space_runtime(space_id)
            last = rt
            st_ = str(getattr(rt, "stage", "") or getattr(rt, "status", ""))
            print(f"  runtime[{i}]: {st_}")
            if st_ == "RUNNING":
                break
            if st_ == "FAILED":
                print(f"FAILED: space runtime FAILED; fetch build logs via API")
                break
            if st_ == "SLEEPING":
                try:
                    import requests
                    requests.get(url, timeout=30)
                    print("  (sent wake GET)")
                except Exception:
                    pass
        except Exception as e:
            print(f"  poll: {type(e).__name__}: {str(e)[:200]}")
        time.sleep(15)
    print(f"SPACE_URL: {url}")
    if last is not None:
        print(f"FINAL_RUNTIME: {str(getattr(last, 'status', 'unknown'))}")


if __name__ == "__main__":
    main()
