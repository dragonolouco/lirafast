"""Standalone LiraFast v0.3 research prototype.

Key properties:
- executable structural parameters (requires/adds masks + micro-ops)
- selective method activation through a rare pivot index
- bounded best-state memory
- verified route-template cache (procedure cache, not answer cache)
- compact packed record layout target

This file is intentionally small enough to audit. The full project contains the
richer semantic/compiler and binary-container code.
"""
from __future__ import annotations

from dataclasses import dataclass
import heapq
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Tuple


def bits(mask: int) -> Iterator[int]:
    while mask:
        b = mask & -mask
        yield b.bit_length() - 1
        mask ^= b


class Concepts:
    def __init__(self) -> None:
        self.names: List[str] = []
        self.index: Dict[str, int] = {}

    def id(self, name: str) -> int:
        name = name.upper()
        if name not in self.index:
            self.index[name] = len(self.names)
            self.names.append(name)
        return self.index[name]

    def mask(self, names: Iterable[str]) -> int:
        out = 0
        for name in names:
            out |= 1 << self.id(name)
        return out


@dataclass(frozen=True)
class Method:
    name: str
    requires: int
    adds: int
    ops: Tuple[str, ...] = ()
    cost: float = 1.0
    reliability: float = 1.0

    def applicable(self, state: int) -> bool:
        return (state & self.requires) == self.requires


class CompiledModel:
    def __init__(self, concepts: Concepts, methods: Sequence[Method]) -> None:
        self.concepts = concepts
        self.methods = tuple(self._canonicalize(methods))
        freq: Dict[int, int] = {}
        for m in self.methods:
            for bit in bits(m.requires):
                freq[bit] = freq.get(bit, 0) + 1

        pivots: Dict[int, List[int]] = {}
        zero: List[int] = []
        for i, m in enumerate(self.methods):
            req = list(bits(m.requires))
            if not req:
                zero.append(i)
                continue
            pivot = min(req, key=lambda b: (freq[b], b))
            pivots.setdefault(pivot, []).append(i)
        self.pivots = {k: tuple(v) for k, v in pivots.items()}
        self.zero = tuple(zero)

    @staticmethod
    def _canonicalize(methods: Sequence[Method]) -> List[Method]:
        best: Dict[Tuple[int, int, Tuple[str, ...]], Method] = {}
        for m in methods:
            key = (m.requires, m.adds, m.ops)
            old = best.get(key)
            score = m.cost + (1.0 - m.reliability)
            old_score = float("inf") if old is None else old.cost + (1.0 - old.reliability)
            if score < old_score:
                best[key] = m
        return list(best.values())

    def candidates(self, state: int) -> Iterator[int]:
        seen = set()
        for i in self.zero:
            seen.add(i)
            yield i
        for bit in bits(state):
            for i in self.pivots.get(bit, ()):
                if i not in seen:
                    seen.add(i)
                    yield i


class BoundedBest:
    def __init__(self, capacity: int) -> None:
        self.capacity = max(1, capacity)
        self.costs: Dict[int, float] = {}
        self.evictions = 0

    def get(self, state: int) -> float:
        return self.costs.get(state, float("inf"))

    def consider(self, state: int, cost: float) -> bool:
        old = self.costs.get(state)
        if old is not None:
            if cost >= old:
                return False
            self.costs[state] = cost
            return True
        if len(self.costs) >= self.capacity:
            worst_state, worst = max(self.costs.items(), key=lambda x: x[1])
            if cost >= worst:
                return False
            del self.costs[worst_state]
            self.evictions += 1
        self.costs[state] = cost
        return True


@dataclass(frozen=True)
class Route:
    method_indexes: Tuple[int, ...]
    goal: int

    def run(self, model: CompiledModel, state: int) -> Optional[int]:
        for idx in self.method_indexes:
            m = model.methods[idx]
            if not m.applicable(state):
                return None
            nxt = state | m.adds
            if nxt == state:
                return None
            state = nxt
        return state if (state & self.goal) == self.goal else None


@dataclass
class Report:
    solved: bool
    state: int
    methods: Tuple[str, ...]
    ops: Tuple[str, ...]
    expanded: int
    generated: int
    method_checks: int
    peak_frontier: int
    peak_history: int
    cache_hit: bool = False


class Solver:
    def __init__(self, model: CompiledModel) -> None:
        self.model = model
        self.routes: Dict[Tuple[int, int], Route] = {}

    def solve(self, initial: int, goal: int, *, frontier_limit: int = 256,
              history_limit: int = 4096) -> Report:
        key = (initial, goal)
        route = self.routes.get(key)
        if route is not None:
            state = route.run(self.model, initial)
            if state is not None:
                ids = tuple(self.model.methods[i].name for i in route.method_indexes)
                ops = tuple(op for i in route.method_indexes for op in self.model.methods[i].ops)
                return Report(True, state, ids, ops, 0, 0, len(route.method_indexes), 1, 1, True)

        heap: List[Tuple[float, int, int, Tuple[int, ...], Tuple[str, ...]]] = [(0.0, 0, initial, (), ())]
        best = BoundedBest(history_limit)
        best.consider(initial, 0.0)
        serial = expanded = generated = checks = 0
        peak_frontier = peak_history = 1

        while heap:
            cost, _, state, path, ops = heapq.heappop(heap)
            if cost > best.get(state):
                continue
            if (state & goal) == goal:
                self.routes[key] = Route(path, goal)
                names = tuple(self.model.methods[i].name for i in path)
                return Report(True, state, names, ops, expanded, generated, checks,
                              peak_frontier, peak_history)
            expanded += 1
            for idx in self.model.candidates(state):
                checks += 1
                m = self.model.methods[idx]
                if not m.applicable(state):
                    continue
                nxt = state | m.adds
                if nxt == state:
                    continue
                new_cost = cost + m.cost + max(0.0, 1.0 - m.reliability)
                generated += 1
                if not best.consider(nxt, new_cost):
                    continue
                serial += 1
                heapq.heappush(heap, (new_cost, serial, nxt, path + (idx,), ops + m.ops))
            if len(heap) > frontier_limit:
                heap = heapq.nsmallest(frontier_limit, heap)
                heapq.heapify(heap)
            peak_frontier = max(peak_frontier, len(heap))
            peak_history = max(peak_history, len(best.costs))

        return Report(False, initial, (), (), expanded, generated, checks,
                      peak_frontier, peak_history)


def demo_model(noise: int = 0) -> Tuple[CompiledModel, int, int]:
    c = Concepts()
    methods = [
        Method("make_expr", c.mask(["START", "ADD"]), c.mask(["EXPR"]), ("EXPR_ADD",), 0.5),
        Method("wrap", c.mask(["EXPR"]), c.mask(["FUNCTION"]), ("WRAP_FUNCTION",), 0.7),
        Method("verify", c.mask(["FUNCTION"]), c.mask(["VALID"]), ("VERIFY",), 0.2),
    ]
    for i in range(noise):
        methods.append(Method(f"noise_{i}", c.mask([f"NOISE_{i}"]), c.mask([f"OUT_{i}"])))
    model = CompiledModel(c, methods)
    return model, c.mask(["START", "ADD"]), c.mask(["VALID"])


if __name__ == "__main__":
    model, initial, goal = demo_model(20_000)
    solver = Solver(model)
    print(solver.solve(initial, goal))
    print(solver.solve(initial, goal))
