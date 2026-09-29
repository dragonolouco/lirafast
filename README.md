# LiraFast

Experimental research project for **executable structural intelligence**.

## Current research branch: v0.6 — Executable Structural Programs

v0.6 extends the v0.5 runtime so a learned method is no longer only metadata. It can be stored as a compact validated numeric program and executed directly with new inputs.

### Implemented

- structural semantic routing;
- exact-result fast path;
- method/error/result memory;
- DEEP -> FAST promotion;
- reversible numeric knowledge codec;
- AST-targeted Python delta editing;
- sectioned `.lirafast` container;
- compact numeric VM;
- safe mathematical expression compiler;
- executable program store;
- verified formula learning;
- persistence/reload of runnable methods;
- runtime execution from method memory.

### Example

A reusable structure such as:

```
a + b * 2
```

can become a numeric instruction stream conceptually equivalent to:

```
LOAD_INPUT 0
LOAD_INPUT 1
LOAD_CONST 0
MUL
ADD
RETURN
```

After verification, the program can be saved and later executed for new values without reconstructing the expression in natural language or source code.

### Fast path hierarchy

```text
exact verified request
  -> saved result

known structural family
  -> executable method
  -> calculate with current inputs

known error / variant
  -> guard / correction route

unknown barrier
  -> DEEP exploration
  -> verify
  -> persist new method
  -> future FAST execution
```

## Tests

```bash
python -m pip install -r requirements.txt
PYTHONPATH=. python -m pytest -q
```

## Scope

LiraFast is still a research prototype. The numeric VM and routing benchmarks measure specific runtime mechanisms, not general intelligence or end-to-end superiority over large language models.

See `V06_ARCHITECTURE.md` for the current design.
