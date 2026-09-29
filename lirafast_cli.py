from __future__ import annotations
import argparse, json
from pathlib import Path
from semantic_compiler import SemanticCompiler
from container_v05 import LiraFastContainer
from python_ast_delta import PythonASTDelta

def cmd_compile(args):
    c=SemanticCompiler().compile(args.text)
    print(json.dumps({'normalized':c.normalized,'primitives':c.primitives,'unknown':c.unknown,'signature':c.signature,'confidence':c.confidence},ensure_ascii=False,indent=2))

def cmd_inspect(args):
    sections=LiraFastContainer.read(args.path)
    print(json.dumps({k:len(v) for k,v in sections.items()},indent=2,sort_keys=True))

def cmd_pack(args):
    memory=Path(args.memory).read_bytes(); meta={'created_by':'lirafast_cli','version':5}
    Path(args.output).write_bytes(LiraFastContainer.pack({'memory':memory,'meta':json.dumps(meta,separators=(',',':')).encode()}))
    print(args.output)

def cmd_patch_python(args):
    p=Path(args.path); text=p.read_text(encoding='utf-8'); target=PythonASTDelta.locate(text,args.target,args.kind)
    repl=Path(args.replacement).read_text(encoding='utf-8'); r=PythonASTDelta.replace_node(p,target,repl)
    print(json.dumps({'before':r.before_hash,'after':r.after_hash,'preserved_prefix_bytes':r.preserved_prefix_bytes,'preserved_suffix_bytes':r.preserved_suffix_bytes},indent=2))

def build_parser():
    p=argparse.ArgumentParser(prog='lirafast')
    sp=p.add_subparsers(dest='command',required=True)
    c=sp.add_parser('compile-text'); c.add_argument('text'); c.set_defaults(func=cmd_compile)
    i=sp.add_parser('inspect'); i.add_argument('path'); i.set_defaults(func=cmd_inspect)
    k=sp.add_parser('pack-memory'); k.add_argument('memory'); k.add_argument('output'); k.set_defaults(func=cmd_pack)
    x=sp.add_parser('patch-python'); x.add_argument('path'); x.add_argument('target'); x.add_argument('replacement'); x.add_argument('--kind',choices=['function','class'],default='function'); x.set_defaults(func=cmd_patch_python)
    return p

def main(argv=None):
    args=build_parser().parse_args(argv); args.func(args)

if __name__=='__main__':main()
