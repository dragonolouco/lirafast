from __future__ import annotations
"""Translate structured knowledge files into aliases/primitives for the fast compiler.

The loader is deliberately schema-aware instead of recursively treating every string as
knowledge. It extracts only routing-grade cues.
"""
import json
from pathlib import Path
from typing import Dict, Iterable, Mapping, MutableMapping, Sequence

def _add(dst:MutableMapping[str,set[str]], concept:str, values:Iterable[object])->None:
    bucket=dst.setdefault(concept,set())
    for v in values:
        if isinstance(v,str) and v.strip(): bucket.add(v.strip())

def aliases_from_document(doc:Mapping[str,object], *, include_lexical:bool=False)->Dict[str,tuple[str,...]]:
    out:Dict[str,set[str]]={}
    fmt=doc.get('format_id')
    if isinstance(fmt,str) and fmt and fmt not in {'global_interpretation'}:
        concept=f'lang:{fmt.lower()}'; vals=[]
        for key in ('aliases','extensions'):
            v=doc.get(key)
            if isinstance(v,list): vals.extend(v)
        lang=doc.get('language')
        if isinstance(lang,str): vals.append(lang)
        _add(out,concept,vals)
    signal_roles=doc.get('signal_roles')
    if isinstance(signal_roles,dict):
        for _,group in signal_roles.items():
            rows=group if isinstance(group,list) else [group] if isinstance(group,dict) else []
            for row in rows:
                if not isinstance(row,dict): continue
                concept=row.get('interpret_as') or row.get('id'); cues=row.get('cues')
                if isinstance(concept,str) and isinstance(cues,list): _add(out,concept,cues)
    routing=doc.get('domain_routing')
    if isinstance(routing,dict):
        domains=routing.get('domains')
        if isinstance(domains,list):
            for row in domains:
                if not isinstance(row,dict): continue
                rid=row.get('id'); signals=row.get('signals')
                if isinstance(rid,str) and isinstance(signals,list): _add(out,f'domain:{rid}',signals)
    intents=doc.get('semantic_intents')
    if isinstance(intents,list):
        for row in intents:
            if not isinstance(row,dict): continue
            rid=row.get('id')
            if isinstance(rid,str):
                aliases=[rid]; term=row.get('term')
                if isinstance(term,str): aliases.append(term)
                _add(out,f'intent:{rid}',aliases)
    if include_lexical:
        entries=doc.get('lexical_entries')
        if isinstance(entries,list):
            for row in entries:
                if not isinstance(row,dict): continue
                surface=row.get('surface'); category=row.get('category')
                if isinstance(surface,str) and isinstance(category,str): _add(out,f'lex:{category}',[surface])
    return {k:tuple(sorted(v,key=lambda s:(len(s),s))) for k,v in out.items()}

def merge_alias_maps(*maps:Mapping[str,Sequence[str]])->Dict[str,tuple[str,...]]:
    out:Dict[str,set[str]]={}
    for m in maps:
        for concept,vals in m.items(): _add(out,concept,vals)
    return {k:tuple(sorted(v,key=lambda s:(len(s),s))) for k,v in out.items()}

def load_aliases(paths:Sequence[str|Path], *, include_lexical:bool=False)->Dict[str,tuple[str,...]]:
    maps=[]
    for path in paths:
        doc=json.loads(Path(path).read_text(encoding='utf-8'))
        if isinstance(doc,dict): maps.append(aliases_from_document(doc,include_lexical=include_lexical))
    return merge_alias_maps(*maps)
