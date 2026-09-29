from __future__ import annotations
"""Runtime that executes verified structural methods directly as numeric programs."""
from dataclasses import dataclass
from typing import Mapping, Sequence
from runtime_v05 import LiraFastRuntime, RouteDecision
from program_store import ProgramStore

@dataclass(frozen=True)
class ExecutionResult:
    mode:str
    value:float|str|None
    method_id:str|None
    routed:RouteDecision

class ExecutableRuntime(LiraFastRuntime):
    def __init__(self,*args,programs:ProgramStore|None=None,**kwargs)->None:
        super().__init__(*args,**kwargs); self.programs=programs or ProgramStore()
    def execute(self,text:str,inputs:Mapping[str,float]|Sequence[float],*,domain:str='general',exact_error_parts=(),variant_error_parts=())->ExecutionResult:
        d=self.route(text,domain=domain,exact_error_parts=exact_error_parts,variant_error_parts=variant_error_parts)
        if d.mode=='RESULT':
            return ExecutionResult('RESULT',d.payload.result,getattr(d.payload,'method_id',None),d)
        if d.mode=='METHOD':
            method=d.payload; program=self.programs.get(method.method_id)
            if program is None:return ExecutionResult('METHOD_NO_PROGRAM',None,method.method_id,d)
            try:value=program.execute(inputs)
            except Exception:
                self.memory.record_method_outcome(method.method_id,False); raise
            self.memory.record_method_outcome(method.method_id,True)
            return ExecutionResult('METHOD',value,method.method_id,d)
        return ExecutionResult(d.mode,None,getattr(d.payload,'method_id',None),d)
