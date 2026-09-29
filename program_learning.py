from __future__ import annotations
"""Promote a verified formula into structural memory + executable program store."""
from dataclasses import dataclass
from typing import Mapping, Sequence
from formula_compiler import FormulaCompiler
from program_store import ProgramStore
from structural_memory import MethodMemory, StructuralMemory

@dataclass(frozen=True)
class Example:
    inputs:Mapping[str,float]
    expected:float

@dataclass(frozen=True)
class LearnedProgram:
    method:MethodMemory
    max_abs_error:float
    examples:int

def learn_verified_formula(*,memory:StructuralMemory,programs:ProgramStore,method_id:str,domain:str,structure_signature:str,expression:str,inputs:Sequence[str],examples:Sequence[Example],tolerance:float=1e-9)->LearnedProgram:
    if not examples: raise ValueError('at least one verification example is required')
    program=FormulaCompiler(inputs).compile(expression).program
    max_error=0.0
    for ex in examples:
        got=program.execute(ex.inputs); err=abs(got-float(ex.expected)); max_error=max(max_error,err)
        if err>tolerance: raise ValueError(f'verification failed: expected {ex.expected}, got {got}')
    existing=memory.methods.get(method_id)
    if existing is None:
        method=MethodMemory(method_id,domain,structure_signature,tuple(int(i.op) for i in program.code),confidence=0.5,verified_runs=0,failures=0,provenance='verified-formula')
        memory.register_method(method)
    else: method=existing
    for _ in examples: memory.record_method_outcome(method_id,True)
    programs.put(method_id,program)
    return LearnedProgram(method,max_error,len(examples))
