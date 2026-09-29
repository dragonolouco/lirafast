# LiraFast v0.5 — Learned Structure, Promotion and Delta Execution

## Goal

v0.5 turns the earlier storage/runtime prototypes into a learning cycle:

```text
INPUT
  -> exact verified result? -> return immediately
  -> cheap structural compile
  -> known error/variant? -> guard/correction
  -> known structural method? -> execute FAST
  -> otherwise DEEP
       -> experiment/solve
       -> verify
       -> successful trace
       -> repeated evidence
       -> promote method to FAST
       -> future variants reuse the structure
```

The model does not need to encode every possible answer. It needs enough primitives, relations and procedures to reconstruct answers, plus selective memory for valuable exact outputs.

## Data-driven primitives

`knowledge_loader.py` translates explicit routing cues from structured knowledge files into compiler aliases. It does not recursively treat every string as a fact. Supported routing-grade structures currently include:

- `signal_roles` / `interpret_as` cues;
- `domain_routing` signals;
- language `format_id`, aliases and extensions;
- semantic intents;
- optional lexical surfaces.

A local run over `interpretacao.json`, Python, TypeScript and pt-BR knowledge yielded 150 routing concepts and 1,326 cue/alias forms.

## Negation

Fast keyword activation cannot ignore local negation. `sem alterar` must not activate `action:edit`. v0.5 suppresses action/intent/operator activation when a nearby negator scopes over the cue, while retaining explicit `negation` and constraint concepts.

This is still a lightweight rule, not a complete semantic theory. Ambiguous scope remains a DEEP-path problem.

## Exact result vs structural method

These are intentionally separate:

- exact result key = normalized complete request;
- structural method key = semantic primitive signature.

Therefore a cached answer to one exact request cannot silently become the answer to a variant. The variant may reuse the method but must execute it with its own values/state.

## DEEP -> FAST promotion

A successful trace does not become a permanent method after one lucky run. `DeepToFastPromoter` requires repeated success and a minimum confidence threshold. Domain is part of the trace identity, so the same structural signature in unrelated domains does not overwrite another method.

## Artifact delta

`PythonASTDelta` edits an existing function/class by AST location while preserving all unrelated source bytes. It supports qualified methods such as `Player.update`, verifies that the target region has not changed since planning, validates the replacement node and parses the full resulting file before writing.

This implements the rule: **valid existing artifacts are state, not prompts to regenerate from zero**.

## Container

`container_v05.py` provides a single-file `.lirafast` section container with:

- fixed magic/version;
- section directory;
- optional per-section zlib compression;
- CRC32 validation;
- generic sections for memory, metadata, symbols, numeric structure and future kernels.

The container is intentionally generic so the internal representation can evolve without changing the extension.

## Local microbenchmarks

Repeated-call Python microbenchmarks in the development environment after the bounded semantic cache:

- cached semantic compile: ~0.5M calls/s;
- known structural method route: ~0.13M calls/s;
- exact verified result route: ~0.20M calls/s.

These numbers measure tiny routing operations, not general AI capability and not end-to-end model quality.
