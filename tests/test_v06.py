from pathlib import Path
import pytest

from executable_runtime import ExecutableRuntime
from formula_compiler import FormulaCompiler
from model_v06 import LiraFastModel
from numeric_vm import NumericProgram
from program_learning import Example, learn_verified_formula
from program_store import ProgramStore
from semantic_compiler import SemanticCompiler
from structural_memory import StructuralMemory

def test_formula_compiles_and_runs_new_values():
    p=FormulaCompiler(('a','b')).compile('a + b * 2').program
    assert p.execute({'a':3,'b':4})==11
    assert p.execute({'a':10,'b':-2})==6

def test_conditional_formula_zero_guard():
    p=FormulaCompiler(('a','b')).compile('0 if b == 0 else a / b').program
    assert p.execute({'a':8,'b':2})==4
    assert p.execute({'a':8,'b':0})==0

def test_unsupported_python_is_rejected():
    with pytest.raises(ValueError):
        FormulaCompiler(('x',)).compile('__import__("os").system("echo nope")')

def test_program_binary_roundtrip():
    p=FormulaCompiler(('x',)).compile('abs(x) + 3').program
    q=NumericProgram.from_bytes(p.to_bytes())
    assert q==p and q.execute({'x':-7})==10

def test_learn_verified_formula_rejects_wrong_method():
    mem=StructuralMemory(); store=ProgramStore()
    with pytest.raises(ValueError):
        learn_verified_formula(memory=mem,programs=store,method_id='bad',domain='math',structure_signature='sig',expression='a+b',inputs=('a','b'),examples=[Example({'a':1,'b':2},99)])

def test_verified_formula_becomes_executable_method():
    compiler=SemanticCompiler(); text='somar números'; c=compiler.compile(text)
    mem=StructuralMemory(); store=ProgramStore()
    learned=learn_verified_formula(memory=mem,programs=store,method_id='sum2',domain='math',structure_signature=c.signature,expression='a+b',inputs=('a','b'),examples=[Example({'a':1,'b':2},3),Example({'a':10,'b':5},15),Example({'a':-2,'b':9},7)])
    rt=ExecutableRuntime(mem,compiler,programs=store)
    out=rt.execute(text,{'a':123,'b':456},domain='math')
    assert out.mode=='METHOD' and out.value==579 and learned.method.verified_runs>=3

def test_model_file_persists_executable_program(tmp_path:Path):
    compiler=SemanticCompiler(); c=compiler.compile('multiplicar números')
    mem=StructuralMemory(); store=ProgramStore()
    learn_verified_formula(memory=mem,programs=store,method_id='mul2',domain='math',structure_signature=c.signature,expression='a*b',inputs=('a','b'),examples=[Example({'a':2,'b':3},6),Example({'a':5,'b':4},20),Example({'a':-2,'b':8},-16)])
    path=tmp_path/'m.lirafast'; LiraFastModel.save(path,mem,store,meta={'name':'test'})
    m2,s2,meta=LiraFastModel.load(path)
    rt=ExecutableRuntime(m2,compiler,programs=s2)
    assert rt.execute('multiplicar números',{'a':7,'b':8},domain='math').value==56
    assert meta['model_version']==6 and meta['executable_programs']==1

def test_result_cache_still_wins_over_execution():
    compiler=SemanticCompiler(); text='somar números'; c=compiler.compile(text)
    mem=StructuralMemory(); store=ProgramStore()
    learn_verified_formula(memory=mem,programs=store,method_id='sum2',domain='math',structure_signature=c.signature,expression='a+b',inputs=('a','b'),examples=[Example({'a':1,'b':2},3),Example({'a':2,'b':3},5),Example({'a':4,'b':5},9)])
    assert mem.maybe_save_result(request_parts=(c.normalized,),method_id='sum2',result='cached-perfect',confidence=.999,verified_runs=3)
    rt=ExecutableRuntime(mem,compiler,programs=store)
    out=rt.execute(text,{'a':999,'b':999},domain='math')
    assert out.mode=='RESULT' and out.value=='cached-perfect'
