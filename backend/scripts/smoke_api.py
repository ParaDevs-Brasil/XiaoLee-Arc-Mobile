from __future__ import annotations

import json
import subprocess
import time
import urllib.request
from pathlib import Path


def main() -> int:
    log_path = Path("/tmp/xiaolee-smoke-api.log")
    with log_path.open("w", encoding="utf-8") as log_file:
        process = subprocess.Popen(
            [
                "../.venv/bin/python",
                "-m",
                "uvicorn",
                "server.app:app",
                "--host",
                "127.0.0.1",
                "--port",
                "18000",
            ],
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )

        try:
            status_payload = None
            deadline = time.time() + 30
            while time.time() < deadline:
                try:
                    with urllib.request.urlopen("http://127.0.0.1:18000/status", timeout=1) as response:
                        status_payload = response.read().decode("utf-8")
                        break
                except Exception:
                    time.sleep(0.25)

            if status_payload is None:
                raise RuntimeError("smoke-api timeout: /status did not become available")

            status_json = json.loads(status_payload)
            if status_json.get("status") != "running":
                raise RuntimeError(f"unexpected /status payload: {status_json}")

            with urllib.request.urlopen("http://127.0.0.1:18000/metrics", timeout=2) as response:
                metrics_payload = response.read().decode("utf-8")

            if "xiaolee_http_requests_total" not in metrics_payload:
                raise RuntimeError("metrics did not contain xiaolee_http_requests_total")

            print("API smoke checks finished successfully.")
            return 0
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except Exception:
                process.kill()
                process.wait()


if __name__ == "__main__":
    raise SystemExit(main())
