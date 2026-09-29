from __future__ import annotations
"""Discover -> verify -> persist an arithmetic method."""
from dataclasses import dataclass
from typing import Sequence
from program_learning import Example, LearnedProgram, learn_verified_formula
from program_store import ProgramStore
from program_synthesizer import SynthesisExample, Synthesized, synthesize_formula
from structural_memory import StructuralMemory

@dataclass(frozen=True)
class AutoLearnResult:
    synthesized:Synthesized
    learned:LearnedProgram

def discover_and_learn(*,memory:StructuralMemory,programs:ProgramStore,method_id:str,domain:str,structure_signature:str,inputs:Sequence[str],examples:Sequence[Example],max_depth:int=2)->AutoLearnResult|None:
    syn_examples=[SynthesisExample(e.inputs,e.expected) for e in examples]
    syn=synthesize_formula(inputs=inputs,examples=syn_examples,max_depth=max_depth)
    if syn is None:return None
    learned=learn_verified_formula(memory=memory,programs=programs,method_id=method_id,domain=domain,structure_signature=structure_signature,expression=syn.expression,inputs=inputs,examples=examples)
    return AutoLearnResult(syn,learned)
