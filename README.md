# LiraFast

Experimental research project for **executable structural intelligence**: store reusable methods, relations, error guards and selectively verified results in a compact, reversible format, then use a low-latency runtime to route known structures immediately and reserve expensive search for genuinely new barriers.

## Current version: v0.5 research release

Core ideas now implemented:

- reversible numeric knowledge representation;
- structural method memory;
- exact + variant-aware error memory;
- optional high-confidence final-result cache;
- `DEEP -> FAST` method promotion after repeated verification;
- data-driven primitive/cue loading from structured knowledge;
- bounded semantic compile cache;
- local-negation suppression for fast cue routing;
- AST-targeted incremental Python edits;
- single-file `.lirafast` v5 section container with checksums;
- selective structural solver from earlier v0.3 work.
- local-network coordinator/worker MVP for verifiable integer batch computation;

## Principle

```text
few reusable primitives
+ composition
+ verification
+ persistent error/method memory
= many reconstructable results
```

LiraFast is **not** currently a replacement for a frontier LLM. The repository is a research runtime and format prototype. Performance claims in the docs are microbenchmarks of specific routing/storage kernels unless explicitly stated otherwise.

## Run tests

```bash
python -m pip install -r requirements.txt
PYTHONPATH=. python -m pytest -q
```

## CLI examples

```bash
python lirafast_cli.py compile-text "crie função python para somar"
python lirafast_cli.py inspect model.lirafast
python lirafast_cli.py pack-memory memory.json model.lirafast
python lirafast_cli.py patch-python app.py Player.update replacement.py
```

See `V05_ARCHITECTURE.md`, `V04_ARCHITECTURE.md` and `V03_RESEARCH_STATUS.md` for the evolution of the design.

## Local Wi-Fi compute

The first distributed-compute prototype is documented in [`LAN_COMPUTE.md`](LAN_COMPUTE.md). Run `lan_compute.py worker` on a computer or Android device and use `lan_compute.py coordinator` to distribute verified numeric ranges across workers on the same Wi-Fi network.

```bash
python lan_compute.py worker --host 0.0.0.0 --port 8765
python lan_compute.py coordinator --workers http://PHONE_IP:8765 --operation sum_squares --end 1000000
```

This is a measurable parallel-compute foundation, not a claim of quantum computing or universal speed superiority.
