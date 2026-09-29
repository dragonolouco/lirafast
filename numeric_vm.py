from __future__ import annotations
"""Compact numeric stack VM for executable LiraFast methods.

The VM is deterministic and deliberately small. A learned method is encoded as
numeric opcodes, validated as a control-flow graph, persisted, audited, decoded
and executed with new inputs without regenerating source code.
"""
from dataclasses import dataclass
from enum import IntEnum
import math
import struct
from typing import Mapping, Sequence, Tuple

MAGIC=b"LFVM6"
VERSION=2
HEADER=struct.Struct("<5sBHHH")
INS=struct.Struct("<BH")

class Op(IntEnum):
    LOAD_INPUT=1
    LOAD_CONST=2
    ADD=10
    SUB=11
    MUL=12
    DIV=13
    MOD=14
    POW=15
    NEG=16
    ABS=17
    MIN=18
    MAX=19
    EQ=30
    NE=31
    LT=32
    LE=33
    GT=34
    GE=35
    SELECT=40
    JUMP_IF_FALSE=41
    JUMP=42
    RETURN=255

@dataclass(frozen=True)
class Instruction:
    op: Op
    arg: int=0

@dataclass(frozen=True)
class NumericProgram:
    inputs: Tuple[str,...]
    constants: Tuple[float,...]
    code: Tuple[Instruction,...]

    def validate(self)->int:
        if not self.code: raise ValueError("empty program")
        binary={Op.ADD,Op.SUB,Op.MUL,Op.DIV,Op.MOD,Op.POW,Op.MIN,Op.MAX,Op.EQ,Op.NE,Op.LT,Op.LE,Op.GT,Op.GE}
        unary={Op.NEG,Op.ABS}
        seen_depth:dict[int,int]={}
        work=[(0,0)]
        peak=0
        returns=0
        while work:
            pc,depth=work.pop()
            if pc<0 or pc>=len(self.code): raise ValueError(f"jump outside program: {pc}")
            old=seen_depth.get(pc)
            if old is not None:
                if old!=depth: raise ValueError(f"inconsistent stack depth at {pc}: {old} vs {depth}")
                continue
            seen_depth[pc]=depth
            ins=self.code[pc]; op=ins.op
            if op==Op.LOAD_INPUT:
                if ins.arg>=len(self.inputs): raise ValueError(f"bad input index at {pc}")
                nd=depth+1; nxt=[pc+1]
            elif op==Op.LOAD_CONST:
                if ins.arg>=len(self.constants): raise ValueError(f"bad constant index at {pc}")
                nd=depth+1; nxt=[pc+1]
            elif op in binary:
                if depth<2: raise ValueError(f"stack underflow at {pc}")
                nd=depth-1; nxt=[pc+1]
            elif op in unary:
                if depth<1: raise ValueError(f"stack underflow at {pc}")
                nd=depth; nxt=[pc+1]
            elif op==Op.SELECT:
                if depth<3: raise ValueError(f"stack underflow at {pc}")
                nd=depth-2; nxt=[pc+1]
            elif op==Op.JUMP_IF_FALSE:
                if depth<1: raise ValueError(f"stack underflow at {pc}")
                if ins.arg>=len(self.code): raise ValueError(f"bad branch target at {pc}")
                nd=depth-1; nxt=[pc+1,ins.arg]
            elif op==Op.JUMP:
                if ins.arg>=len(self.code): raise ValueError(f"bad jump target at {pc}")
                nd=depth; nxt=[ins.arg]
            elif op==Op.RETURN:
                if depth!=1: raise ValueError(f"RETURN requires one value, got {depth}")
                returns+=1; peak=max(peak,depth); continue
            else:
                raise ValueError(f"unknown opcode {ins.op}")
            peak=max(peak,nd)
            for target in nxt:
                if target>=len(self.code): raise ValueError(f"fallthrough outside program from {pc}")
                work.append((target,nd))
        if returns==0: raise ValueError("program has no reachable RETURN")
        return peak

    def execute(self, values: Mapping[str,float]|Sequence[float])->float:
        self.validate()
        if isinstance(values,Mapping):
            argv=[float(values[name]) for name in self.inputs]
        else:
            if len(values)!=len(self.inputs): raise ValueError("wrong input count")
            argv=[float(x) for x in values]
        s:list[float]=[]; pc=0; steps=0; max_steps=max(32,len(self.code)*8)
        while True:
            if pc<0 or pc>=len(self.code): raise RuntimeError("program counter outside code")
            steps+=1
            if steps>max_steps: raise RuntimeError("instruction budget exceeded")
            ins=self.code[pc]; op=ins.op
            if op==Op.LOAD_INPUT:s.append(argv[ins.arg]); pc+=1
            elif op==Op.LOAD_CONST:s.append(self.constants[ins.arg]); pc+=1
            elif op==Op.NEG:s[-1]=-s[-1]; pc+=1
            elif op==Op.ABS:s[-1]=abs(s[-1]); pc+=1
            elif op==Op.RETURN:return s[-1]
            elif op==Op.SELECT:
                false=s.pop(); true=s.pop(); cond=s.pop(); s.append(true if cond else false); pc+=1
            elif op==Op.JUMP_IF_FALSE:
                cond=s.pop(); pc=pc+1 if cond else ins.arg
            elif op==Op.JUMP:
                pc=ins.arg
            else:
                b=s.pop(); a=s.pop()
                if op==Op.ADD:r=a+b
                elif op==Op.SUB:r=a-b
                elif op==Op.MUL:r=a*b
                elif op==Op.DIV:r=a/b
                elif op==Op.MOD:r=a%b
                elif op==Op.POW:r=math.pow(a,b)
                elif op==Op.MIN:r=min(a,b)
                elif op==Op.MAX:r=max(a,b)
                elif op==Op.EQ:r=float(a==b)
                elif op==Op.NE:r=float(a!=b)
                elif op==Op.LT:r=float(a<b)
                elif op==Op.LE:r=float(a<=b)
                elif op==Op.GT:r=float(a>b)
                elif op==Op.GE:r=float(a>=b)
                else:raise ValueError(f"unsupported opcode {op}")
                if not math.isfinite(r): raise ArithmeticError("non-finite numeric result")
                s.append(float(r)); pc+=1

    def to_bytes(self)->bytes:
        self.validate()
        out=bytearray(HEADER.pack(MAGIC,VERSION,len(self.inputs),len(self.constants),len(self.code)))
        for name in self.inputs:
            raw=name.encode("utf-8")
            if len(raw)>255: raise ValueError("input name too long")
            out.append(len(raw)); out.extend(raw)
        for c in self.constants: out.extend(struct.pack("<d",float(c)))
        for ins in self.code: out.extend(INS.pack(int(ins.op),ins.arg))
        return bytes(out)

    @classmethod
    def from_bytes(cls,blob:bytes)->"NumericProgram":
        if len(blob)<HEADER.size: raise ValueError("truncated VM header")
        magic,version,n_inputs,n_consts,n_code=HEADER.unpack_from(blob,0)
        if magic!=MAGIC or version!=VERSION: raise ValueError("invalid VM format")
        pos=HEADER.size; names=[]
        for _ in range(n_inputs):
            if pos>=len(blob): raise ValueError("truncated input name")
            n=blob[pos]; pos+=1
            if pos+n>len(blob): raise ValueError("truncated input name")
            names.append(blob[pos:pos+n].decode("utf-8")); pos+=n
        constants=[]
        for _ in range(n_consts):
            if pos+8>len(blob): raise ValueError("truncated constant")
            constants.append(struct.unpack_from("<d",blob,pos)[0]); pos+=8
        code=[]
        for _ in range(n_code):
            if pos+INS.size>len(blob): raise ValueError("truncated instruction")
            op,arg=INS.unpack_from(blob,pos); pos+=INS.size
            try: opcode=Op(op)
            except ValueError as exc: raise ValueError(f"unknown opcode {op}") from exc
            code.append(Instruction(opcode,arg))
        if pos!=len(blob): raise ValueError("trailing VM bytes")
        p=cls(tuple(names),tuple(constants),tuple(code)); p.validate(); return p
