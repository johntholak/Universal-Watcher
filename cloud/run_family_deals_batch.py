"""Bounded GitHub runner for the preserved Family Deals V5 flow.

Requires UW_API_BASE and UW_WORKER_SECRET from GitHub Actions secrets. The
workflow dispatch carries no criteria. This script does nothing on import.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import sys
import threading
from contextlib import contextmanager
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    from .family_deals_v5 import normalize_v5_snapshot, run_v5_page
except ImportError:  # direct script execution
    from family_deals_v5 import normalize_v5_snapshot, run_v5_page

ROOT = Path(__file__).resolve().parents[1]
LEGACY_SERVER = ROOT / "modules" / "family-deals" / "server.py"


@contextmanager
def local_v5_server():
    spec = importlib.util.spec_from_file_location("universal_watcher_family_v5", LEGACY_SERVER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    server = ThreadingHTTPServer(("127.0.0.1", 0), module.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


class WorkerAPI:
    def __init__(self, base: str, secret: str):
        if not base.startswith("https://") or len(secret) < 32:
            raise ValueError("Worker API requires HTTPS and a configured secret")
        self.base = base.rstrip("/")
        self.secret = secret

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = Request(
            self.base + path,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": "Bearer " + self.secret,
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=30) as response:
                return json.load(response)
        except HTTPError as exc:
            # Never print headers, request bodies, criteria or credentials.
            raise RuntimeError(
                f"Worker API rejected {path.rsplit('/', 1)[-1]} with HTTP {exc.code}"
            ) from None
        except URLError:
            raise RuntimeError("Worker API temporarily unreachable") from None


async def heartbeat(api: WorkerAPI, job: dict[str, Any], stopped: asyncio.Event,
                    lost: asyncio.Event) -> None:
    path = f"/api/v1/internal/jobs/{job['id']}/heartbeat"
    while not stopped.is_set():
        try:
            await asyncio.wait_for(stopped.wait(), timeout=90)
        except asyncio.TimeoutError:
            try:
                await asyncio.to_thread(api.post, path, {"claim_id": job["claim_id"]})
            except RuntimeError:
                lost.set()
                return


async def execute_job(api: WorkerAPI, page: Any, base_url: str,
                      job: dict[str, Any]) -> dict[str, Any]:
    stopped, lost = asyncio.Event(), asyncio.Event()
    renewal = asyncio.create_task(heartbeat(api, job, stopped, lost))
    try:
        try:
            snapshot = await asyncio.wait_for(run_v5_page(page, base_url, job["criteria"]), timeout=600)
            result = normalize_v5_snapshot(snapshot, job["criteria"], job["id"])
        except Exception as exc:
            if lost.is_set():
                raise RuntimeError("Job lease was lost; failure will not be submitted")
            response = await asyncio.to_thread(
                api.post,
                f"/api/v1/internal/jobs/{job["id"]}/failure",
                {"claim_id": job["claim_id"], "category": "execution"},
            )
            print(f"Family Deals job {job["id"]} execution error: {type(exc).__name__}; failure response={response}")
            return {"outcome": "ERROR", "candidate_count": 0}
        if lost.is_set():
            raise RuntimeError("Job lease was lost; result will not be submitted")
        path = f"/api/v1/internal/jobs/{job['id']}"
        for offset in range(0, len(result["results"]), 5):
            if lost.is_set():
                raise RuntimeError("Job lease was lost; result will not be submitted")
            await asyncio.to_thread(
                api.post,
                path + "/results",
                {"claim_id": job["claim_id"], "items": result["results"][offset:offset + 5]},
            )
        if lost.is_set():
            raise RuntimeError("Job lease was lost; result will not be submitted")
        response = await asyncio.to_thread(
            api.post,
            path + "/complete",
            {
                "claim_id": job["claim_id"],
                "outcome": result["outcome"],
                "summary": result["summary"],
                "coverage": result["coverage"],
            },
        )
        print(f"Family Deals job {job["id"]} completed: outcome={result["outcome"]}; candidates={len(result["results"])}; completion response={response}")
        return {"outcome": result["outcome"], "candidate_count": len(result["results"])}
    finally:
        stopped.set()
        await renewal


async def run_batch(api: WorkerAPI) -> int:
    from playwright.async_api import async_playwright

    pending = await asyncio.to_thread(
        api.post,
        "/api/v1/internal/jobs/claim",
        {"module": "family-deals", "limit": 1},
    )
    if not pending.get("jobs"):
        return 0
    handled = 0
    with local_v5_server() as base_url:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            try:
                context = await browser.new_context()
                for _ in range(10):
                    jobs = pending.get("jobs") or []
                    if not jobs:
                        break
                    job = jobs[0]
                    page = await context.new_page()
                    try:
                        await execute_job(api, page, base_url, job)
                        handled += 1
                    finally:
                        await page.close()
                    pending = await asyncio.to_thread(
                        api.post,
                        "/api/v1/internal/jobs/claim",
                        {"module": "family-deals", "limit": 1},
                    )
            finally:
                await browser.close()
    return handled


def main() -> int:
    api = WorkerAPI(os.environ.get("UW_API_BASE", ""), os.environ.get("UW_WORKER_SECRET", ""))
    count = asyncio.run(run_batch(api))
    print(f"Family Deals jobs handled: {count}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
