from pathlib import Path
import pytest
from semantic_compiler import SemanticCompiler
from structural_memory import StructuralMemory
from learning import DeepToFastPromoter
from python_ast_delta import PythonASTDelta
from container_v05 import LiraFastContainer
from runtime_v05 import LiraFastRuntime

def test_semantic_compiler_same_structure_different_wording():
    c=SemanticCompiler(); a=c.compile('Crie uma função Python para somar dois números e testar')
    b=c.compile('Faça function em python para adicionar números; teste')
    assert 'intent:create' in a.primitives and 'op:add' in a.primitives
    assert a.signature==b.signature and a.normalized!=b.normalized

def test_deep_promotes_to_fast_after_verified_repetition():
    mem=StructuralMemory(); p=DeepToFastPromoter(mem,min_successes=3,min_confidence=.75); sig='abc'
    assert p.observe_success(domain='code',structure_signature=sig,op_ids=[1,7]) is None
    assert p.observe_success(domain='code',structure_signature=sig,op_ids=[1,7]) is None
    m=p.observe_success(domain='code',structure_signature=sig,op_ids=[1,7])
    assert m and mem.best_method(sig,'code').method_id==m.method_id

def test_same_signature_different_domain_does_not_collide():
    mem=StructuralMemory(); p=DeepToFastPromoter(mem,min_successes=1,min_confidence=.5)
    a=p.observe_success(domain='code',structure_signature='same',op_ids=[1])
    b=p.observe_success(domain='math',structure_signature='same',op_ids=[2])
    assert a.method_id!=b.method_id

def test_error_memory_guards_variant():
    mem=StructuralMemory(); p=DeepToFastPromoter(mem)
    p.observe_failure(domain='math',structure_signature='div',exact_parts=['divide','b=0'],variant_parts=['divide','denominator-zero'],detector=['denom == 0'],correction_method_id='guard')
    rt=LiraFastRuntime(mem)
    d=rt.route('dividir dois números',domain='math',exact_error_parts=['other'],variant_error_parts=['divide','denominator-zero'])
    assert d.mode=='GUARDED'

def test_python_ast_delta_changes_only_top_level_target(tmp_path:Path):
    p=tmp_path/'m.py'; before='HEADER = "keep"\n\ndef f(x):\n    return x + 1\n\nTAIL = "keep too"\n'
    p.write_text(before,encoding='utf-8'); t=PythonASTDelta.locate(before,'f')
    r=PythonASTDelta.replace_node(p,t,'def f(x):\n    y = x + 1\n    return y * 2\n')
    after=p.read_text(encoding='utf-8')
    assert after.startswith('HEADER = "keep"\n\n') and after.endswith('\nTAIL = "keep too"\n')
    assert 'return y * 2' in after and r.preserved_prefix_bytes>0 and r.preserved_suffix_bytes>0

def test_python_ast_delta_nested_method_preserves_class_and_tail(tmp_path:Path):
    p=tmp_path/'m.py'; before='class Player:\n    def update(self, x):\n        return x + 1\n\n    def untouched(self):\n        return 7\n\nTAIL = 3\n'
    p.write_text(before,encoding='utf-8'); t=PythonASTDelta.locate(before,'Player.update')
    PythonASTDelta.replace_node(p,t,'def update(self, x):\n    y = x + 1\n    return y * 2\n')
    after=p.read_text(encoding='utf-8'); assert '    def untouched' in after and after.endswith('TAIL = 3\n'); compile(after,'m.py','exec')

def test_python_ast_delta_rejects_stale_node(tmp_path:Path):
    p=tmp_path/'m.py'; a='def f():\n    return 1\n'; p.write_text(a,encoding='utf-8'); t=PythonASTDelta.locate(a,'f')
    p.write_text('def f():\n    return 99\n',encoding='utf-8')
    with pytest.raises(RuntimeError): PythonASTDelta.replace_node(p,t,'def f():\n    return 2\n')

def test_container_roundtrip_and_corruption_detection():
    blob=LiraFastContainer.pack({'memory':b'{"a":1}','symbols':b'abc'*100})
    out=LiraFastContainer.unpack(blob); assert out['memory']==b'{"a":1}' and out['symbols']==b'abc'*100
    bad=bytearray(blob); bad[-1]^=1
    with pytest.raises(Exception): LiraFastContainer.unpack(bytes(bad))

def test_result_cache_is_exact_but_method_cache_generalizes():
    rt=LiraFastRuntime(); a='crie função python somar'; b='faça function python adicionar'
    c=rt.compiler.compile(a)
    for _ in range(3): rt.promoter.observe_success(domain='code',structure_signature=c.signature,op_ids=[1])
    assert rt.route(b,domain='code').mode=='METHOD'
    assert rt.save_verified_result(a,domain='code',result='cached-A',confidence=.999,verified_runs=3)
    assert rt.route(a,domain='code').mode=='RESULT'
    assert rt.route(b,domain='code').mode=='METHOD'

def test_semantic_cache_is_bounded():
    c=SemanticCompiler(cache_limit=3)
    for i in range(20): c.compile(f'crie arquivo python {i}')
    assert len(c._cache)==3

def test_exact_result_bypasses_semantic_compiler():
    class BombCompiler(SemanticCompiler):
        def compile(self,text): raise AssertionError('exact result path must not compile')
    mem=StructuralMemory(); base=SemanticCompiler(); c=base.compile('crie função python somar')
    from structural_memory import MethodMemory
    m=MethodMemory('m','code',c.signature,(1,),confidence=.99,verified_runs=5); mem.register_method(m)
    mem.maybe_save_result(request_parts=(c.normalized,),method_id='m',result='ready',confidence=.999,verified_runs=3)
    rt=LiraFastRuntime(mem,BombCompiler())
    assert rt.route('crie função python somar',domain='code').mode=='RESULT'

def test_knowledge_loader_uses_explicit_interpretation_cues(tmp_path:Path):
    import json
    from knowledge_loader import load_aliases
    doc={'format_id':'python','language':'Python','aliases':['py'],'extensions':['.py'],'signal_roles':{'actions':[{'id':'create','cues':['criar','monte'],'interpret_as':'action:create'}]},'domain_routing':{'domains':[{'id':'programming','signals':['código','python']}]}}
    p=tmp_path/'k.json'; p.write_text(json.dumps(doc,ensure_ascii=False),encoding='utf-8')
    a=load_aliases([p])
    assert '.py' in a['lang:python'] and 'criar' in a['action:create'] and 'código' in a['domain:programming']

def test_negated_action_is_not_activated_but_constraint_survives(tmp_path:Path):
    import json
    from knowledge_loader import load_aliases
    doc={'signal_roles':{'actions':[{'id':'edit','cues':['alterar'],'interpret_as':'action:edit'}],'negation':{'id':'negation','cues':['sem','não'],'interpret_as':'negation'},'constraints':{'id':'constraint','cues':['sem alterar'],'interpret_as':'constraint'}}}
    p=tmp_path/'i.json'; p.write_text(json.dumps(doc,ensure_ascii=False),encoding='utf-8')
    c=SemanticCompiler(load_aliases([p])); r=c.compile('crie arquivo sem alterar o resto')
    assert 'action:edit' not in r.primitives and 'constraint' in r.primitives

def test_runtime_can_take_domain_from_loaded_knowledge(tmp_path:Path):
    import json
    from knowledge_loader import load_aliases
    from structural_memory import MethodMemory
    doc={'domain_routing':{'domains':[{'id':'programming','signals':['python','código']}]}}
    p=tmp_path/'i.json'; p.write_text(json.dumps(doc,ensure_ascii=False),encoding='utf-8')
    compiler=SemanticCompiler(load_aliases([p])); mem=StructuralMemory(); c=compiler.compile('python código')
    mem.register_method(MethodMemory('m','programming',c.signature,(1,),confidence=.9,verified_runs=5))
    d=LiraFastRuntime(mem,compiler).route('python código')
    assert d.mode=='METHOD' and d.domain=='programming'

def test_cli_compile_text(capsys):
    from lirafast_cli import main
    main(['compile-text','crie função python somar'])
    out=capsys.readouterr().out
    assert 'lang:python' in out and 'op:add' in out
