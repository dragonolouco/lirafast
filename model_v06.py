from __future__ import annotations
"""Persistence facade for a runnable LiraFast v0.6 model."""
import json
from pathlib import Path
from typing import Mapping
from container_v05 import LiraFastContainer
from program_store import ProgramStore
from structural_memory import StructuralMemory

class LiraFastModel:
    @staticmethod
    def save(path:str|Path,memory:StructuralMemory,programs:ProgramStore,*,meta:Mapping[str,object]|None=None)->None:
        info={"model_version":6,"format":"lirafast","executable_programs":len(programs)}
        info.update(dict(meta or {}))
        sections={
            "memory":memory.to_json().encode("utf-8"),
            "programs":programs.to_bytes(),
            "meta":json.dumps(info,ensure_ascii=False,separators=(",",":"),sort_keys=True).encode("utf-8"),
        }
        LiraFastContainer.write(path,sections)
    @staticmethod
    def load(path:str|Path)->tuple[StructuralMemory,ProgramStore,dict]:
        s=LiraFastContainer.read(path)
        for required in ("memory","programs","meta"):
            if required not in s: raise ValueError(f"missing section {required}")
        memory=StructuralMemory.from_json(s["memory"].decode("utf-8"))
        programs=ProgramStore.from_bytes(s["programs"])
        meta=json.loads(s["meta"].decode("utf-8"))
        if meta.get("model_version")!=6: raise ValueError("not a v0.6 model")
        return memory,programs,meta
