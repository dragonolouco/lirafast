from __future__ import annotations

"""Compile BRX/DADOS JSON knowledge into reversible numeric LiraFast streams."""

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Tuple

from numeric_codec import EncodedKnowledge, NumericKnowledgeCodec


@dataclass(frozen=True)
class CompiledDataStats:
    source_bytes: int
    symbols_bytes: int
    structure_bytes: int
    total_encoded_bytes: int
    symbol_count: int


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def compile_json_file(path: str | Path) -> Tuple[EncodedKnowledge, CompiledDataStats]:
    p = Path(path)
    obj = load_json(p)
    codec = NumericKnowledgeCodec()
    encoded = codec.encode(obj)
    symbols = NumericKnowledgeCodec._decode_symbols(encoded.symbols)
    return encoded, CompiledDataStats(
        source_bytes=p.stat().st_size,
        symbols_bytes=len(encoded.symbols),
        structure_bytes=len(encoded.structure),
        total_encoded_bytes=encoded.total_bytes,
        symbol_count=len(symbols),
    )


def write_compiled(path: str | Path, out_prefix: str | Path) -> CompiledDataStats:
    encoded, stats = compile_json_file(path)
    base = Path(out_prefix)
    base.with_suffix(".lfsym").write_bytes(encoded.symbols)
    base.with_suffix(".lfstruct").write_bytes(encoded.structure)
    return stats
