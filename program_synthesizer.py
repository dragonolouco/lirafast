from __future__ import annotations
"""Small enumerative synthesizer for arithmetic structural methods.

This is intentionally bounded research code, not a general program synthesizer.
It demonstrates the DEEP-path idea: explore candidate structures, collapse
behaviorally equivalent candidates, verify, then promote only the survivor.
"""
from dataclasses import dataclass
import math
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple
from formula_compiler import FormulaCompiler
from numeric_vm import NumericProgram

@dataclass(frozen=True)
class SynthesisExample:
    inputs: Mapping[str,float]
    expected: float

@dataclass(frozen=True)
class Synthesized:
    expression: str
    program: NumericProgram
    depth: int
    candidates_evaluated: int
    unique_behaviors: int

@dataclass(frozen=True)
class _Expr:
    text: str
    depth: int

_COMMUTATIVE={"+","*"}

def _safe_eval(program:NumericProgram, examples:Sequence[SynthesisExample])->Tuple[float,...]|None:
    out=[]
    try:
        for ex in examples:
            v=program.execute(ex.inputs)
            if not math.isfinite(v) or abs(v)>1e15:return None
            out.append(round(float(v),12))
    except Exception:
        return None
    return tuple(out)

def _target(examples:Sequence[SynthesisExample])->Tuple[float,...]:
    return tuple(round(float(e.expected),12) for e in examples)

def synthesize_formula(*,inputs:Sequence[str],examples:Sequence[SynthesisExample],constants:Sequence[float]=(-1,0,1,2),ops:Sequence[str]=("+","-","*","/"),max_depth:int=2,max_unique:int=50_000)->Synthesized|None:
    if not examples:raise ValueError("examples required")
    compiler=FormulaCompiler(tuple(inputs)); target=_target(examples)
    atoms=[_Expr(name,0) for name in inputs]+[_Expr(repr(float(c)),0) for c in constants]
    behavior_to_expr:Dict[Tuple[float,...],_Expr]={}
    pool:List[_Expr]=[]
    evaluated=0

    def consider(expr:_Expr)->Synthesized|None:
        nonlocal evaluated
        try:p=compiler.compile(expr.text).program
        except Exception:return None
        evaluated+=1; behavior=_safe_eval(p,examples)
        if behavior is None:return None
        if behavior==target:return Synthesized(expr.text,p,expr.depth,evaluated,len(behavior_to_expr)+1)
        if behavior not in behavior_to_expr and len(behavior_to_expr)<max_unique:
            behavior_to_expr[behavior]=expr; pool.append(expr)
        return None

    for atom in atoms:
        found=consider(atom)
        if found:return found

    start=0
    for depth in range(1,max_depth+1):
        base=list(pool)
        lefts=[e for e in base if e.depth<=depth-1]
        rights=lefts
        before=len(pool)
        for a in lefts:
            for b in rights:
                if max(a.depth,b.depth)!=depth-1:continue
                for op in ops:
                    if op in _COMMUTATIVE and a.text>b.text:continue
                    expr=_Expr(f"({a.text}{op}{b.text})",depth)
                    found=consider(expr)
                    if found:return found
                    if len(behavior_to_expr)>=max_unique:return None
        if len(pool)==before:break
        start=before
    return None
