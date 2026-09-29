from __future__ import annotations
"""DEEP -> FAST promotion and error consolidation."""
from dataclasses import dataclass
from typing import Dict, Sequence, Tuple
from structural_memory import MethodMemory, StructuralMemory

@dataclass
class TraceStats:
    domain:str; structure_signature:str; op_ids:Tuple[int,...]; preconditions:Tuple[str,...]; postconditions:Tuple[str,...]
    successes:int=0; failures:int=0; method_id:str|None=None
    @property
    def confidence(self)->float:return (1+self.successes)/(2+self.successes+self.failures)

class DeepToFastPromoter:
    def __init__(self,memory:StructuralMemory,*,min_successes:int=3,min_confidence:float=.8)->None:
        self.memory=memory; self.min_successes=min_successes; self.min_confidence=min_confidence; self.traces:Dict[Tuple[str,str],TraceStats]={}
    def observe_success(self,*,domain:str,structure_signature:str,op_ids:Sequence[int],preconditions:Sequence[str]=(),postconditions:Sequence[str]=())->MethodMemory|None:
        key=(domain,structure_signature); t=self.traces.get(key)
        if t is None:
            t=TraceStats(domain,structure_signature,tuple(op_ids),tuple(preconditions),tuple(postconditions)); self.traces[key]=t
        elif t.op_ids!=tuple(op_ids):
            variant=f'{structure_signature}:{hash(tuple(op_ids)) & 0xffffffff:08x}'
            key=(domain,variant); t=self.traces.get(key)
            if t is None:
                t=TraceStats(domain,structure_signature,tuple(op_ids),tuple(preconditions),tuple(postconditions)); self.traces[key]=t
        t.successes+=1
        if t.successes>=self.min_successes and t.confidence>=self.min_confidence:
            mid=t.method_id or f'auto:{domain}:{structure_signature[:12]}:{abs(hash(t.op_ids)) & 0xffff:04x}'; t.method_id=mid
            m=self.memory.methods.get(mid)
            if m is None:
                m=MethodMemory(mid,domain,structure_signature,t.op_ids,t.preconditions,t.postconditions,t.confidence,t.successes,t.failures,'deep-to-fast')
                self.memory.register_method(m)
            else:
                m.verified_runs=t.successes; m.failures=t.failures; m.confidence=t.confidence
            return m
        return None
    def observe_failure(self,*,domain:str,structure_signature:str,exact_parts:Sequence[str],variant_parts:Sequence[str],detector:Sequence[str],correction_method_id:str|None=None)->None:
        for (d,sig),t in self.traces.items():
            if d==domain and t.structure_signature==structure_signature: t.failures+=1
        self.memory.learn_error(domain=domain,exact_parts=exact_parts,variant_parts=variant_parts,detector=detector,correction_method_id=correction_method_id)
