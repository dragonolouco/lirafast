from __future__ import annotations
"""Single-file .lirafast v0.5 container with section table and checksums."""
from dataclasses import dataclass
import json, struct, zlib
from pathlib import Path
from typing import Dict, Mapping

MAGIC=b'LIRAFST5'; VERSION=5
HEADER=struct.Struct('<8sHHI')
ENTRY=struct.Struct('<16sQQII')
FLAG_ZLIB=1

@dataclass(frozen=True)
class SectionInfo:
    name:str; offset:int; stored_size:int; crc32:int; flags:int

class LiraFastContainer:
    @staticmethod
    def pack(sections:Mapping[str,bytes],*,compress:bool=True)->bytes:
        rows=[]; payloads=[]; count=len(sections); directory_bytes=count*ENTRY.size
        offset=HEADER.size+directory_bytes
        for name,raw in sections.items():
            if len(name.encode('ascii'))>16: raise ValueError('section name max 16 ASCII bytes')
            stored=zlib.compress(raw,6) if compress and len(raw)>64 else raw; flags=FLAG_ZLIB if stored is not raw else 0
            if flags and len(stored)>=len(raw): stored=raw; flags=0
            crc=zlib.crc32(raw)&0xffffffff; rows.append((name,offset,len(stored),crc,flags)); payloads.append(stored); offset+=len(stored)
        out=bytearray(HEADER.pack(MAGIC,VERSION,count,directory_bytes))
        for name,off,size,crc,flags in rows: out.extend(ENTRY.pack(name.encode('ascii').ljust(16,b'\0'),off,size,crc,flags))
        for p in payloads: out.extend(p)
        return bytes(out)
    @staticmethod
    def unpack(blob:bytes)->Dict[str,bytes]:
        if len(blob)<HEADER.size: raise ValueError('truncated header')
        magic,ver,count,db=HEADER.unpack_from(blob,0)
        if magic!=MAGIC or ver!=VERSION or db!=count*ENTRY.size: raise ValueError('invalid container')
        out={}; pos=HEADER.size
        for _ in range(count):
            raw_name,off,size,crc,flags=ENTRY.unpack_from(blob,pos); pos+=ENTRY.size; name=raw_name.rstrip(b'\0').decode('ascii')
            if off+size>len(blob): raise ValueError('section outside container')
            stored=blob[off:off+size]; raw=zlib.decompress(stored) if flags&FLAG_ZLIB else stored
            if zlib.crc32(raw)&0xffffffff!=crc: raise ValueError(f'crc mismatch: {name}')
            out[name]=raw
        return out
    @staticmethod
    def from_memory_json(memory_json:str,meta:Mapping[str,object]|None=None)->bytes:
        return LiraFastContainer.pack({'memory':memory_json.encode('utf-8'),'meta':json.dumps(dict(meta or {}),ensure_ascii=False,separators=(',',':')).encode('utf-8')})
    @staticmethod
    def write(path:str|Path,sections:Mapping[str,bytes])->None:Path(path).write_bytes(LiraFastContainer.pack(sections))
    @staticmethod
    def read(path:str|Path)->Dict[str,bytes]:return LiraFastContainer.unpack(Path(path).read_bytes())
