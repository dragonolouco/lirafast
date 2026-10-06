"""Local-network compute coordinator and worker.

The protocol is intentionally small and standard-library-only so a worker can run
on Linux, Termux or another Python-capable phone on the same Wi-Fi network.
"""
from __future__ import annotations

import argparse
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from time import perf_counter
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from math_kernels import run_kernel

MAX_WORKER_SPAN = 10_000_000


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _token_ok(headers, expected: str | None) -> bool:
    return not expected or headers.get("X-LiraFast-Token") == expected


class WorkerHandler(BaseHTTPRequestHandler):
    server_version = "LiraFastWorker/0.1"

    def _send(self, status: int, payload: Any) -> None:
        body = _json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._send(200, {"ok": True, "service": "lirafast-worker", "max_span": MAX_WORKER_SPAN})
        else:
            self._send(404, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        expected = getattr(self.server, "token", None)
        if not _token_ok(self.headers, expected):
            self._send(401, {"error": "unauthorized"})
            return
        if self.path != "/compute":
            self._send(404, {"error": "not_found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            request = json.loads(self.rfile.read(length))
            start, end = int(request["start"]), int(request["end"])
            if end - start > MAX_WORKER_SPAN:
                raise ValueError("chunk exceeds worker limit")
            started = perf_counter()
            result = run_kernel(str(request["operation"]), start, end)
            payload = asdict(result) | {"elapsed_ms": (perf_counter() - started) * 1000}
            self._send(200, payload)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            self._send(400, {"error": str(exc)})
        except Exception as exc:  # keep worker protocol alive for one bad task
            self._send(500, {"error": f"worker_failure: {exc}"})

    def log_message(self, format: str, *args: Any) -> None:
        return


def serve_worker(host: str, port: int, token: str | None = None) -> None:
    server = ThreadingHTTPServer((host, port), WorkerHandler)
    server.token = token
    print(f"LiraFast worker listening on http://{host}:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def _request_worker(url: str, payload: dict[str, Any], token: str | None, timeout: float) -> dict[str, Any]:
    endpoint = url.rstrip("/") + "/compute"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-LiraFast-Token"] = token
    request = Request(endpoint, data=_json_bytes(payload), headers=headers, method="POST")
    try:
        with urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read())
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"worker {url} unavailable: {exc}") from exc
    if "error" in body:
        raise RuntimeError(f"worker {url} rejected task: {body['error']}")
    return body


def coordinate(workers: list[str], operation: str, start: int, end: int, chunk_size: int,
               token: str | None = None, timeout: float = 30.0) -> dict[str, Any]:
    if not workers:
        raise ValueError("at least one worker URL is required")
    if end <= start or chunk_size <= 0:
        raise ValueError("expected end > start and chunk_size > 0")
    chunks = [(offset, min(offset + chunk_size, end)) for offset in range(start, end, chunk_size)]
    started = perf_counter()
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=len(workers)) as pool:
        futures = {
            pool.submit(_request_worker, workers[index % len(workers)],
                        {"operation": operation, "start": a, "end": b}, token, timeout): (a, b)
            for index, (a, b) in enumerate(chunks)
        }
        for future in as_completed(futures):
            result = future.result()
            a, b = futures[future]
            if result["start"] != a or result["end"] != b or result["operation"] != operation:
                raise RuntimeError("worker returned a mismatched chunk")
            results.append(result)
    results.sort(key=lambda item: item["start"])
    expected_start = start
    for item in results:
        if item["start"] != expected_start:
            raise RuntimeError("missing or overlapping chunk")
        expected_start = item["end"]
    if expected_start != end:
        raise RuntimeError("incomplete distributed range")
    return {
        "operation": operation,
        "start": start,
        "end": end,
        "value": sum(item["value"] for item in results),
        "iterations": sum(item["iterations"] for item in results),
        "chunks": len(results),
        "workers": workers,
        "elapsed_ms": (perf_counter() - started) * 1000,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="LiraFast local-network math compute")
    sub = parser.add_subparsers(dest="command", required=True)
    worker = sub.add_parser("worker", help="run a worker on this machine/phone")
    worker.add_argument("--host", default="0.0.0.0")
    worker.add_argument("--port", type=int, default=8765)
    worker.add_argument("--token", default=os.getenv("LIRAFAST_TOKEN"))
    coord = sub.add_parser("coordinator", help="distribute a numeric range across workers")
    coord.add_argument("--workers", nargs="+", required=True)
    coord.add_argument("--operation", choices=["sum_squares", "sum_cubes"], default="sum_squares")
    coord.add_argument("--start", type=int, default=0)
    coord.add_argument("--end", type=int, required=True)
    coord.add_argument("--chunk-size", type=int, default=100_000)
    coord.add_argument("--timeout", type=float, default=30.0)
    coord.add_argument("--token", default=os.getenv("LIRAFAST_TOKEN"))
    args = parser.parse_args(argv)
    if args.command == "worker":
        serve_worker(args.host, args.port, args.token)
    else:
        print(json.dumps(coordinate(args.workers, args.operation, args.start, args.end,
                                     args.chunk_size, args.token, args.timeout), indent=2))


if __name__ == "__main__":
    main()
