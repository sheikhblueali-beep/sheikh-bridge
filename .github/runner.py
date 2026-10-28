import os, json, time, uuid, subprocess, sys, traceback
from pathlib import Path
import requests

TOKEN = os.environ["TG_TOKEN"]
API = f"https://api.telegram.org/bot{TOKEN}"
ROOT = Path(".").resolve()
QUEUE = ROOT / "queue"
RESULTS = ROOT / "results"
UPDATES = ROOT / "updates"
STATE = ROOT / "state.json"
MAX_RUNTIME = 5.7 * 3600  # 5h42m, less than 6h job limit

def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, cwd=ROOT)

def git_pull():
    git("fetch", "origin", "main")
    git("reset", "--hard", "origin/main")

def git_push(msg):
    git("add", "-A")
    git("commit", "-m", msg)
    git("push", "origin", "HEAD:main")
def load_state():
    if STATE.exists():
        try: return json.loads(STATE.read_text())
        except: pass
    return {"offset": 0}

def save_state(s):
    STATE.write_text(json.dumps(s))

def call_telegram(method, params=None):
    url = f"{API}/{method}"
    try:
        r = requests.post(url, json=params or {}, timeout=15)
        return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}

def process_queue():
    jobs = sorted(QUEUE.glob("*.json"))
    for job_file in jobs:
        try:
            job = json.loads(job_file.read_text())
        except Exception:
            job_file.unlink(missing_ok=True)
            continue
        job_id = job["id"]
        method = job["method"]
        params = job.get("params", {})
        print(f"[job] {job_id} → {method}")
        result = call_telegram(method, params)
        (RESULTS / f"{job_id}.json").write_text(json.dumps(result))
        job_file.unlink(missing_ok=True)

def poll_updates(state):
    res = call_telegram("getUpdates", {"offset": state["offset"], "timeout": 2})
    if not res.get("ok"):
        return
    updates = res.get("result", [])
    if not updates:
        return
    ts = int(time.time())
    for u in updates:
        (UPDATES / f"{ts}_{u['update_id']}.json").write_text(json.dumps(u))
        state["offset"] = u["update_id"] + 1
    save_state(state)
    print(f"[poll] {len(updates)} updates")

def main():
    start = time.time()
    state = load_state()
    last_pull = 0
    last_push = 0
    while time.time() - start < MAX_RUNTIME:
        try:
            now = time.time()
            if now - last_pull > 2:
                git_pull()
                last_pull = now
            process_queue()
            poll_updates(state)
            now = time.time()
            if now - last_push > 5:
                if any(QUEUE.glob("*.json")) is False and any(RESULTS.glob("*.json")) or any(UPDATES.glob("*.json")):
                    pass  # cleanup handled below
                if list(RESULTS.glob("*.json")) or list(UPDATES.glob("*.json")):
                    # push results and updates
                    git_push(f"bridge: push @ {int(time.time())}")
                    # optionally clean results older than 1h
                    cutoff = time.time() - 3600
                    for f in RESULTS.glob("*.json"):
                        if f.stat().st_mtime < cutoff:
                            f.unlink()
                    for f in UPDATES.glob("*.json"):
                        if f.stat().st_mtime < cutoff:
                            f.unlink()
                last_push = now
            time.sleep(1)
        except Exception:
            traceback.print_exc()
            time.sleep(3)
    print("[runner] max runtime reached, exiting")

if __name__ == "__main__":
    main()
