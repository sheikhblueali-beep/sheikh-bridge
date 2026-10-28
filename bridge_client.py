import os, json, uuid, subprocess, time, asyncio
from pathlib import Path

class GitBridge:
    def __init__(self, repo_path, timeout=120):
        self.repo_path = Path(repo_path)
        self.queue = self.repo_path / "queue"
        self.results = self.repo_path / "results"
        self.timeout = timeout
        self.lock = asyncio.Lock()

    def _git(self, *args):
        return subprocess.run(["git", *args], cwd=self.repo_path, capture_output=True, text=True)

    async def call(self, method, params):
        async with self.lock:
            job_id = str(uuid.uuid4())
            job_file = self.queue / f"{job_id}.json"
            
            job = {"id": job_id, "method": method, "params": params}
            job_file.write_text(json.dumps(job))
            
            await asyncio.to_thread(self._git, "add", "-A")
            await asyncio.to_thread(self._git, "commit", "-m", f"job {job_id}")
            await asyncio.to_thread(self._git, "push", "origin", "HEAD:main")
            
            result_file = self.results / f"{job_id}.json"
            start = time.time()
            while time.time() - start < self.timeout:
                await asyncio.sleep(1)
                await asyncio.to_thread(self._git, "pull", "--rebase")
                if result_file.exists():
                    try:
                        res = json.loads(result_file.read_text())
                        return res
                    except Exception:
                        pass
            raise TimeoutError(f"Job {job_id} timed out after {self.timeout}s")
