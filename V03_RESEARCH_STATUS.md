# LiraFast v0.3 research status

Date: 2026-09-29

## What changed

The v0.3 prototype evolves the previous structural runtime in four directions:

1. **Selective routing** — methods are indexed by a rare required concept, so unrelated methods are not scanned at every state.
2. **Bounded history** — not only the frontier but also the remembered best-state table has a hard capacity.
3. **Procedure reuse** — a verified sequence of methods can be cached and re-executed for the same structural signature; numerical answers are not cached as knowledge.
4. **Verification-driven repair** — a failed objective check adds a local constraint and reruns only the affected structural search.

## Research references studied through GitHub

- microsoft/BitNet — low-bit representations and specialized inference kernels.
- ggml-org/llama.cpp — integer quantization, SIMD and hardware backends.
- state-spaces/mamba — selective state update / selective scan.
- vllm-project/vllm — bounded/paged active memory, continuous work scheduling, reusable cached structure.
- ML-GSAI/LLaDA — iterative refinement of uncertain positions rather than rebuilding everything.
- egraphs-good/egg — equality saturation and canonicalization of equivalent structures.

The prototype translates principles from these systems; it does not copy their architectures.

## Local experimental results

A sparse synthetic graph with 20,004 methods, only four of which were relevant, was solved 50 times:

- full scan method checks: 4,000,800
- selective method checks: 500
- check reduction: ~8,001.6x
- local Python wall-clock ratio in that run: ~190.5x

A separate NumPy micro-kernel executed one million ADD items in roughly 1.1–1.2 ms in the local environment after structural selection. This is a simple vector arithmetic benchmark, not an AI benchmark.

The full local project passed **76 tests** after the v0.3 evolution.
