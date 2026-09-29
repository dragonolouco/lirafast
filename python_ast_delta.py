from __future__ import annotations
"""AST-targeted Python edits that preserve all unrelated source bytes."""
from dataclasses import dataclass
import ast
from hashlib import sha256
from pathlib import Path
import textwrap

def _hash(text:str)->str:return sha256(text.encode('utf-8')).hexdigest()

@dataclass(frozen=True)
class NodeTarget:
    kind:str; qualified_name:str; start_line:int; end_line:int; indent:int; expected_hash:str

@dataclass(frozen=True)
class ASTPatchResult:
    target:NodeTarget; before_hash:str; after_hash:str; preserved_prefix_bytes:int; preserved_suffix_bytes:int

class PythonASTDelta:
    @staticmethod
    def locate(text:str,qualified_name:str,kind:str='function')->NodeTarget:
        tree=ast.parse(text); parts=qualified_name.split('.'); body=tree.body; node=None
        for i,part in enumerate(parts):
            if i<len(parts)-1:
                matches=[n for n in body if isinstance(n,ast.ClassDef) and n.name==part]
                if len(matches)!=1: raise LookupError(f'expected class {part!r} in path {qualified_name!r}, found {len(matches)}')
                node=matches[0]; body=node.body
            else:
                wanted=(ast.FunctionDef,ast.AsyncFunctionDef) if kind=='function' else (ast.ClassDef,)
                matches=[n for n in body if isinstance(n,wanted) and getattr(n,'name',None)==part]
                if len(matches)!=1: raise LookupError(f'expected exactly one {kind} named {qualified_name!r}, found {len(matches)}')
                node=matches[0]
        assert node is not None
        lines=text.splitlines(keepends=True); region=''.join(lines[node.lineno-1:node.end_lineno])
        return NodeTarget(kind,qualified_name,node.lineno,node.end_lineno,int(getattr(node,'col_offset',0)),_hash(region))
    @staticmethod
    def replace_node(path:str|Path,target:NodeTarget,replacement_source:str)->ASTPatchResult:
        p=Path(path); text=p.read_text(encoding='utf-8'); lines=text.splitlines(keepends=True)
        region=''.join(lines[target.start_line-1:target.end_line])
        if _hash(region)!=target.expected_hash: raise RuntimeError('target node changed since plan; refusing stale AST patch')
        raw=textwrap.dedent(replacement_source).strip('\n')+'\n'; repl_tree=ast.parse(raw)
        if len(repl_tree.body)!=1: raise ValueError('replacement must contain exactly one top-level node')
        repl=repl_tree.body[0]; name=target.qualified_name.split('.')[-1]; wanted=(ast.FunctionDef,ast.AsyncFunctionDef) if target.kind=='function' else (ast.ClassDef,)
        if not isinstance(repl,wanted) or repl.name!=name: raise ValueError('replacement node kind/name mismatch')
        indent=' '*target.indent; rendered=''.join(indent+line if line.strip() else line for line in raw.splitlines(keepends=True))
        prefix=''.join(lines[:target.start_line-1]); suffix=''.join(lines[target.end_line:]); new=prefix+rendered+suffix
        ast.parse(new)
        before=_hash(text); p.write_text(new,encoding='utf-8',newline=''); after=_hash(new)
        return ASTPatchResult(target,before,after,len(prefix.encode()),len(suffix.encode()))
