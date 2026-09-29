# LiraFast

Research repository for **LiraFast**, a separate fast-execution variant of the Lira project.

## v0.3 — Adaptive Structural Engine

This branch contains a small auditable prototype of the current research direction:

- executable structural parameters instead of memorized final answers;
- bitset state and procedure composition;
- selective method activation through a compiled pivot index;
- bounded historical state memory;
- verified route-template reuse (procedure cache, not result cache);
- external verification -> local constraint -> reroute;
- packed numeric format work in the full project.

The full working project remains larger than this research reference prototype. The files in this branch are intentionally compact so the core algorithm can be reviewed independently.

## Important

The benchmarks here measure routing/kernel overhead in synthetic tasks. They are **not** evidence that LiraFast already outperforms general-purpose LLMs.
