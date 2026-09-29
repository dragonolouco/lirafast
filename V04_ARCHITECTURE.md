# LiraFast v0.4 — Reversible Structural Memory

## Core correction

LiraFast does not need to memorize every answer. It should memorize **how to reconstruct classes of answers** and optionally cache only final results that are unusually valuable, stable and highly verified.

The system distinguishes:

1. **Method memory** — reusable procedure/structure.
2. **Error memory** — exact failures plus structural variants and corrective route.
3. **Result memory** — optional fast-path final outputs with high confidence and repeated verification.
4. **Artifact memory** — existing files are state; edits patch the required region instead of regenerating the whole artifact.

## Reversible numeric representation

The runtime representation is not encryption. Human-readable symbols are interned once into a symbol table, while the hot structural stream stores numeric IDs, tags, masks and operation codes. A debug/translation tool can reconstruct the original JSON-compatible structure exactly.

```text
human structure
    -> symbol dictionary
    -> numeric IDs
    -> typed instruction stream
    -> runtime

runtime/debug
    -> IDs
    -> symbol dictionary
    -> original structure
```

This is closer to tokenized bytecode/IR than to opaque neural weights.

## Fast path vs deep path

```text
exact verified repeat
    -> result cache

known structural family
    -> method cache
    -> execute with new values

known error/variant
    -> guard before execution
    -> corrective method

new barrier
    -> deep search / experiments
    -> verification
    -> create new method
    -> register error constraints
    -> promote to fast path
```

## Incremental artifact rule

Never rebuild an artifact from zero when the requested change is local and the existing artifact is valid.

```text
existing artifact
  -> snapshot/hash
  -> locate target node/range
  -> calculate minimal delta
  -> verify precondition hash
  -> patch only target
  -> run validation/tests
  -> retain unchanged bytes/structure
```

The current reference engine is line based. Language-specific adapters should evolve this to AST/node-based edits for Python, TypeScript, Java, C#, etc.

## Error architecture

An error record stores:

- exact signature;
- variant/generalized signature;
- domain;
- detector(s);
- condition/context;
- correction method;
- evidence count;
- confidence;
- active/retired state.

A guard is scoped: it prevents the failed structural condition rather than banning a whole technique globally when the failure was contextual.

## What DADOS already supports

The supplied DADOS documents already specify the same design direction:

- basic finite primitives -> composition -> practically unlimited results;
- fast path for mastered structures;
- deep path for new/ambiguous problems;
- error, cause, condition, detector, correction and similar errors are knowledge;
- new knowledge extends/relates to previous knowledge rather than silently replacing it.

The v0.4 code turns those principles into concrete runtime objects.
