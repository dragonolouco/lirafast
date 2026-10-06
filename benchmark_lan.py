from __future__ import annotations

import argparse
import json
from time import perf_counter

from lan_compute import coordinate
from math_kernels import run_kernel


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Benchmark LiraFast local vs LAN")
    parser.add_argument("--workers", nargs="+", required=True)
    parser.add_argument("--end", type=int, default=1_000_000)
    parser.add_argument("--chunk-size", type=int, default=100_000)
    args = parser.parse_args(argv)
    started = perf_counter()
    local = run_kernel("sum_squares", 0, args.end)
    local_ms = (perf_counter() - started) * 1000
    distributed = coordinate(args.workers, "sum_squares", 0, args.end, args.chunk_size)
    if distributed["value"] != local.value:
        raise SystemExit("verification failed: LAN result differs from local result")
    print(json.dumps({"local_ms": local_ms, "distributed": distributed,
                      "verified_equal": True}, indent=2))


if __name__ == "__main__":
    main()
