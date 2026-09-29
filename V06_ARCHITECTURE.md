# LiraFast v0.6 — Executable Structural Programs

v0.6 moves from **remembering that a method exists** to **persisting a method that can directly execute**.

## Representation

A numeric method consists of:

- named input slots;
- numeric constant pool;
- validated opcode stream;
- structural method metadata in `StructuralMemory`;
- verification evidence.

Example source formula:

```
a + b * 2
```

can compile to the conceptual stream:

```
LOAD_INPUT a
LOAD_INPUT b
LOAD_CONST 2
MUL
ADD
RETURN
```

The runtime does not need the original expression to calculate new inputs.

## Why this matches the project goal

A calculator does not memorize every multiplication result. It preserves an operation that can regenerate correct results. LiraFast v0.6 applies the same principle to reusable structural methods.

```text
known exact request + verified final result
    -> RESULT fast path

known structural signature + executable method
    -> load inputs
    -> run compact numeric program
    -> result

unknown structure
    -> DEEP discovery
    -> verify examples/invariants
    -> persist program
    -> future FAST execution
```

## Safety / correctness boundary

The formula compiler is deliberately restricted. It never calls Python `eval` and rejects arbitrary function calls, imports, attributes and other executable syntax. Supported operations are explicit VM opcodes.

A program must pass static stack validation before serialization or execution.

## Verification before learning

`learn_verified_formula` requires examples with expected results. A formula that fails even one example beyond tolerance is rejected instead of becoming structural memory.

Later versions should add:

- property/invariant testing;
- symbolic equivalence where possible;
- counterexample generation;
- automatic synthesis of candidate programs;
- integer/bitwise/vector opcodes;
- SIMD/native backends;
- method specialization and fusion.

## Persistence

A v0.6 `.lirafast` file stores:

- `memory`: methods/errors/results;
- `programs`: executable numeric bytecode keyed by method ID;
- `meta`: format/version metadata.

The existing sectioned container remains generic so future native kernels and indices can be added without changing the file extension.
