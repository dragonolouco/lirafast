"""Deterministic integer kernels used by the local/distributed compute MVP."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KernelResult:
    operation: str
    start: int
    end: int
    value: int
    iterations: int


def _validate_range(start: int, end: int) -> None:
    if not isinstance(start, int) or not isinstance(end, int):
        raise TypeError("start and end must be integers")
    if start < 0 or end < start:
        raise ValueError("expected 0 <= start <= end")


def sum_squares(start: int, end: int) -> KernelResult:
    """Compute sum(i*i for i in [start, end)) without floating point."""
    _validate_range(start, end)
    total = 0
    for value in range(start, end):
        total += value * value
    return KernelResult("sum_squares", start, end, total, end - start)


def sum_cubes(start: int, end: int) -> KernelResult:
    """Compute sum(i*i*i for i in [start, end)) without floating point."""
    _validate_range(start, end)
    total = 0
    for value in range(start, end):
        total += value * value * value
    return KernelResult("sum_cubes", start, end, total, end - start)


KERNELS = {"sum_squares": sum_squares, "sum_cubes": sum_cubes}


def run_kernel(operation: str, start: int, end: int) -> KernelResult:
    try:
        kernel = KERNELS[operation]
    except KeyError as exc:
        raise ValueError(f"unsupported operation: {operation}") from exc
    return kernel(start, end)
