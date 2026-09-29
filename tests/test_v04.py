from pathlib import Path

from numeric_codec import NumericKnowledgeCodec
from structural_memory import MethodMemory, StructuralMemory
from artifact_delta import ArtifactDeltaEngine


def test_numeric_codec_roundtrip_complex_json():
    obj = {
        "language": "TypeScript",
        "rules": [
            {"op": "add", "cost": 1, "verified": True},
            {"op": "guard", "cost": -2, "verified": False},
        ],
        "nullable": None,
        "ratio": 0.125,
        "same": "TypeScript",
    }
    codec = NumericKnowledgeCodec()
    enc = codec.encode(obj)
    assert codec.decode(enc) == obj


def test_method_memory_learns_confidence_from_execution():
    mem = StructuralMemory()
    m = MethodMemory("m1", "code", "sig:function:add", (1, 2, 9))
    mem.register_method(m)
    for _ in range(9):
        mem.record_method_outcome("m1", True)
    mem.record_method_outcome("m1", False)
    assert 0.8 < mem.methods["m1"].confidence < 1.0


def test_error_exact_and_variant_are_remembered():
    mem = StructuralMemory()
    mem.learn_error(
        domain="code",
        exact_parts=["division", "b=0", "no_guard"],
        variant_parts=["division", "denominator_zero", "missing_guard"],
        detector=["denominator == 0"],
        correction_method_id="guard_zero",
    )
    assert mem.match_error(
        ["division", "b=0", "no_guard"],
        ["division", "denominator_zero", "missing_guard"],
    ) is not None
    assert mem.match_error(
        ["division", "input2=0", "unguarded"],
        ["division", "denominator_zero", "missing_guard"],
    ) is not None


def test_only_high_confidence_verified_results_are_saved():
    mem = StructuralMemory(result_threshold=0.98, min_result_verifications=2)
    assert not mem.maybe_save_result(
        request_parts=["2+2"], method_id="add", result="4", confidence=0.97, verified_runs=10
    )
    assert not mem.maybe_save_result(
        request_parts=["2+2"], method_id="add", result="4", confidence=0.999, verified_runs=1
    )
    assert mem.maybe_save_result(
        request_parts=["2+2"], method_id="add", result="4", confidence=0.999, verified_runs=3
    )
    assert mem.exact_result(["2+2"]).result == "4"


def test_memory_roundtrip():
    mem = StructuralMemory()
    mem.register_method(MethodMemory("m", "math", "addition", (1,), confidence=0.9, verified_runs=10))
    mem.learn_error(
        domain="math",
        exact_parts=["x"],
        variant_parts=["class-x"],
        detector=["d"],
        correction_method_id="m",
    )
    mem.maybe_save_result(
        request_parts=["same"], method_id="m", result="ok", confidence=0.999, verified_runs=3
    )
    restored = StructuralMemory.from_json(mem.to_json())
    assert restored.methods["m"].op_ids == (1,)
    assert restored.exact_result(["same"]).result == "ok"
    assert restored.match_error(["other"], ["class-x"]) is not None


def test_artifact_delta_preserves_unmodified_content(tmp_path: Path):
    p = tmp_path / "app.py"
    original = "A = 1\n\ndef old():\n    return 1\n\nTAIL = 9\n"
    p.write_text(original, encoding="utf-8")
    patch = ArtifactDeltaEngine.make_patch(
        original,
        start_line=3,
        end_line=4,
        replacement_text="def old():\n    return 2\n\ndef extra():\n    return 3\n",
    )
    result = ArtifactDeltaEngine.apply(p, patch)
    text = p.read_text(encoding="utf-8")
    assert text.startswith("A = 1\n\n")
    assert text.endswith("\nTAIL = 9\n")
    assert "return 2" in text and "def extra" in text
    assert result.preserved_prefix_lines == 2
    assert result.preserved_suffix_lines == 2


def test_artifact_delta_rejects_stale_patch(tmp_path: Path):
    p = tmp_path / "a.txt"
    original = "one\ntwo\nthree\n"
    p.write_text(original, encoding="utf-8")
    patch = ArtifactDeltaEngine.make_patch(original, start_line=2, end_line=2, replacement_text="TWO\n")
    p.write_text("one\nchanged\nthree\n", encoding="utf-8")
    try:
        ArtifactDeltaEngine.apply(p, patch)
    except RuntimeError:
        pass
    else:
        raise AssertionError("stale patch should have been rejected")
