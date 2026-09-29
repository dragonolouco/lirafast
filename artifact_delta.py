from __future__ import annotations

"""Transactional incremental artifact editing for LiraFast."""

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Sequence, Tuple


def digest(data: bytes) -> str:
    return sha256(data).hexdigest()


@dataclass(frozen=True)
class ArtifactSnapshot:
    path: str
    sha256: str
    size: int
    line_count: int


@dataclass(frozen=True)
class LinePatch:
    start_line: int
    end_line: int
    replacement: Tuple[str, ...]
    expected_before_hash: str


@dataclass(frozen=True)
class PatchResult:
    before: ArtifactSnapshot
    after: ArtifactSnapshot
    changed_lines_old: int
    changed_lines_new: int
    preserved_prefix_lines: int
    preserved_suffix_lines: int


class ArtifactDeltaEngine:
    @staticmethod
    def snapshot(path: str | Path) -> ArtifactSnapshot:
        p = Path(path)
        raw = p.read_bytes()
        text = raw.decode("utf-8")
        return ArtifactSnapshot(str(p), digest(raw), len(raw), len(text.splitlines()))

    @staticmethod
    def region_hash(lines: Sequence[str], start_line: int, end_line: int) -> str:
        region = "" if end_line < start_line else "".join(lines[start_line - 1:end_line])
        return digest(region.encode("utf-8"))

    @staticmethod
    def make_patch(original_text: str, *, start_line: int, end_line: int, replacement_text: str) -> LinePatch:
        lines = original_text.splitlines(keepends=True)
        if start_line < 1 or end_line < start_line - 1 or end_line > len(lines):
            raise ValueError("invalid patch range")
        replacement = tuple(replacement_text.splitlines(keepends=True))
        if replacement_text and not replacement:
            replacement = (replacement_text,)
        return LinePatch(
            start_line,
            end_line,
            replacement,
            ArtifactDeltaEngine.region_hash(lines, start_line, end_line),
        )

    @staticmethod
    def apply(path: str | Path, patch: LinePatch) -> PatchResult:
        p = Path(path)
        raw = p.read_bytes()
        before = ArtifactSnapshot(str(p), digest(raw), len(raw), len(raw.decode("utf-8").splitlines()))
        text = raw.decode("utf-8")
        lines = text.splitlines(keepends=True)
        actual = ArtifactDeltaEngine.region_hash(lines, patch.start_line, patch.end_line)
        if actual != patch.expected_before_hash:
            raise RuntimeError("artifact changed since patch was planned; refusing destructive rewrite")

        prefix = lines[: patch.start_line - 1]
        suffix = lines[patch.end_line:] if patch.end_line >= patch.start_line else lines[patch.start_line - 1:]
        new_lines = prefix + list(patch.replacement) + suffix
        new_text = "".join(new_lines)
        p.write_text(new_text, encoding="utf-8", newline="")
        new_raw = p.read_bytes()
        after = ArtifactSnapshot(str(p), digest(new_raw), len(new_raw), len(new_text.splitlines()))
        return PatchResult(
            before,
            after,
            max(0, patch.end_line - patch.start_line + 1),
            len(patch.replacement),
            len(prefix),
            len(suffix),
        )
