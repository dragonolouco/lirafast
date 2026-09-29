from __future__ import annotations
"""Compact method_id -> executable program store."""
from dataclasses import dataclass
import struct
from typing import Dict, Iterator
from numeric_vm import NumericProgram

MAGIC=b"LFPS6"; VERSION=1
HEADER=struct.Struct("<5sBI")

@dataclass(frozen=True)
class StoredProgram:
    method_id:str
    program:NumericProgram

class ProgramStore:
    def __init__(self)->None:self._programs:Dict[str,NumericProgram]={}
    def put(self,method_id:str,program:NumericProgram)->None:
        if not method_id: raise ValueError("empty method id")
        program.validate(); self._programs[method_id]=program
    def get(self,method_id:str)->NumericProgram|None:return self._programs.get(method_id)
    def __len__(self)->int:return len(self._programs)
    def items(self)->Iterator[StoredProgram]:
        for k,v in self._programs.items():yield StoredProgram(k,v)
    def to_bytes(self)->bytes:
        out=bytearray(HEADER.pack(MAGIC,VERSION,len(self._programs)))
        for method_id,program in sorted(self._programs.items()):
            name=method_id.encode("utf-8"); blob=program.to_bytes()
            if len(name)>65535: raise ValueError("method id too long")
            out.extend(struct.pack("<HI",len(name),len(blob))); out.extend(name); out.extend(blob)
        return bytes(out)
    @classmethod
    def from_bytes(cls,blob:bytes)->"ProgramStore":
        if len(blob)<HEADER.size: raise ValueError("truncated program store")
        magic,version,count=HEADER.unpack_from(blob,0)
        if magic!=MAGIC or version!=VERSION: raise ValueError("invalid program store")
        pos=HEADER.size; out=cls()
        for _ in range(count):
            if pos+6>len(blob): raise ValueError("truncated program entry")
            n_name,n_blob=struct.unpack_from("<HI",blob,pos); pos+=6
            if pos+n_name+n_blob>len(blob): raise ValueError("truncated program payload")
            method_id=blob[pos:pos+n_name].decode("utf-8"); pos+=n_name
            program=NumericProgram.from_bytes(blob[pos:pos+n_blob]); pos+=n_blob; out.put(method_id,program)
        if pos!=len(blob): raise ValueError("trailing program-store bytes")
        return out
