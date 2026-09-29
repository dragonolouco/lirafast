from __future__ import annotations
"""Integration layer: exact-result fast path -> structural method/error path -> DEEP fallback."""
from dataclasses import dataclass
from typing import Sequence
from semantic_compiler import CompileResult, SemanticCompiler, norm_text
from structural_memory import StructuralMemory
from learning import DeepToFastPromoter

@dataclass(frozen=True)
class RouteDecision:
    mode:str
    compiled:CompileResult|None
    payload:object|None
    domain:str

class LiraFastRuntime:
    def __init__(self,memory:StructuralMemory|None=None,compiler:SemanticCompiler|None=None)->None:
        self.memory=memory or StructuralMemory(); self.compiler=compiler or SemanticCompiler(); self.promoter=DeepToFastPromoter(self.memory)
    @staticmethod
    def _domain(c:CompileResult,requested:str)->str:
        if requested!='general':return requested
        domains=[p.split(':',1)[1] for p in c.primitives if p.startswith('domain:')]
        return domains[0] if domains else 'general'
    def route(self,text:str,*,domain:str='general',exact_error_parts:Sequence[str]=(),variant_error_parts:Sequence[str]=())->RouteDecision:
        normalized=norm_text(text); result=self.memory.exact_result((normalized,))
        if result:return RouteDecision('RESULT',None,result,domain)
        c=self.compiler.compile(normalized); resolved=self._domain(c,domain)
        if exact_error_parts or variant_error_parts:
            g=self.memory.match_error(exact_error_parts,variant_error_parts)
            if g:return RouteDecision('GUARDED',c,g,resolved)
        m=self.memory.best_method(c.signature,resolved)
        if m:return RouteDecision('METHOD',c,m,resolved)
        return RouteDecision('DEEP',c,None,resolved)
    def save_verified_result(self,text:str,*,domain:str='general',result:str,confidence:float,verified_runs:int)->bool:
        c=self.compiler.compile(text); resolved=self._domain(c,domain); method=self.memory.best_method(c.signature,resolved)
        if method is None:return False
        return self.memory.maybe_save_result(request_parts=(c.normalized,),method_id=method.method_id,result=result,confidence=confidence,verified_runs=verified_runs)
