import json
import threading
import urllib.request

from http.server import ThreadingHTTPServer

from lan_compute import WorkerHandler, coordinate
from math_kernels import run_kernel


def test_sum_squares_kernel_has_exact_half_open_range():
    result = run_kernel("sum_squares", 1, 5)
    assert result.value == 1 + 4 + 9 + 16
    assert result.iterations == 4


def test_worker_health_and_compute():
    server = ThreadingHTTPServer(("127.0.0.1", 0), WorkerHandler)
    server.token = "secret"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with urllib.request.urlopen(base + "/health") as response:
            assert json.loads(response.read())["ok"] is True
        request = urllib.request.Request(
            base + "/compute",
            data=json.dumps({"operation": "sum_squares", "start": 0, "end": 5}).encode(),
            headers={"Content-Type": "application/json", "X-LiraFast-Token": "secret"},
            method="POST",
        )
        with urllib.request.urlopen(request) as response:
            payload = json.loads(response.read())
        assert payload["value"] == 30
    finally:
        server.shutdown()
        server.server_close()


def test_coordinator_distributes_and_verifies_chunks():
    servers, threads, urls = [], [], []
    try:
        for _ in range(2):
            server = ThreadingHTTPServer(("127.0.0.1", 0), WorkerHandler)
            server.token = None
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            servers.append(server)
            threads.append(thread)
            urls.append(f"http://127.0.0.1:{server.server_port}")
        result = coordinate(urls, "sum_squares", 0, 100, 17)
        assert result["value"] == sum(i * i for i in range(100))
        assert result["iterations"] == 100
        assert result["chunks"] == 6
    finally:
        for server in servers:
            server.shutdown()
            server.server_close()
