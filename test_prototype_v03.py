from prototype_v03 import BoundedBest, Solver, demo_model


def test_selective_solver_ignores_unrelated_library():
    model, initial, goal = demo_model(10_000)
    report = Solver(model).solve(initial, goal)
    assert report.solved
    assert report.method_checks < 50


def test_route_cache_reuses_procedure():
    model, initial, goal = demo_model(1000)
    solver = Solver(model)
    first = solver.solve(initial, goal)
    second = solver.solve(initial, goal)
    assert first.solved and second.solved
    assert not first.cache_hit
    assert second.cache_hit
    assert second.expanded == 0


def test_history_memory_has_hard_limit():
    b = BoundedBest(4)
    for i in range(100):
        b.consider(i, float(100 - i))
    assert len(b.costs) <= 4
    assert b.evictions > 0
