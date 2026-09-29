from __future__ import annotations
"""Cheap structural compiler: language -> finite primitives -> reusable signature.

This component intentionally extracts only enough structure to route execution.
Unknown content is retained as unknown rather than guessed. A later/deeper path can
resolve it and feed a verified structure back into memory.
"""
from dataclasses import dataclass
from hashlib import blake2b
import re
import unicodedata
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple
from collections import OrderedDict

_TOKEN_RE=re.compile(r"[\w.+#-]+|[^\w\s]",re.UNICODE)
_NEGATORS={'não','nao','sem','nunca','jamais','nem','nenhum','nenhuma'}

def _suppress_when_negated(concept:str)->bool:
    return concept.startswith('action:') or concept.startswith('intent:') or concept.startswith('op:')

def _negated_before(text:str,start:int)->bool:
    prefix=text[:start].rstrip()
    words=re.findall(r'[\wÀ-ÿ]+',prefix[-48:])
    return any(w in _NEGATORS for w in words[-3:])

def norm_text(text:str)->str:
    text=unicodedata.normalize('NFKC',text).lower().strip()
    return ' '.join(text.split())

def stable_structure(parts:Iterable[str])->str:
    h=blake2b(digest_size=16)
    for p in sorted(set(parts)):
        b=p.encode('utf-8'); h.update(len(b).to_bytes(2,'little')); h.update(b)
    return h.hexdigest()

@dataclass(frozen=True)
class CompileResult:
    normalized:str
    primitives:Tuple[str,...]
    unknown:Tuple[str,...]
    signature:str
    confidence:float
    @property
    def exact_request_parts(self)->Tuple[str,...]:
        return (self.normalized,)

class SemanticCompiler:
    DEFAULT_ALIASES:Mapping[str,Tuple[str,...]]={
      'intent:create':('criar','crie','faça','fazer','gere','gerar','create','build','make'),
      'intent:edit':('editar','edite','alterar','altere','modificar','modifique','expandir','expanda','update','edit','modify'),
      'artifact:file':('arquivo','file'),
      'artifact:function':('função','funcao','function','método','metodo'),
      'artifact:class':('classe','class'),
      'lang:python':('python','.py'), 'lang:typescript':('typescript','.ts','tsx'), 'lang:java':('java','.java'),
      'op:add':('somar','soma','adicionar','add','sum','+'), 'op:subtract':('subtrair','subtração','subtracao','subtract','-'),
      'op:multiply':('multiplicar','multiplicação','multiplicacao','multiply','*'), 'op:divide':('dividir','divisão','divisao','divide','/'),
      'verify:test':('testar','teste','tests','test'), 'verify:compile':('compilar','compile'),
      'constraint:preserve':('preservar','preserve','manter','não mudar','nao mudar','sem reescrever','continue','continuar'),
      'error:fix':('corrigir','consertar','fix','erro','error'),
    }
    STOP={'o','a','os','as','um','uma','de','da','do','dos','das','e','em','no','na','nos','nas','que','para','por','com','the','an','to','of','and','in','on','for','with'}
    def __init__(self,aliases:Mapping[str,Sequence[str]]|None=None,*,cache_limit:int=4096)->None:
        src=dict(self.DEFAULT_ALIASES)
        if aliases:
            for k,v in aliases.items(): src[k]=tuple(v)
        self.aliases={k:tuple(norm_text(x) for x in v) for k,v in src.items()}
        self.cache_limit=max(0,cache_limit); self._cache:OrderedDict[str,CompileResult]=OrderedDict()
        self.single:Dict[str,List[str]]={}; self.multi:List[Tuple[str,str]]=[]
        for concept,vals in self.aliases.items():
            for v in vals:
                if ' ' in v:self.multi.append((v,concept))
                else:self.single.setdefault(v,[]).append(concept)
        self.multi.sort(key=lambda x:len(x[0]),reverse=True)
    def compile(self,text:str)->CompileResult:
        n=norm_text(text)
        cached=self._cache.get(n)
        if cached is not None:
            self._cache.move_to_end(n); return cached
        found=set(); covered=set()
        for phrase,concept in self.multi:
            start=0
            while True:
                idx=n.find(phrase,start)
                if idx<0:break
                if not (_suppress_when_negated(concept) and _negated_before(n,idx)):
                    found.add(concept); covered.update(phrase.split())
                start=idx+max(1,len(phrase))
        matches=list(_TOKEN_RE.finditer(n)); unknown=[]
        for m in matches:
            t=m.group(0); cs=self.single.get(t)
            if cs:
                for concept in cs:
                    if not (_suppress_when_negated(concept) and _negated_before(n,m.start())): found.add(concept)
                covered.add(t)
            elif t.isalnum() and len(t)>2 and t not in self.STOP and t not in covered:
                unknown.append(t)
        primitives=tuple(sorted(found)); unk=tuple(dict.fromkeys(unknown))
        known=max(1,len(primitives)); conf=known/(known+0.35*len(unk))
        result=CompileResult(n,primitives,unk,stable_structure(primitives),min(1.0,conf))
        if self.cache_limit:
            self._cache[n]=result; self._cache.move_to_end(n)
            while len(self._cache)>self.cache_limit:self._cache.popitem(last=False)
        return result
