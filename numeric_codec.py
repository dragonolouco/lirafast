from __future__ import annotations

"""LiraFast reversible numeric knowledge codec.

This is not encryption. The runtime representation is numeric and compact, while
an explicit symbol table makes it fully reversible for debugging/auditing.
"""

from dataclasses import dataclass
import struct
from typing import Any, Dict, Iterable, List, Tuple

MAGIC = b"LFN4"
VERSION = 1

TAG_NULL = 0
TAG_FALSE = 1
TAG_TRUE = 2
TAG_INT = 3
TAG_FLOAT64 = 4
TAG_STRING = 5
TAG_ARRAY = 6
TAG_OBJECT = 7


def _put_uvarint(out: bytearray, n: int) -> None:
    if n < 0:
        raise ValueError("uvarint requires non-negative integer")
    while n >= 0x80:
        out.append((n & 0x7F) | 0x80)
        n >>= 7
    out.append(n)


def _get_uvarint(data: memoryview, pos: int) -> Tuple[int, int]:
    shift = 0
    value = 0
    while True:
        if pos >= len(data):
            raise ValueError("truncated varint")
        b = int(data[pos])
        pos += 1
        value |= (b & 0x7F) << shift
        if not (b & 0x80):
            return value, pos
        shift += 7
        if shift > 63:
            raise ValueError("varint too large")


def _zigzag_encode(n: int) -> int:
    return (n << 1) ^ (n >> (n.bit_length() or 1))


def _zigzag_decode(n: int) -> int:
    return (n >> 1) ^ -(n & 1)


@dataclass(frozen=True)
class EncodedKnowledge:
    symbols: bytes
    structure: bytes

    @property
    def total_bytes(self) -> int:
        return len(self.symbols) + len(self.structure)


class NumericKnowledgeCodec:
    """Encode JSON-compatible knowledge to a reversible numeric representation."""

    def __init__(self) -> None:
        self._symbol_to_id: Dict[str, int] = {}
        self._symbols: List[str] = []

    def _intern(self, text: str) -> int:
        try:
            return self._symbol_to_id[text]
        except KeyError:
            idx = len(self._symbols)
            self._symbol_to_id[text] = idx
            self._symbols.append(text)
            return idx

    def _collect(self, value: Any) -> None:
        if isinstance(value, str):
            self._intern(value)
        elif isinstance(value, dict):
            for k, v in value.items():
                if not isinstance(k, str):
                    raise TypeError("JSON object keys must be strings")
                self._intern(k)
                self._collect(v)
        elif isinstance(value, list):
            for item in value:
                self._collect(item)
        elif value is None or isinstance(value, (bool, int, float)):
            return
        else:
            raise TypeError(f"unsupported type: {type(value)!r}")

    def encode(self, value: Any) -> EncodedKnowledge:
        self._symbol_to_id.clear()
        self._symbols.clear()
        self._collect(value)

        sym = bytearray(MAGIC)
        sym.append(VERSION)
        _put_uvarint(sym, len(self._symbols))
        for s in self._symbols:
            raw = s.encode("utf-8")
            _put_uvarint(sym, len(raw))
            sym.extend(raw)

        structure = bytearray()
        self._encode_value(value, structure)
        return EncodedKnowledge(bytes(sym), bytes(structure))

    def _encode_value(self, value: Any, out: bytearray) -> None:
        if value is None:
            out.append(TAG_NULL)
        elif value is False:
            out.append(TAG_FALSE)
        elif value is True:
            out.append(TAG_TRUE)
        elif isinstance(value, int) and not isinstance(value, bool):
            out.append(TAG_INT)
            _put_uvarint(out, _zigzag_encode(value))
        elif isinstance(value, float):
            out.append(TAG_FLOAT64)
            out.extend(struct.pack("<d", value))
        elif isinstance(value, str):
            out.append(TAG_STRING)
            _put_uvarint(out, self._symbol_to_id[value])
        elif isinstance(value, list):
            out.append(TAG_ARRAY)
            _put_uvarint(out, len(value))
            for item in value:
                self._encode_value(item, out)
        elif isinstance(value, dict):
            out.append(TAG_OBJECT)
            _put_uvarint(out, len(value))
            for key, item in value.items():
                _put_uvarint(out, self._symbol_to_id[key])
                self._encode_value(item, out)
        else:
            raise TypeError(f"unsupported type: {type(value)!r}")

    @staticmethod
    def decode(encoded: EncodedKnowledge) -> Any:
        symbols = NumericKnowledgeCodec._decode_symbols(encoded.symbols)
        data = memoryview(encoded.structure)
        value, pos = NumericKnowledgeCodec._decode_value(data, 0, symbols)
        if pos != len(data):
            raise ValueError("trailing structure bytes")
        return value

    @staticmethod
    def _decode_symbols(blob: bytes) -> List[str]:
        data = memoryview(blob)
        if len(data) < 5 or bytes(data[:4]) != MAGIC:
            raise ValueError("bad symbol table magic")
        if int(data[4]) != VERSION:
            raise ValueError("unsupported symbol table version")
        pos = 5
        count, pos = _get_uvarint(data, pos)
        out: List[str] = []
        for _ in range(count):
            n, pos = _get_uvarint(data, pos)
            end = pos + n
            if end > len(data):
                raise ValueError("truncated symbol")
            out.append(bytes(data[pos:end]).decode("utf-8"))
            pos = end
        if pos != len(data):
            raise ValueError("trailing symbol bytes")
        return out

    @staticmethod
    def _decode_value(data: memoryview, pos: int, symbols: List[str]) -> Tuple[Any, int]:
        if pos >= len(data):
            raise ValueError("truncated value")
        tag = int(data[pos])
        pos += 1
        if tag == TAG_NULL:
            return None, pos
        if tag == TAG_FALSE:
            return False, pos
        if tag == TAG_TRUE:
            return True, pos
        if tag == TAG_INT:
            n, pos = _get_uvarint(data, pos)
            return _zigzag_decode(n), pos
        if tag == TAG_FLOAT64:
            end = pos + 8
            if end > len(data):
                raise ValueError("truncated float")
            return struct.unpack("<d", data[pos:end])[0], end
        if tag == TAG_STRING:
            idx, pos = _get_uvarint(data, pos)
            return symbols[idx], pos
        if tag == TAG_ARRAY:
            n, pos = _get_uvarint(data, pos)
            arr = []
            for _ in range(n):
                item, pos = NumericKnowledgeCodec._decode_value(data, pos, symbols)
                arr.append(item)
            return arr, pos
        if tag == TAG_OBJECT:
            n, pos = _get_uvarint(data, pos)
            obj = {}
            for _ in range(n):
                key_id, pos = _get_uvarint(data, pos)
                value, pos = NumericKnowledgeCodec._decode_value(data, pos, symbols)
                obj[symbols[key_id]] = value
            return obj, pos
        raise ValueError(f"unknown tag {tag}")
