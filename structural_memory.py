from __future__ import annotations

"""Persistent structural memory for LiraFast.

Separates reusable method knowledge, error/variant guards, and optional
high-confidence final-result memory.
"""

from dataclasses import dataclass, asdict
from hashlib import blake2b
import json
from typing import Dict, Iterable, Optional, Sequence, Tuple


def stable_sig(parts: Iterable[str]) -> str:
    h = blake2b(digest_size=16)
    for p in parts:
        raw = p.strip().lower().encode("utf-8")
        h.update(len(raw).to_bytes(4, "little"))
        h.update(raw)
    return h.hexdigest()


@dataclass
class MethodMemory:
    method_id: str
    domain: str
    structure_signature: str
    op_ids: Tuple[int, ...]
    preconditions: Tuple[str, ...] = ()
    postconditions: Tuple[str, ...] = ()
    confidence: float = 0.5
    verified_runs: int = 0
    failures: int = 0
    provenance: str = "learned"

    def observe(self, ok: bool) -> None:
        if ok:
            self.verified_runs += 1
        else:
            self.failures += 1
        self.confidence = (1 + self.verified_runs) / (2 + self.verified_runs + self.failures)


@dataclass
class ErrorGuard:
    error_id: str
    domain: str
    exact_signature: str
    variant_signature: str
    detector: Tuple[str, ...]
    correction_method_id: Optional[str]
    evidence_count: int = 1
    confidence: float = 0.75
    active: bool = True

    def observe_again(self) -> None:
        self.evidence_count += 1
        self.confidence = self.evidence_count / (self.evidence_count + 1.0)


@dataclass
class FinalResultMemory:
    request_signature: str
    method_id: str
    result: str
    confidence: float
    verified_runs: int
    result_hash: str


class StructuralMemory:
    def __init__(self, result_threshold: float = 0.985, min_result_verifications: int = 2) -> None:
        self.result_threshold = result_threshold
        self.min_result_verifications = min_result_verifications
        self.methods: Dict[str, MethodMemory] = {}
        self.errors_exact: Dict[str, ErrorGuard] = {}
        self.errors_variant: Dict[str, ErrorGuard] = {}
        self.results: Dict[str, FinalResultMemory] = {}

    def register_method(self, method: MethodMemory) -> None:
        self.methods[method.method_id] = method

    def record_method_outcome(self, method_id: str, ok: bool) -> None:
        self.methods[method_id].observe(ok)

    def learn_error(
        self,
        *,
        domain: str,
        exact_parts: Sequence[str],
        variant_parts: Sequence[str],
        detector: Sequence[str],
        correction_method_id: Optional[str] = None,
    ) -> ErrorGuard:
        exact = stable_sig(exact_parts)
        variant = stable_sig(variant_parts)
        existing = self.errors_exact.get(exact)
        if existing:
            existing.observe_again()
            return existing
        guard = ErrorGuard(
            error_id=f"err:{exact[:12]}",
            domain=domain,
            exact_signature=exact,
            variant_signature=variant,
            detector=tuple(detector),
            correction_method_id=correction_method_id,
        )
        self.errors_exact[exact] = guard
        self.errors_variant[variant] = guard
        return guard

    def match_error(self, exact_parts: Sequence[str], variant_parts: Sequence[str]) -> Optional[ErrorGuard]:
        exact = stable_sig(exact_parts)
        guard = self.errors_exact.get(exact)
        if guard and guard.active:
            return guard
        variant = stable_sig(variant_parts)
        guard = self.errors_variant.get(variant)
        return guard if guard and guard.active else None

    def maybe_save_result(
        self,
        *,
        request_parts: Sequence[str],
        method_id: str,
        result: str,
        confidence: float,
        verified_runs: int,
    ) -> bool:
        if confidence < self.result_threshold or verified_runs < self.min_result_verifications:
            return False
        sig = stable_sig(request_parts)
        rh = blake2b(result.encode("utf-8"), digest_size=16).hexdigest()
        self.results[sig] = FinalResultMemory(sig, method_id, result, confidence, verified_runs, rh)
        return True

    def exact_result(self, request_parts: Sequence[str]) -> Optional[FinalResultMemory]:
        return self.results.get(stable_sig(request_parts))

    def best_method(self, structure_signature: str, domain: Optional[str] = None) -> Optional[MethodMemory]:
        candidates = [m for m in self.methods.values() if m.structure_signature == structure_signature]
        if domain is not None:
            candidates = [m for m in candidates if m.domain == domain]
        if not candidates:
            return None
        return max(candidates, key=lambda m: (m.confidence, m.verified_runs, -m.failures))

    def to_json(self) -> str:
        payload = {
            "version": 1,
            "result_threshold": self.result_threshold,
            "min_result_verifications": self.min_result_verifications,
            "methods": [asdict(v) for v in self.methods.values()],
            "errors": [asdict(v) for v in self.errors_exact.values()],
            "results": [asdict(v) for v in self.results.values()],
        }
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

    @classmethod
    def from_json(cls, text: str) -> "StructuralMemory":
        p = json.loads(text)
        mem = cls(p["result_threshold"], p["min_result_verifications"])
        for row in p.get("methods", []):
            row["op_ids"] = tuple(row.get("op_ids", ()))
            row["preconditions"] = tuple(row.get("preconditions", ()))
            row["postconditions"] = tuple(row.get("postconditions", ()))
            mem.register_method(MethodMemory(**row))
        for row in p.get("errors", []):
            row["detector"] = tuple(row.get("detector", ()))
            g = ErrorGuard(**row)
            mem.errors_exact[g.exact_signature] = g
            mem.errors_variant[g.variant_signature] = g
        for row in p.get("results", []):
            r = FinalResultMemory(**row)
            mem.results[r.request_signature] = r
        return mem
