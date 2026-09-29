# DADOS -> LiraFast v0.4 findings

The supplied DADOS archive was used as a real structural corpus for the v0.4 codec experiment.

## Corpus

- 92 JSON files
- approximately 15.8 MB of raw JSON text
- domains include programming languages, interpretation, narrative, characters, dialogues, worlds and localized language knowledge

## Reversible numeric compile experiment

All 92 JSON files were encoded and decoded successfully with the v0.4 numeric codec.

Aggregate local result:

- raw JSON: 15,806,424 bytes
- symbol dictionaries: 2,457,722 bytes
- hot numeric structure streams: 1,531,046 bytes
- total reversible encoding: 3,988,768 bytes
- total encoded / raw: ~25.2%
- hot structure / raw: ~9.7%
- Python compile pass over all 92 files: ~1.16 s in the test environment

Representative examples:

| file | raw | symbols | hot structure | total reversible |
| --- | ---: | ---: | ---: | ---: |
| typescript.json | 60,493 B | 20,989 B | 5,837 B | 26,826 B |
| interpretacao.json | 1,630,348 B | 198,409 B | 174,188 B | 372,597 B |
| historias.json | 2,555,094 B | 122,781 B | 231,778 B | 354,559 B |

These are codec/storage measurements, not model-quality benchmarks.

## Meaning for the architecture

The experiment supports a hot/cold split:

- **cold/auditable layer**: symbol dictionary and provenance;
- **hot/runtime layer**: numeric IDs, tags, masks, opcodes and structural relationships;
- **translator**: reconstructs human-readable structure when inspection or editing is needed.

The representation is intentionally reversible. It is not meant to hide knowledge; it is meant to avoid carrying human-readable repetition through the hot execution path.
